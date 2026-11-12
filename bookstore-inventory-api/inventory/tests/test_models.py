"""Book validation and persistence regression tests."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from inventory.models import Book
from inventory.validators import validate_isbn


class BookTests(TestCase):
    def make_book(self, **overrides: object) -> Book:
        values: dict[str, object] = {
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "isbn": "9780140328721",
            "cost_usd": Decimal("12.99"),
        }
        values.update(overrides)
        return Book(**values)

    def test_create_defaults_and_string_representation(self) -> None:
        book = self.make_book()
        book.save()
        book.refresh_from_db()

        self.assertEqual(book.stock_quantity, 0)
        self.assertIsNone(book.category)
        self.assertEqual(book.cost_usd, Decimal("12.99"))
        self.assertEqual(str(book), "The Hobbit by J. R. R. Tolkien")
        self.assertIsNotNone(book.created_at)
        self.assertIsNotNone(book.updated_at)

    def test_valid_isbn_formats_and_checksums(self) -> None:
        for isbn in ("0306406152", "080442957X", "9780306406157", "9791234567896"):
            with self.subTest(isbn=isbn):
                self.make_book(isbn=isbn).full_clean()

    def test_invalid_isbn_formats_and_checksums(self) -> None:
        for isbn in (
            "0306406153", "0804429570", "9780306406158", "9791234567897",
            "1234567890128", "978030640615", "97803064061570", "030640615",
            "978-0306406158", "03064 6152", "X804429570",
            "９７８０３０６４０６１５７", "", None,
        ):
            with self.subTest(isbn=isbn):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(isbn=isbn).full_clean()
                self.assertIn("isbn", caught.exception.message_dict)

    def test_validator_exposes_error_code(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            validate_isbn("9780306406158")
        self.assertEqual(caught.exception.code, "invalid_isbn")

    def test_isbn_separators_and_lowercase_check_digit_are_normalized(self) -> None:
        for isbn, expected in (
            ("978-84-376-0494-7", "9788437604947"),
            ("0 8044 2957 x", "080442957X"),
            ("9780306406157\n", "9780306406157"),
        ):
            with self.subTest(isbn=isbn):
                book = self.make_book(isbn=isbn)
                book.save()
                book.refresh_from_db()
                self.assertEqual(book.isbn, expected)

    def test_isbn_uniqueness_is_checked_after_normalization(self) -> None:
        self.make_book(isbn="9788437604947").save()
        with self.assertRaises(ValidationError) as caught:
            self.make_book(isbn="978-84-376-0494-7").save()
        self.assertIn("isbn", caught.exception.message_dict)

    def test_supplier_country_is_normalized_and_validated(self) -> None:
        book = self.make_book(supplier_country="es")
        book.save()
        book.refresh_from_db()
        self.assertEqual(book.supplier_country, "ES")
        for country in ("ESP", "1E", "!"):
            with self.subTest(country=country):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(supplier_country=country).full_clean()
                self.assertIn("supplier_country", caught.exception.message_dict)

    def test_selling_price_is_nullable_and_cannot_be_negative(self) -> None:
        book = self.make_book()
        book.save()
        self.assertIsNone(book.selling_price_local)
        with self.assertRaises(ValidationError) as caught:
            self.make_book(selling_price_local=Decimal("-0.01")).full_clean()
        self.assertIn("selling_price_local", caught.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Book.objects.filter(pk=book.pk).update(selling_price_local=Decimal("-0.01"))

    def test_title_and_author_are_required_and_limited(self) -> None:
        for field in ("title", "author"):
            for value in ("", None, " \t\n", "a" * 256):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError) as caught:
                        self.make_book(**{field: value}).full_clean()
                    self.assertIn(field, caught.exception.message_dict)

    def test_clean_rejects_whitespace_only_text(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            self.make_book(title="   ", author="\t").clean()
        self.assertEqual(set(caught.exception.message_dict), {"title", "author"})

    def test_price_rejects_nonpositive_values_and_invalid_precision(self) -> None:
        for price in ("0", "-0.01", "0.001", "100000000.00", "NaN", "Infinity", "bad"):
            with self.subTest(cost_usd=price):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(cost_usd=price).full_clean()
                self.assertIn("cost_usd", caught.exception.message_dict)

    def test_price_accepts_supported_boundaries(self) -> None:
        for price in (Decimal("0.01"), Decimal("99999999.99")):
            with self.subTest(cost_usd=price):
                self.make_book(cost_usd=price).full_clean()

    def test_stock_requires_nonnegative_values(self) -> None:
        for stock in (-1, "-2", None, "bad"):
            with self.subTest(stock_quantity=stock):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(stock_quantity=stock).full_clean()
                self.assertIn("stock_quantity", caught.exception.message_dict)
        for stock in (0, 1, 100):
            with self.subTest(stock_quantity=stock):
                self.make_book(stock_quantity=stock).full_clean()

    def test_stock_does_not_silently_truncate_fractional_values(self) -> None:
        for stock in (
            -0.5, 1.5, Decimal("2.5"), float("nan"), float("inf"),
            Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
        ):
            with self.subTest(stock_quantity=stock):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(stock_quantity=stock).full_clean()
                self.assertIn("stock_quantity", caught.exception.message_dict)

    def test_category_is_optional_and_limited(self) -> None:
        for category in (None, "", "Fiction", "a" * 100):
            with self.subTest(category=category):
                self.make_book(category=category).full_clean()
        with self.assertRaises(ValidationError) as caught:
            self.make_book(category="a" * 101).full_clean()
        self.assertIn("category", caught.exception.message_dict)

    def test_duplicate_isbn_is_rejected_on_save(self) -> None:
        self.make_book().save()
        with self.assertRaises(ValidationError) as caught:
            self.make_book(title="Duplicate edition").save()
        self.assertIn("isbn", caught.exception.message_dict)
        self.assertEqual(Book.objects.count(), 1)

    def test_updates_allow_unchanged_isbn_and_update_timestamp(self) -> None:
        book = self.make_book()
        book.save()
        created_at = book.created_at
        next_update = book.updated_at + timedelta(seconds=1)
        with patch("django.utils.timezone.now", return_value=next_update):
            book.stock_quantity = 2
            book.save()
        book.refresh_from_db()
        self.assertEqual(book.created_at, created_at)
        self.assertEqual(book.updated_at, next_update)
        self.assertEqual(book.stock_quantity, 2)

    def test_save_validates_fields_and_model_clean_before_persistence(self) -> None:
        for values, field in (({"cost_usd": 0}, "cost_usd"), ({"title": "   "}, "title")):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as caught:
                    self.make_book(**values).save()
                self.assertIn(field, caught.exception.message_dict)
        self.assertFalse(Book.objects.exists())

    def test_database_constraints_prevent_invalid_bulk_updates(self) -> None:
        book = self.make_book()
        book.save()
        for values in ({"cost_usd": 0}, {"cost_usd": Decimal("-0.01")}, {"stock_quantity": -1}):
            with self.subTest(values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Book.objects.filter(pk=book.pk).update(**values)
        book.refresh_from_db()
        self.assertEqual(book.cost_usd, Decimal("12.99"))
        self.assertEqual(book.stock_quantity, 0)

    def test_database_constraint_prevents_duplicate_bulk_inserts(self) -> None:
        self.make_book().save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Book.objects.bulk_create([self.make_book()])
