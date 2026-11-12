"""Book request validation and response serialization."""

from decimal import Decimal
import re
from typing import Any

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from rest_framework import serializers
from rest_framework.settings import api_settings

from .models import Book
from .validators import normalize_isbn


def model_validation_error(error: DjangoValidationError) -> serializers.ValidationError:
    """Preserve field errors and translate Django's non-field error key."""
    detail = serializers.as_serializer_error(error)
    non_field_errors = detail.pop(NON_FIELD_ERRORS, [])
    if non_field_errors:
        detail.setdefault(api_settings.NON_FIELD_ERRORS_KEY, []).extend(non_field_errors)
    return serializers.ValidationError(detail)


class CalculatePriceSerializer(serializers.Serializer):
    """Persisted selling prices always use the configured local currency."""

    target_currency = serializers.CharField(min_length=3, max_length=3, required=False)

    def validate_target_currency(self, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise serializers.ValidationError("Use a three-letter currency code, such as EUR.")
        if value != settings.LOCAL_CURRENCY:
            raise serializers.ValidationError(
                f"Use the configured local currency: {settings.LOCAL_CURRENCY}."
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs.setdefault("target_currency", settings.LOCAL_CURRENCY)
        return attrs


class StockThresholdSerializer(serializers.Serializer):
    threshold = serializers.IntegerField(min_value=0, max_value=2147483647, default=10)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if data.get("threshold") == "":
            raise serializers.ValidationError({"threshold": ["Enter a nonnegative integer."]})
        return super().to_internal_value(data)


class DisplayCurrencySerializer(serializers.Serializer):
    currency = serializers.CharField(min_length=3, max_length=3, required=False)

    def validate_currency(self, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise serializers.ValidationError("Use a three-letter currency code.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs.setdefault("currency", settings.LOCAL_CURRENCY)
        return attrs


class CategorySearchSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=100)


class ISBNField(serializers.CharField):
    def to_internal_value(self, data: Any) -> str:
        return normalize_isbn(super().to_internal_value(data))


class CountryCodeField(serializers.CharField):
    def to_internal_value(self, data: Any) -> str:
        return super().to_internal_value(data).upper()


class BookSerializer(serializers.ModelSerializer):
    """Expose editable book data and read-only identifiers and timestamps."""

    class Meta:
        model = Book
        fields = (
            "id", "title", "author", "isbn", "cost_usd", "selling_price_local",
            "stock_quantity", "category", "supplier_country", "created_at", "updated_at",
        )
        read_only_fields = ("id", "selling_price_local", "created_at", "updated_at")

    def build_standard_field(
        self, field_name: str, model_field: models.Field,
    ) -> tuple[type[serializers.Field], dict[str, Any]]:
        field_class, kwargs = super().build_standard_field(field_name, model_field)
        # Keep DRF's model validators and uniqueness checks after normalization.
        if field_name == "isbn":
            field_class = ISBNField
        elif field_name == "supplier_country":
            field_class = CountryCodeField
        return field_class, kwargs

    def validate_cost_usd(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError("USD cost must be greater than 0.")
        return value

    def validate_stock_quantity(self, value: int) -> int:
        if value < 0:
            raise serializers.ValidationError("Stock must be greater than or equal to 0.")
        return value

    def create(self, validated_data: dict[str, Any]) -> Book:
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise model_validation_error(error) from error

    def update(self, instance: Book, validated_data: dict[str, Any]) -> Book:
        if "cost_usd" in validated_data and validated_data["cost_usd"] != instance.cost_usd:
            validated_data["selling_price_local"] = None
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise model_validation_error(error) from error
