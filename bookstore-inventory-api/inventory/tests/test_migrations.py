"""Verify the exam migration preserves existing costs, quantities and timestamps."""

from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class BookMigrationTests(TransactionTestCase):
    def test_existing_book_survives_field_renames(self) -> None:
        before = [("inventory", "0001_initial")]
        after = [("inventory", "0002_align_exam_book_fields")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(before)
            old_apps = executor.loader.project_state(before).apps
            old_book = old_apps.get_model("inventory", "Book").objects.create(
                title="Existing book", author="Existing author", isbn="9788437604947",
                price=Decimal("15.99"), stock=25, category="Classic",
            )
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new_apps = executor.loader.project_state(after).apps
            new_book = new_apps.get_model("inventory", "Book").objects.get(pk=old_book.pk)
            self.assertEqual(new_book.cost_usd, Decimal("15.99"))
            self.assertEqual(new_book.stock_quantity, 25)
            self.assertEqual(new_book.title, old_book.title)
            self.assertEqual(new_book.isbn, old_book.isbn)
            self.assertEqual(new_book.created_at, old_book.created_at)
            self.assertEqual(new_book.updated_at, old_book.updated_at)
            self.assertEqual(new_book.supplier_country, "")
            self.assertIsNone(new_book.selling_price_local)
        finally:
            MigrationExecutor(connection).migrate(after)
