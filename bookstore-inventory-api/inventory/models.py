"""Inventory persistence and model-level validation."""

from collections.abc import Collection
from decimal import Decimal
from math import isfinite
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from .validators import normalize_isbn, validate_isbn


class Book(models.Model):
    """A book edition and its inventory data."""

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True, validators=[validate_isbn])
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"), message="USD cost must be greater than 0."),
        ],
    )
    selling_price_local = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    category = models.CharField(max_length=100, blank=True, null=True)
    supplier_country = models.CharField(
        max_length=2, blank=True, default="",
        validators=[RegexValidator(r"\A[A-Z]{2}\Z", "Use a two-letter country code, such as ES.")],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cost_usd__gt=0),
                name="book_cost_usd_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name="book_stock_quantity_gte_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price_local__isnull=True) | models.Q(selling_price_local__gte=0),
                name="book_selling_price_gte_zero",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"

    def clean_fields(self, exclude: Collection[str] | None = None) -> None:
        """Reject fractional stock before IntegerField can truncate it."""
        excluded = set(exclude or ())
        if "isbn" not in excluded and isinstance(self.isbn, str):
            self.isbn = normalize_isbn(self.isbn)
        if "supplier_country" not in excluded and isinstance(self.supplier_country, str):
            self.supplier_country = self.supplier_country.strip().upper()
        errors: dict[str, list[ValidationError]] = {}
        if "stock_quantity" not in excluded and isinstance(self.stock_quantity, (float, Decimal)):
            finite = (
                self.stock_quantity.is_finite()
                if isinstance(self.stock_quantity, Decimal) else isfinite(self.stock_quantity)
            )
            if not finite or self.stock_quantity != int(self.stock_quantity):
                errors["stock_quantity"] = [
                    ValidationError("Stock must be a whole number.", code="invalid"),
                ]
        try:
            super().clean_fields(exclude=excluded | errors.keys())
        except ValidationError as error:
            error.update_error_dict(errors)
        if errors:
            raise ValidationError(errors)

    def clean(self) -> None:
        """Reject whitespace-only required text in addition to field validation."""
        super().clean()
        errors: dict[str, str] = {}
        for field in ("title", "author"):
            value = getattr(self, field)
            if isinstance(value, str) and value and not value.strip():
                errors[field] = "This field cannot contain only whitespace."
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Validate normal saves; bulk operations bypass Django model hooks."""
        self.full_clean()
        super().save(*args, **kwargs)
