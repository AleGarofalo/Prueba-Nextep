"""Demo seeding must be repeatable and preserve existing inventory edits."""

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from inventory.management.commands.seed_demo_books import DEMO_BOOK_COUNT, demo_isbn
from inventory.models import Book


class DemoDataTests(TestCase):
    def test_running_seed_twice_preserves_records_and_timestamps(self) -> None:
        call_command("seed_demo_books", stdout=StringIO())
        before = list(Book.objects.order_by("id").values())
        self.assertEqual(len(before), DEMO_BOOK_COUNT)
        call_command("seed_demo_books", stdout=StringIO())
        self.assertEqual(list(Book.objects.order_by("id").values()), before)

    def test_existing_books_and_edited_demo_books_are_not_overwritten(self) -> None:
        user_book = Book.objects.create(
            title="My book", author="My author", isbn="9788437604947",
            cost_usd=Decimal("15.99"), stock_quantity=25,
        )
        edited_demo = Book.objects.create(
            title="Edited demo", author="Edited author", isbn=demo_isbn(1),
            cost_usd=Decimal("25.00"), stock_quantity=99,
            selling_price_local=Decimal("40.00"), category="My category", supplier_country="GB",
        )
        existing_ids = (user_book.pk, edited_demo.pk)
        before = list(Book.objects.filter(pk__in=existing_ids).order_by("id").values())
        call_command("seed_demo_books", stdout=StringIO())
        after = list(Book.objects.filter(pk__in=existing_ids).order_by("id").values())
        self.assertEqual(after, before)
        self.assertEqual(Book.objects.count(), DEMO_BOOK_COUNT + 1)
