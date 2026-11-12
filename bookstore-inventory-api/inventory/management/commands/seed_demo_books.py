"""Repeatable fictional inventory for manual API testing."""

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Book

DEMO_BOOK_COUNT = 25
CATEGORIES = ("Literatura Clásica", "Ciencia", "Tecnología", "Historia", "Ficción")
STOCK_LEVELS = (0, 5, 10, 11, 25)
COUNTRIES = ("ES", "US", "GB", "AR", "MX")


def demo_isbn(index: int) -> str:
    """Build a deterministic ISBN-13 with a valid check digit for demo records."""
    body = f"97809999{index:04d}"
    total = sum(int(digit) * (1 if position % 2 == 0 else 3) for position, digit in enumerate(body))
    return body + str((-total) % 10)


def demo_books() -> Iterator[dict[str, Any]]:
    for index in range(DEMO_BOOK_COUNT):
        category = CATEGORIES[index % len(CATEGORIES)]
        yield {
            "isbn": demo_isbn(index + 1),
            "title": f"Demo {index + 1:02d}: {category}",
            "author": f"Autor de prueba {index + 1:02d}",
            "cost_usd": Decimal("5.00") + Decimal(index + 1) * Decimal("1.25"),
            "stock_quantity": STOCK_LEVELS[(index + index // len(CATEGORIES)) % len(STOCK_LEVELS)],
            "category": category,
            "supplier_country": COUNTRIES[index % len(COUNTRIES)],
        }


class Command(BaseCommand):
    help = "Create 25 fictional demo books without overwriting existing records."

    def handle(self, *args: Any, **options: Any) -> None:
        created_count = 0
        with transaction.atomic():
            for values in demo_books():
                isbn = values.pop("isbn")
                _, created = Book.objects.get_or_create(isbn=isbn, defaults=values)
                created_count += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Demo books created: {created_count}; already present: {DEMO_BOOK_COUNT - created_count}."
        ))
