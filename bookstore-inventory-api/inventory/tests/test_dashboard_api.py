"""Server-backed dashboard totals, global search and read-only currency views."""

from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import override_settings
import requests
from rest_framework.test import APITestCase

from inventory.models import Book
from inventory.tests.test_pricing import PRICING_SETTINGS


@override_settings(**PRICING_SETTINGS)
class DashboardAPITests(APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.addCleanup(cache.clear)
        self.first = Book.objects.create(
            title="A book about planets", author="Ada Lovelace", isbn="9788437604947",
            cost_usd=Decimal("10.00"), stock_quantity=5, category="Science",
            selling_price_local=Decimal("14.00"),
        )
        self.second = Book.objects.create(
            title="A history of libraries", author="George Orwell", isbn="9780306406157",
            cost_usd=Decimal("20.00"), stock_quantity=11, category="History",
        )
        Book.objects.create(
            title="An empty shelf", author="Another author", isbn="080442957X",
            cost_usd=Decimal("5.00"), stock_quantity=0, category="Science",
        )

    def test_summary_aggregates_entire_inventory_independently_of_pagination(self) -> None:
        response = self.client.get("/books/summary", {"page_size": 1, "low_stock": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_titles"], 3)
        self.assertEqual(response.data["inventory_value_usd"], "270.00")
        self.assertEqual(response.data["low_stock_titles"], 2)
        self.assertEqual(response.data["out_of_stock_titles"], 1)
        self.assertEqual(response.data["categories"], ["History", "Science"])
        self.assertEqual(response.data["local_currency"], "EUR")
        self.assertEqual(response.data["margin_percentage"], 40)

    def test_empty_summary_is_safe(self) -> None:
        Book.objects.all().delete()
        response = self.client.get("/books/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_titles"], 0)
        self.assertEqual(response.data["inventory_value_usd"], "0.00")
        self.assertEqual(response.data["categories"], [])

    def test_search_matches_title_author_and_formatted_isbn(self) -> None:
        for search in ("PLANETS", "ada lovelace", "978-84-376-0494-7"):
            with self.subTest(search=search):
                response = self.client.get("/books", {"search": search, "page_size": 1})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(response.data["results"][0]["id"], self.first.pk)

    def test_search_combines_with_category_and_low_stock(self) -> None:
        response = self.client.get("/books/low-stock", {"category": "Science", "search": "Ada"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_descending_id_order_and_invalid_order(self) -> None:
        response = self.client.get("/books", {"ordering": "-id"})
        ids = [book["id"] for book in response.data["results"]]
        self.assertEqual(ids, sorted(ids, reverse=True))
        self.assertEqual(self.client.get("/books", {"ordering": "bad"}).status_code, 400)

    def test_display_currency_is_read_only_and_uses_cross_rate(self) -> None:
        provider = Mock()
        provider.json.return_value = {"base": "USD", "rates": {"USD": 1, "EUR": "0.8", "GBP": "0.6"}}
        before = list(Book.objects.order_by("id").values())
        with patch("inventory.services.requests.get", return_value=provider) as http:
            response = self.client.get("/books/exchange-rate", {"currency": "gbp"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversion_rate"], "0.75")
        self.assertFalse(response.data["is_fallback"])
        self.assertEqual(http.call_count, 1)
        self.assertEqual(list(Book.objects.order_by("id").values()), before)

    def test_local_display_needs_no_provider(self) -> None:
        with patch("inventory.services.requests.get") as http:
            response = self.client.get("/books/exchange-rate", {"currency": "EUR"})
        self.assertEqual(response.data["conversion_rate"], "1")
        http.assert_not_called()

    def test_display_usd_can_use_explicit_local_fallback(self) -> None:
        with patch("inventory.services.requests.get", side_effect=requests.Timeout()), patch("inventory.services.logger"):
            response = self.client.get("/books/exchange-rate", {"currency": "USD"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_fallback"])
        self.assertEqual(Decimal(response.data["conversion_rate"]), Decimal(1) / Decimal("0.85"))

    def test_other_display_currencies_fail_honestly_during_outage(self) -> None:
        with patch("inventory.services.requests.get", side_effect=requests.Timeout()), patch("inventory.services.logger"):
            response = self.client.get("/books/exchange-rate", {"currency": "GBP"})
        self.assertEqual(response.status_code, 503)
