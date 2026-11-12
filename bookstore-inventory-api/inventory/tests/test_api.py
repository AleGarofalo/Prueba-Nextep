"""Book serialization and API behavior regression tests."""

from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Book
from inventory.serializers import BookSerializer


class BookAPITests(APITestCase):
    def setUp(self) -> None:
        self.url = reverse("books:book-list")
        self.payload = {
            "title": "Matilda",
            "author": "Roald Dahl",
            "isbn": "9780140328721",
            "cost_usd": "12.99",
            "stock_quantity": 5,
            "category": "Fiction",
            "supplier_country": "ES",
        }

    def create_book(self, **overrides: object) -> Book:
        values = {**self.payload, **overrides}
        return Book.objects.create(**values)

    def detail_url(self, book: Book) -> str:
        return reverse("books:book-detail", args=[book.pk])

    def test_create_returns_201_and_serializes_all_fields(self) -> None:
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data), {
            "id", "title", "author", "isbn", "cost_usd", "selling_price_local",
            "stock_quantity", "category", "supplier_country",
            "created_at", "updated_at",
        })
        self.assertEqual(response.data["cost_usd"], "12.99")
        book = Book.objects.get(pk=response.data["id"])
        self.assertEqual(book.isbn, self.payload["isbn"])
        self.assertEqual(book.stock_quantity, 5)

    def test_identifier_and_timestamps_are_read_only(self) -> None:
        payload = {
            **self.payload,
            "id": 987654,
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data["id"], payload["id"])
        self.assertNotEqual(response.data["created_at"], payload["created_at"])
        self.assertNotEqual(response.data["updated_at"], payload["updated_at"])

        book = Book.objects.get(pk=response.data["id"])
        created_at = book.created_at
        response = self.client.patch(self.detail_url(book), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(response.data["id"], book.pk)
        self.assertEqual(book.created_at, created_at)
        self.assertNotEqual(response.data["updated_at"], payload["updated_at"])

    def test_create_uses_model_defaults(self) -> None:
        payload = {key: value for key, value in self.payload.items() if key not in {"stock_quantity", "category"}}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["stock_quantity"], 0)
        self.assertIsNone(response.data["category"])

    def test_invalid_numeric_values_return_field_errors(self) -> None:
        for field, value in (
            ("cost_usd", "0"), ("cost_usd", "-0.01"), ("cost_usd", "0.001"),
            ("cost_usd", "100000000.00"), ("cost_usd", "NaN"), ("cost_usd", "Infinity"),
            ("stock_quantity", -1), ("stock_quantity", 1.5), ("stock_quantity", -0.5), ("stock_quantity", "bad"),
        ):
            with self.subTest(field=field, value=value):
                response = self.client.post(self.url, {**self.payload, field: value}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertFalse(Book.objects.exists())

    def test_positive_price_and_zero_stock_are_accepted(self) -> None:
        response = self.client.post(self.url, {**self.payload, "cost_usd": "0.01", "stock_quantity": 0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_required_text_and_isbn_return_400(self) -> None:
        for field, value in (("title", "  "), ("author", ""), ("isbn", "9780140328722")):
            with self.subTest(field=field):
                response = self.client.post(self.url, {**self.payload, field: value}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_missing_required_fields_return_400(self) -> None:
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"title", "author", "isbn", "cost_usd"})

    def test_duplicate_isbn_returns_400(self) -> None:
        self.create_book()
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("isbn", response.data)
        self.assertEqual(Book.objects.count(), 1)

    def test_retrieve_update_partial_update_and_delete_statuses(self) -> None:
        book = self.create_book()
        url = self.detail_url(book)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], book.pk)

        response = self.client.put(url, {**self.payload, "cost_usd": "15.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cost_usd"], "15.00")

        response = self.client.patch(url, {"stock_quantity": 0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.cost_usd, Decimal("15.00"))
        self.assertEqual(book.stock_quantity, 0)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")
        self.assertFalse(Book.objects.filter(pk=book.pk).exists())

    def test_invalid_partial_update_preserves_existing_values(self) -> None:
        book = self.create_book()
        response = self.client.patch(self.detail_url(book), {"stock_quantity": -1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        book.refresh_from_db()
        self.assertEqual(book.stock_quantity, 5)

    def test_model_validation_errors_return_400_on_create_and_update(self) -> None:
        book = self.create_book()
        with patch.object(Book, "clean", side_effect=DjangoValidationError({"stock_quantity": "Inventory rule failed."})):
            response = self.client.post(self.url, {**self.payload, "isbn": "9780306406157"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("stock_quantity", response.data)
            response = self.client.patch(self.detail_url(book), {"stock_quantity": 2}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("stock_quantity", response.data)
        book.refresh_from_db()
        self.assertEqual(book.stock_quantity, 5)
        self.assertEqual(Book.objects.count(), 1)

    def test_non_field_model_validation_errors_return_400(self) -> None:
        with patch.object(Book, "clean", side_effect=DjangoValidationError("Inventory rule failed.")):
            response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_missing_book_returns_404_for_detail_operations(self) -> None:
        url = reverse("books:book-detail", args=[987654])
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_list_has_paginated_response(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"count": 0, "next": None, "previous": None, "results": []})

    def test_category_filter_is_case_insensitive_and_matches_whole_category(self) -> None:
        matching = self.create_book(category="Fiction")
        self.create_book(isbn="9780306406157", category="Science Fiction")
        self.create_book(isbn="080442957X", category=None)
        response = self.client.get(self.url, {"category": "fiction"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], matching.pk)

    def test_low_stock_includes_zero_and_ten_and_excludes_eleven(self) -> None:
        zero = self.create_book(stock_quantity=0)
        five = self.create_book(isbn="9780306406157", stock_quantity=10)
        self.create_book(isbn="080442957X", stock_quantity=11)
        for value in ("true", "1", "TRUE"):
            with self.subTest(value=value):
                response = self.client.get(self.url, {"low_stock": value})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual([item["id"] for item in response.data["results"]], [zero.pk, five.pk])
        for value in ("false", "0"):
            with self.subTest(value=value):
                response = self.client.get(self.url, {"low_stock": value})
                self.assertEqual(response.data["count"], 3)

    def test_category_and_low_stock_filters_combine(self) -> None:
        matching = self.create_book(category="Fiction", stock_quantity=5)
        self.create_book(isbn="9780306406157", category="Fiction", stock_quantity=11)
        self.create_book(isbn="080442957X", category="Science", stock_quantity=0)
        response = self.client.get(self.url, {"category": "Fiction", "low_stock": "true"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], matching.pk)

    def test_invalid_low_stock_filter_returns_400(self) -> None:
        response = self.client.get(self.url, {"low_stock": "maybe"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("low_stock", response.data)

    def test_unmatched_filters_return_empty_results(self) -> None:
        self.create_book()
        response = self.client.get(self.url, {"category": "Unknown"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_pagination_is_ordered_and_has_working_navigation(self) -> None:
        first = self.create_book()
        second = self.create_book(isbn="9780306406157")
        response = self.client.get(self.url, {"page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], first.pk)
        self.assertIsNone(response.data["previous"])
        response = self.client.get(response.data["next"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], second.pk)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_pagination_defaults_to_twenty_and_caps_page_size(self) -> None:
        books = []
        for index in range(101):
            prefix = f"97800000{index:04d}"
            total = sum(int(digit) * (1 if position % 2 == 0 else 3) for position, digit in enumerate(prefix))
            isbn = prefix + str((-total) % 10)
            books.append(Book(**{**self.payload, "isbn": isbn}))
        Book.objects.bulk_create(books)
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 101)
        self.assertEqual(len(response.data["results"]), 20)
        response = self.client.get(self.url, {"page_size": 1000})
        self.assertEqual(len(response.data["results"]), 100)

    def test_invalid_page_returns_404(self) -> None:
        response = self.client.get(self.url, {"page": 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_serializer_supports_partial_updates(self) -> None:
        book = self.create_book()
        serializer = BookSerializer(book, data={"stock_quantity": 0}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        book.refresh_from_db()
        self.assertEqual(book.stock_quantity, 0)
        self.assertEqual(book.title, self.payload["title"])
