"""The PDF's book payload, route contract and optional endpoints."""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Book


class ExamContractTests(APITestCase):
    def setUp(self) -> None:
        self.payload = {
            "title": "El Quijote", "author": "Miguel de Cervantes",
            "isbn": "978-84-376-0494-7", "cost_usd": "15.99",
            "selling_price_local": None, "stock_quantity": 25,
            "category": "Literatura Clásica", "supplier_country": "ES",
        }

    def create_book(self, **overrides: object) -> Book:
        return Book.objects.create(**{**self.payload, **overrides})

    def test_exact_exam_routes_are_registered(self) -> None:
        self.assertEqual(reverse("books:book-list"), "/books")
        self.assertEqual(reverse("books:book-detail", args=[1]), "/books/1")
        self.assertEqual(reverse("books:book-search"), "/books/search")
        self.assertEqual(reverse("books:book-low-stock"), "/books/low-stock")
        self.assertEqual(reverse("books:book-calculate-price", args=[1]), "/books/1/calculate-price")

    def test_pdf_example_payload_is_accepted_and_returned(self) -> None:
        response = self.client.post("/books", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["isbn"], "9788437604947")
        self.assertEqual(response.data["cost_usd"], "15.99")
        self.assertEqual(response.data["stock_quantity"], 25)
        self.assertEqual(response.data["supplier_country"], "ES")
        self.assertIsNone(response.data["selling_price_local"])
        self.assertNotIn("price", response.data)
        self.assertNotIn("stock", response.data)

    def test_formatted_isbn_cannot_duplicate_compact_isbn(self) -> None:
        self.create_book(isbn="9788437604947")
        response = self.client.post("/books", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("isbn", response.data)
        self.assertEqual(Book.objects.count(), 1)

    def test_lowercase_isbn_check_digit_and_country_are_normalized(self) -> None:
        response = self.client.post(
            "/books", {**self.payload, "isbn": "0-8044-2957-x", "supplier_country": "es"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["isbn"], "080442957X")
        self.assertEqual(response.data["supplier_country"], "ES")

    def test_invalid_supplier_country_returns_field_error(self) -> None:
        for country in ("ESP", "1E", "!", None):
            with self.subTest(country=country):
                response = self.client.post("/books", {**self.payload, "supplier_country": country}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("supplier_country", response.data)

    def test_selling_price_is_read_only(self) -> None:
        response = self.client.post("/books", {**self.payload, "selling_price_local": "999.99"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["selling_price_local"])
        book = Book.objects.get(pk=response.data["id"])
        book.selling_price_local = Decimal("19.03")
        book.save()
        response = self.client.patch(f"/books/{book.pk}", {"selling_price_local": "999.99"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book.refresh_from_db()
        self.assertEqual(book.selling_price_local, Decimal("19.03"))

    def test_changing_cost_invalidates_the_old_selling_price(self) -> None:
        book = self.create_book(selling_price_local=Decimal("19.03"))
        response = self.client.patch(f"/books/{book.pk}", {"cost_usd": "20.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["selling_price_local"])
        book.refresh_from_db()
        self.assertIsNone(book.selling_price_local)

    def test_changing_stock_preserves_calculated_price(self) -> None:
        book = self.create_book(selling_price_local=Decimal("19.03"))
        response = self.client.patch(f"/books/{book.pk}", {"stock_quantity": 3}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selling_price_local"], "19.03")

    def test_prefixed_routes_remain_available(self) -> None:
        book = self.create_book()
        response = self.client.get("/api/inventory/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], book.pk)
        response = self.client.get(f"/api/inventory/books/{book.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_route_filters_category_and_preserves_pagination(self) -> None:
        first = self.create_book()
        self.create_book(isbn="9780306406157")
        self.create_book(isbn="080442957X", category="Science")
        response = self.client.get("/books/search", {"category": "literatura clásica", "page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], first.pk)
        self.assertIsNotNone(response.data["next"])
        next_page = self.client.get(response.data["next"])
        self.assertEqual(len(next_page.data["results"]), 1)

    def test_search_requires_nonempty_category(self) -> None:
        for params in ({}, {"category": ""}, {"category": "  "}):
            with self.subTest(params=params):
                response = self.client.get("/books/search", params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("category", response.data)

    def test_low_stock_threshold_is_inclusive_and_configurable(self) -> None:
        zero = self.create_book(stock_quantity=0)
        five = self.create_book(isbn="9780306406157", stock_quantity=5)
        ten = self.create_book(isbn="080442957X", stock_quantity=10)
        self.create_book(isbn="9791234567896", stock_quantity=11)
        for params, expected in (
            ({}, [zero.pk, five.pk, ten.pk]),
            ({"threshold": 5}, [zero.pk, five.pk]),
            ({"threshold": 0}, [zero.pk]),
        ):
            with self.subTest(params=params):
                response = self.client.get("/books/low-stock", params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual([item["id"] for item in response.data["results"]], expected)

    def test_low_stock_supports_category_filter_and_pagination(self) -> None:
        self.create_book(stock_quantity=5)
        self.create_book(isbn="9780306406157", stock_quantity=0)
        self.create_book(isbn="080442957X", stock_quantity=5, category="Science")
        response = self.client.get("/books/low-stock", {"category": "Literatura Clásica", "page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)

    def test_invalid_threshold_returns_400(self) -> None:
        for threshold in ("-1", "bad", "1.5", "2147483648", ""):
            with self.subTest(threshold=threshold):
                for path, extra in (("/books/low-stock", {}), ("/books", {"low_stock": "true"})):
                    response = self.client.get(path, {"threshold": threshold, **extra})
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertIn("threshold", response.data)

    def test_list_low_stock_filter_uses_requested_threshold(self) -> None:
        matching = self.create_book(stock_quantity=5)
        self.create_book(isbn="9780306406157", stock_quantity=6)
        response = self.client.get("/books", {"low_stock": "true", "threshold": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [matching.pk])
