"""Execute the exported collection's request sequence against the test API."""

import json
from pathlib import Path
import re
from unittest.mock import Mock, patch
from urllib.parse import parse_qsl, urlencode, urlsplit

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from inventory.models import Book
from inventory.tests.test_pricing import PRICING_SETTINGS


@override_settings(**PRICING_SETTINGS)
class PostmanCollectionTests(APITestCase):
    def test_collection_request_sequence_matches_the_api(self) -> None:
        path = Path(settings.BASE_DIR) / "postman/bookstore-inventory.postman_collection.json"
        collection = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(collection["info"]["schema"], "https://schema.getpostman.com/json/collection/v2.1.0/collection.json")
        variables = {entry["key"]: entry["value"] for entry in collection["variable"]}
        cache.clear()
        self.addCleanup(cache.clear)
        provider = Mock()
        provider.json.return_value = {"base": "USD", "rates": {"USD": 1, "EUR": "0.85"}}

        def substitute(value: str) -> str:
            return re.sub(r"\{\{([^}]+)\}\}", lambda match: variables[match.group(1)], value)

        with patch("inventory.services.requests.get", return_value=provider):
            for item in collection["item"]:
                with self.subTest(request=item["name"]):
                    request = item["request"]
                    url = urlsplit(substitute(request["url"]))
                    target = url.path
                    if url.query:
                        target += "?" + urlencode(parse_qsl(url.query))
                    body = json.loads(substitute(request["body"]["raw"])) if "body" in request else None
                    response = getattr(self.client, request["method"].lower())(target, body, format="json")
                    script = next(event["script"]["exec"] for event in item["event"] if event["listen"] == "test")
                    expected_status = int(re.search(r"\.status\((\d+)\)", "\n".join(script)).group(1))
                    self.assertEqual(response.status_code, expected_status, response.data)
                    if request["method"] == "POST" and target == "/books" and response.status_code == 201:
                        variables["book_id"] = str(response.data["id"])
                    if target.endswith("/calculate-price") and response.status_code == 200:
                        variables["calculated_price"] = response.data["selling_price_local"]
                        self.assertEqual(variables["calculated_price"], "19.03")
                    if item["name"].startswith("09"):
                        self.assertEqual(response.data["selling_price_local"], variables["calculated_price"])
        self.assertFalse(Book.objects.exists())
