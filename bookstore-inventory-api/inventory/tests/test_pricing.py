"""Exchange-rate resilience, exam calculations and persisted selling prices."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
import requests
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Book
from inventory.services import ExchangeRateUnavailable, UnsupportedCurrency, calculate_suggested_price

PRICING_SETTINGS = {
    "LOCAL_CURRENCY": "EUR",
    "EXCHANGE_RATE_DEFAULT_RATE": Decimal("0.85"),
    "EXCHANGE_RATE_API_URL": "https://api.exchangerate-api.com/v4/latest/USD",
    "EXCHANGE_RATE_API_TIMEOUT": 2.5,
    "EXCHANGE_RATE_CACHE_TTL": 60,
    "EXCHANGE_RATE_FALLBACK_TTL": 3600,
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "inventory-pricing-tests",
        },
    },
}


class _PricingTestMixin:
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.now = timezone.now()
        clock_patch = patch("inventory.services.timezone.now", return_value=self.now)
        self.clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        request_patch = patch("inventory.services.requests.get")
        self.http = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.response = Mock()
        self.response.json.return_value = {
            "base": "USD", "rates": {"USD": 1, "EUR": Decimal("0.90"), "VES": 40},
        }
        self.http.return_value = self.response
        logger_patch = patch("inventory.services.logger")
        self.logger = logger_patch.start()
        self.addCleanup(logger_patch.stop)


@override_settings(**PRICING_SETTINGS)
class ExchangeRateServiceTests(_PricingTestMixin, SimpleTestCase):
    def test_fetches_live_rate_with_timeout_and_applies_markup(self) -> None:
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.cost_local, Decimal("9.00"))
        self.assertEqual(quote.selling_price_local, Decimal("12.60"))
        self.assertEqual(quote.rate_source, "live")
        self.assertEqual(quote.rates_fetched_at, self.now)
        self.http.assert_called_once_with(PRICING_SETTINGS["EXCHANGE_RATE_API_URL"], timeout=2.5)

    def test_pdf_example_returns_19_03(self) -> None:
        self.response.json.return_value["rates"]["EUR"] = Decimal("0.85")
        quote = calculate_suggested_price(Decimal("15.99"), "EUR")
        self.assertEqual(quote.cost_local, Decimal("13.59"))
        self.assertEqual(quote.selling_price_local, Decimal("19.03"))

    def test_fresh_rates_are_reused_across_currencies(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        quote = calculate_suggested_price(Decimal("10.00"), "VES")
        self.assertEqual(quote.selling_price_local, Decimal("560.00"))
        self.assertEqual(quote.rate_source, "cache")
        self.assertEqual(self.http.call_count, 1)

    def test_expired_fresh_cache_is_refreshed(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        self.clock.return_value = self.now + timedelta(seconds=61)
        self.response.json.return_value["rates"]["EUR"] = Decimal("1.2")
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.selling_price_local, Decimal("16.80"))
        self.assertEqual(quote.rate_source, "live")
        self.assertEqual(self.http.call_count, 2)

    def test_outage_prefers_last_known_rates_over_default(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        self.clock.return_value = self.now + timedelta(seconds=61)
        self.http.side_effect = requests.Timeout()
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.selling_price_local, Decimal("12.60"))
        self.assertEqual(quote.rate_source, "stale_cache")
        self.assertEqual(quote.rates_fetched_at, self.now)

    def test_expired_fallback_uses_configured_default_rate(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        self.clock.return_value = self.now + timedelta(seconds=3600)
        self.http.side_effect = requests.ConnectionError()
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.exchange_rate, Decimal("0.85"))
        self.assertEqual(quote.selling_price_local, Decimal("11.90"))
        self.assertEqual(quote.rate_source, "default")
        self.assertIsNone(quote.rates_fetched_at)

    def test_cold_cache_network_errors_use_default(self) -> None:
        for error in (requests.Timeout(), requests.ConnectionError()):
            with self.subTest(error=type(error).__name__):
                self.http.side_effect = error
                quote = calculate_suggested_price(Decimal("10.00"), "EUR")
                self.assertEqual(quote.rate_source, "default")
                self.assertEqual(quote.exchange_rate, Decimal("0.85"))

    def test_http_errors_and_invalid_json_use_default(self) -> None:
        for code in (429, 500, 503):
            with self.subTest(code=code):
                self.response.raise_for_status.side_effect = requests.HTTPError(response=Mock(status_code=code))
                self.assertEqual(calculate_suggested_price(Decimal("10.00"), "EUR").rate_source, "default")
        self.response.raise_for_status.side_effect = None
        self.response.json.side_effect = ValueError("Invalid JSON")
        self.assertEqual(calculate_suggested_price(Decimal("10.00"), "EUR").rate_source, "default")

    def test_bad_payloads_and_rates_are_rejected_before_caching(self) -> None:
        payloads = [
            None, [], {}, {"base": "EUR", "rates": {"USD": 1, "EUR": 1}},
            {"base": "USD", "rates": []}, {"base": "USD", "rates": {}},
            {"base": "USD", "rates": {"EUR": 0.9}},
            {"base": "USD", "rates": {"USD": 2, "EUR": 0.9}},
            {"base": "USD", "rates": {"USD": 1}, "result": "error"},
            {"base": "USD", "rates": {"USD": 1, "eur": 0.9}},
        ]
        payloads.extend(
            {"base": "USD", "rates": {"USD": 1, "EUR": value}}
            for value in (0, -1, "bad", "NaN", "sNaN", "Infinity", True, None, {})
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.response.json.return_value = payload
                quote = calculate_suggested_price(Decimal("10.00"), "EUR")
                self.assertEqual(quote.rate_source, "default")
                self.assertEqual(quote.exchange_rate, Decimal("0.85"))

    def test_invalid_response_preserves_last_valid_snapshot(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        self.clock.return_value = self.now + timedelta(seconds=61)
        self.response.json.return_value = {"base": "USD", "rates": {"USD": 1, "EUR": -1}}
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.rate_source, "stale_cache")
        self.assertEqual(quote.selling_price_local, Decimal("12.60"))

    def test_unknown_currency_is_rejected(self) -> None:
        with self.assertRaises(UnsupportedCurrency):
            calculate_suggested_price(Decimal("10.00"), "XYZ")

    def test_no_undocumented_default_is_used_for_another_currency(self) -> None:
        self.http.side_effect = requests.ConnectionError()
        with self.assertRaises(ExchangeRateUnavailable):
            calculate_suggested_price(Decimal("10.00"), "VES")

    def test_usd_identity_rate_still_applies_markup(self) -> None:
        self.http.side_effect = requests.ConnectionError()
        quote = calculate_suggested_price(Decimal("10.00"), "USD")
        self.assertEqual(quote.selling_price_local, Decimal("14.00"))
        self.assertEqual(quote.rate_source, "identity")
        self.http.assert_not_called()

    def test_intermediate_conversion_is_not_prematurely_rounded(self) -> None:
        self.response.json.return_value["rates"]["EUR"] = Decimal("0.333")
        quote = calculate_suggested_price(Decimal("1.01"), "EUR")
        self.assertEqual(quote.cost_local, Decimal("0.34"))
        self.assertEqual(quote.selling_price_local, Decimal("0.47"))

    def test_cache_is_isolated_by_configured_provider_url(self) -> None:
        calculate_suggested_price(Decimal("10.00"), "EUR")
        self.http.side_effect = requests.ConnectionError()
        with override_settings(EXCHANGE_RATE_API_URL="https://example.test/latest/USD"):
            self.assertEqual(calculate_suggested_price(Decimal("10.00"), "EUR").rate_source, "default")

    def test_unusable_provider_rate_uses_configured_default(self) -> None:
        self.response.json.return_value["rates"]["EUR"] = "1E999999999"
        quote = calculate_suggested_price(Decimal("10.00"), "EUR")
        self.assertEqual(quote.rate_source, "default")
        self.assertEqual(quote.selling_price_local, Decimal("11.90"))


@override_settings(**PRICING_SETTINGS)
class BookPricingAPITests(_PricingTestMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.book = Book.objects.create(
            title="El Quijote", author="Miguel de Cervantes", isbn="978-84-376-0494-7",
            cost_usd=Decimal("15.99"), stock_quantity=25, supplier_country="ES",
        )
        self.url = reverse("books:book-calculate-price", args=[self.book.pk])
        self.response.json.return_value["rates"]["EUR"] = Decimal("0.85")

    def test_post_returns_pdf_breakdown_and_saves_selling_price(self) -> None:
        old_updated = self.book.updated_at
        self.clock.return_value = self.now + timedelta(seconds=1)
        response = self.client.post(self.url, {"target_currency": "eur"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {
            "book_id": self.book.pk, "cost_usd": "15.99", "exchange_rate": "0.85",
            "cost_local": "13.59", "margin_percentage": 40, "selling_price_local": "19.03",
            "currency": "EUR", "rate_source": "live", "is_fallback": False,
        }
        for field, value in expected.items():
            self.assertEqual(response.data[field], value)
        self.assertEqual(response.data["calculation_timestamp"], self.clock.return_value.isoformat())
        self.assertIsNotNone(response.data["rates_fetched_at"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("19.03"))
        self.assertEqual(self.book.cost_usd, Decimal("15.99"))
        self.assertGreater(self.book.updated_at, old_updated)
        detail = self.client.get(reverse("books:book-detail", args=[self.book.pk]))
        self.assertEqual(detail.data["selling_price_local"], "19.03")

    def test_empty_body_uses_configured_local_currency(self) -> None:
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], "EUR")

    def test_invalid_or_different_currency_returns_400_without_external_call(self) -> None:
        for currency in ("", "EU", "EURO", "123", None, [], "USD", "XYZ"):
            with self.subTest(currency=currency):
                response = self.client.post(self.url, {"target_currency": currency}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("target_currency", response.data)
        self.http.assert_not_called()

    def test_missing_book_returns_404_without_external_call(self) -> None:
        url = reverse("books:book-calculate-price", args=[987654])
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.http.assert_not_called()

    def test_only_post_is_allowed(self) -> None:
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.http.assert_not_called()

    def test_cold_cache_outage_uses_default_and_saves_price(self) -> None:
        self.http.side_effect = requests.Timeout()
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selling_price_local"], "19.03")
        self.assertEqual(response.data["rate_source"], "default")
        self.assertTrue(response.data["is_fallback"])
        self.assertIsNone(response.data["rates_fetched_at"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("19.03"))

    def test_fresh_cache_is_reported(self) -> None:
        self.client.post(self.url, {}, format="json")
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rate_source"], "cache")
        self.assertFalse(response.data["is_fallback"])
        self.assertEqual(self.http.call_count, 1)

    def test_stale_cache_has_original_fetch_time_and_new_calculation_time(self) -> None:
        first = self.client.post(self.url, {}, format="json")
        self.clock.return_value = self.now + timedelta(seconds=61)
        self.http.side_effect = requests.ConnectionError()
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rate_source"], "stale_cache")
        self.assertTrue(response.data["is_fallback"])
        self.assertEqual(response.data["rates_fetched_at"], first.data["rates_fetched_at"])
        self.assertNotEqual(response.data["calculation_timestamp"], first.data["calculation_timestamp"])

    def test_unusable_provider_and_default_return_503_without_writing(self) -> None:
        self.http.side_effect = requests.Timeout()
        with override_settings(EXCHANGE_RATE_DEFAULT_RATE=Decimal("1E40")):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.book.refresh_from_db()
        self.assertIsNone(self.book.selling_price_local)

    def test_cost_changed_during_rate_fetch_is_read_before_calculation(self) -> None:
        def fetch(*args: object, **kwargs: object) -> Mock:
            Book.objects.filter(pk=self.book.pk).update(cost_usd=Decimal("20.00"))
            return self.response
        self.http.side_effect = fetch
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cost_usd"], "20.00")
        self.assertEqual(response.data["selling_price_local"], "23.80")
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("23.80"))

    def test_book_deleted_during_rate_fetch_returns_404(self) -> None:
        def fetch(*args: object, **kwargs: object) -> Mock:
            self.book.delete()
            return self.response
        self.http.side_effect = fetch
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, status.HTTP_404_NOT_FOUND)

    def test_save_failure_rolls_back_calculated_price(self) -> None:
        original_save = Book.save
        def fail_after_save(book: Book, *args: object, **kwargs: object) -> None:
            original_save(book, *args, **kwargs)
            raise ValidationError({"selling_price_local": "Save failed."})
        with patch.object(Book, "save", fail_after_save):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.book.refresh_from_db()
        self.assertIsNone(self.book.selling_price_local)

    def test_configured_usd_currency_applies_markup_without_provider(self) -> None:
        with override_settings(LOCAL_CURRENCY="USD", EXCHANGE_RATE_DEFAULT_RATE=Decimal("1")):
            response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], "USD")
        self.assertEqual(response.data["selling_price_local"], "22.39")
        self.http.assert_not_called()
