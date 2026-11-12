"""Align the exam contract while preserving existing book costs and quantities."""

from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]

    operations = [
        migrations.RemoveConstraint(model_name="book", name="book_price_gt_zero"),
        migrations.RemoveConstraint(model_name="book", name="book_stock_gte_zero"),
        migrations.RenameField(model_name="book", old_name="price", new_name="cost_usd"),
        migrations.RenameField(model_name="book", old_name="stock", new_name="stock_quantity"),
        migrations.AlterField(
            model_name="book", name="cost_usd",
            field=models.DecimalField(
                max_digits=10, decimal_places=2,
                validators=[MinValueValidator(Decimal("0.01"), message="USD cost must be greater than 0.")],
            ),
        ),
        migrations.AddField(
            model_name="book", name="selling_price_local",
            field=models.DecimalField(
                max_digits=18, decimal_places=2, blank=True, null=True,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddField(
            model_name="book", name="supplier_country",
            field=models.CharField(
                max_length=2, blank=True, default="",
                validators=[RegexValidator(r"\A[A-Z]{2}\Z", "Use a two-letter country code, such as ES.")],
            ),
        ),
        migrations.AddConstraint(
            model_name="book",
            constraint=models.CheckConstraint(
                condition=models.Q(cost_usd__gt=0), name="book_cost_usd_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="book",
            constraint=models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0), name="book_stock_quantity_gte_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="book",
            constraint=models.CheckConstraint(
                condition=models.Q(selling_price_local__isnull=True) | models.Q(selling_price_local__gte=0),
                name="book_selling_price_gte_zero",
            ),
        ),
    ]
