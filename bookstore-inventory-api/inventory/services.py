"""Exchange-rate integration and suggested-price calculations."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, DecimalException, ROUND_HALF_UP, localcontext
from hashlib import sha256
import logging
import re
from typing import Any, Literal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
import requests

from .models import Book

logger = logging.getLogger(__name__)
MARGIN_PERCENTAGE = 40
MAX_SELLING_PRICE = Decimal("9999999999999999.99")


class ExchangeRateUnavailable(Exception):
    """No usable exchange-rate data is available."""


class UnsupportedCurrency(ValueError):
    """The provider does not list the requested target currency."""


@dataclass(frozen=True)
class _RateSnapshot:
    rates: dict[str, Decimal]
    fetched_at: datetime


@dataclass(frozen=True)
class _ExchangeRate:
    value: Decimal
    source: Literal["live", "cache", "stale_cache", "identity", "default"]
    fetched_at: datetime | None


@dataclass(frozen=True)
class SuggestedPrice:
    cost_usd: Decimal
    cost_local: Decimal
    selling_price_local: Decimal
    exchange_rate: Decimal
    currency: str
    calculation_timestamp: datetime
    rate_source: Literal["live", "cache", "stale_cache", "identity", "default"]
    rates_fetched_at: datetime | None


def _parse_rates(payload: Any) -> dict[str, Decimal]:
    """Only accept positive, finite rates explicitly based on USD."""
    if not isinstance(payload, dict) or payload.get("base") != "USD":
        raise ValueError("The provider response must use USD as its base currency.")
    if payload.get("result", "success") != "success":
        raise ValueError("The provider reported an error.")
    values = payload.get("rates")
    if not isinstance(values, dict) or not values:
        raise ValueError("The provider response contains no exchange rates.")

    rates: dict[str, Decimal] = {}
    for currency, value in values.items():
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("The provider returned an invalid currency code.")
        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            raise ValueError("The provider returned a nonnumeric exchange rate.")
        try:
            rate = Decimal(str(value))
        except DecimalException as error:
            raise ValueError("The provider returned a nonnumeric exchange rate.") from error
        if not rate.is_finite() or rate <= 0:
            raise ValueError("The provider returned an invalid exchange rate.")
        rates[currency] = rate
    if rates.get("USD") != Decimal("1"):
        raise ValueError("The provider response must include a USD rate of 1.")
    return rates


def _fetch_rates() -> _RateSnapshot:
    response = requests.get(
        settings.EXCHANGE_RATE_API_URL,
        timeout=settings.EXCHANGE_RATE_API_TIMEOUT,
    )
    response.raise_for_status()
    rates = _parse_rates(response.json(parse_float=Decimal))
    return _RateSnapshot(rates=rates, fetched_at=timezone.now())


def _get_rates() -> tuple[_RateSnapshot, Literal["live", "cache", "stale_cache"]]:
    # Include the configured URL so changing providers cannot reuse old rates.
    key = "inventory:exchange-rates:" + sha256(settings.EXCHANGE_RATE_API_URL.encode()).hexdigest()
    snapshot = cache.get(key)
    if isinstance(snapshot, _RateSnapshot):
        age = (timezone.now() - snapshot.fetched_at).total_seconds()
        if not 0 <= age < settings.EXCHANGE_RATE_FALLBACK_TTL:
            snapshot = None
        elif age < settings.EXCHANGE_RATE_CACHE_TTL:
            return snapshot, "cache"
    else:
        snapshot = None

    try:
        fresh = _fetch_rates()
    except (requests.RequestException, ValueError) as error:
        logger.warning("Exchange-rate request failed (%s).", type(error).__name__)
        if snapshot is not None:
            return snapshot, "stale_cache"
        raise ExchangeRateUnavailable("No recent exchange rates are available.") from error

    cache.set(key, fresh, timeout=settings.EXCHANGE_RATE_FALLBACK_TTL)
    return fresh, "live"


def _get_exchange_rate(target_currency: str) -> _ExchangeRate:
    if target_currency == "USD":
        return _ExchangeRate(Decimal("1"), "identity", None)

    try:
        snapshot, source = _get_rates()
    except ExchangeRateUnavailable:
        if target_currency == settings.LOCAL_CURRENCY:
            return _ExchangeRate(settings.EXCHANGE_RATE_DEFAULT_RATE, "default", None)
        raise
    if target_currency not in snapshot.rates:
        raise UnsupportedCurrency(f"Unsupported target currency: {target_currency}.")
    return _ExchangeRate(snapshot.rates[target_currency], source, snapshot.fetched_at)


def _calculate_price(cost_usd: Decimal, currency: str, rate: _ExchangeRate) -> SuggestedPrice:
    """Apply the required 40% markup before rounding displayed money."""
    try:
        with localcontext() as context:
            context.prec = 38
            converted = cost_usd * rate.value
            selling_price = (converted * Decimal("1.40")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )
            cost_local = converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except DecimalException as error:
        raise ExchangeRateUnavailable("The exchange rate cannot produce a usable price.") from error
    if selling_price > MAX_SELLING_PRICE:
        raise ExchangeRateUnavailable("The calculated price exceeds supported storage precision.")
    return SuggestedPrice(
        cost_usd=cost_usd,
        cost_local=cost_local,
        selling_price_local=selling_price,
        exchange_rate=rate.value,
        currency=currency,
        calculation_timestamp=timezone.now(),
        rate_source=rate.source,
        rates_fetched_at=rate.fetched_at,
    )


def _calculate_with_fallback(cost_usd: Decimal, currency: str, rate: _ExchangeRate) -> SuggestedPrice:
    try:
        return _calculate_price(cost_usd, currency, rate)
    except ExchangeRateUnavailable:
        if currency != settings.LOCAL_CURRENCY or rate.source == "default":
            raise
        logger.warning("Unusable calculated price; using the configured default exchange rate.")
        return _calculate_price(
            cost_usd, currency, _ExchangeRate(settings.EXCHANGE_RATE_DEFAULT_RATE, "default", None),
        )


def calculate_suggested_price(cost_usd: Decimal, target_currency: str) -> SuggestedPrice:
    """Calculate USD cost conversion and 40% markup without saving a book."""
    return _calculate_with_fallback(cost_usd, target_currency, _get_exchange_rate(target_currency))


def calculate_and_save_book_price(book_id: int, target_currency: str) -> SuggestedPrice:
    """Fetch rates before locking, then calculate using the current saved cost."""
    if target_currency != settings.LOCAL_CURRENCY:
        raise UnsupportedCurrency(f"Stored selling prices use {settings.LOCAL_CURRENCY}.")
    rate = _get_exchange_rate(target_currency)
    with transaction.atomic():
        book = Book.objects.select_for_update().get(pk=book_id)
        quote = _calculate_with_fallback(book.cost_usd, target_currency, rate)
        book.selling_price_local = quote.selling_price_local
        book.save(update_fields=["selling_price_local", "updated_at"])
    return quote
