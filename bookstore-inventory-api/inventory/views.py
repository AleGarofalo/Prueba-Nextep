"""Book CRUD endpoints, filtering and pagination."""

from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, F, Max, Q, QuerySet, Sum
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Book
from .serializers import (
    BookSerializer, CalculatePriceSerializer, CategorySearchSerializer, DisplayCurrencySerializer,
    StockThresholdSerializer, model_validation_error,
)
from .services import (
    MARGIN_PERCENTAGE, ExchangeRateUnavailable, UnsupportedCurrency,
    calculate_and_save_book_price, get_display_exchange_rate,
)
from .validators import normalize_isbn


class PricingUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Exchange rates are temporarily unavailable. Please try again later."
    default_code = "exchange_rate_unavailable"


class BookPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BookViewSet(ModelViewSet):
    """Manage books; filter with category and low_stock=true query parameters."""

    queryset = Book.objects.all().order_by("id")
    serializer_class = BookSerializer
    pagination_class = BookPagination

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        values = Book.objects.aggregate(
            total_titles=Count("id"),
            inventory_value_usd=Sum(
                F("cost_usd") * F("stock_quantity"),
                output_field=DecimalField(max_digits=30, decimal_places=2),
            ),
            low_stock_titles=Count("id", filter=Q(stock_quantity__lte=10)),
            out_of_stock_titles=Count("id", filter=Q(stock_quantity=0)),
            last_updated_at=Max("updated_at"),
        )
        values["inventory_value_usd"] = format(values["inventory_value_usd"] or Decimal("0"), ".2f")
        values["last_updated_at"] = values["last_updated_at"].isoformat() if values["last_updated_at"] else None
        values["local_currency"] = settings.LOCAL_CURRENCY
        values["margin_percentage"] = MARGIN_PERCENTAGE
        values["categories"] = list(
            Book.objects.exclude(category__isnull=True).exclude(category="")
            .values_list("category", flat=True).order_by("category").distinct()
        )
        return Response(values)

    @action(detail=False, methods=["get"], url_path="exchange-rate")
    def exchange_rate(self, request: Request) -> Response:
        serializer = DisplayCurrencySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            quote = get_display_exchange_rate(serializer.validated_data["currency"])
        except UnsupportedCurrency as error:
            raise ValidationError({"currency": str(error)}) from error
        except ExchangeRateUnavailable as error:
            raise PricingUnavailable() from error
        return Response({
            "currency": quote.currency,
            "local_currency": quote.local_currency,
            "conversion_rate": str(quote.conversion_rate),
            "rate_source": quote.rate_source,
            "rates_fetched_at": quote.rates_fetched_at.isoformat() if quote.rates_fetched_at else None,
            "is_fallback": quote.rate_source in {"default", "stale_cache"},
        })

    @action(detail=True, methods=["post"], url_path="calculate-price", serializer_class=CalculatePriceSerializer)
    def calculate_price(self, request: Request, pk: str | None = None) -> Response:
        book = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        currency = serializer.validated_data["target_currency"]
        try:
            quote = calculate_and_save_book_price(book.pk, currency)
        except UnsupportedCurrency as error:
            raise ValidationError({"target_currency": str(error)}) from error
        except ExchangeRateUnavailable as error:
            raise PricingUnavailable() from error
        except Book.DoesNotExist as error:
            raise NotFound("Book not found.") from error
        except DjangoValidationError as error:
            raise model_validation_error(error) from error

        return Response({
            "book_id": book.pk,
            "cost_usd": format(quote.cost_usd, ".2f"),
            "exchange_rate": str(quote.exchange_rate),
            "cost_local": format(quote.cost_local, ".2f"),
            "margin_percentage": MARGIN_PERCENTAGE,
            "selling_price_local": format(quote.selling_price_local, ".2f"),
            "currency": quote.currency,
            "calculation_timestamp": quote.calculation_timestamp.isoformat(),
            "rate_source": quote.rate_source,
            "rates_fetched_at": quote.rates_fetched_at.isoformat() if quote.rates_fetched_at else None,
            "is_fallback": quote.rate_source in {"stale_cache", "default"},
            "provider": "ExchangeRate-API",
            "provider_url": "https://www.exchangerate-api.com",
        })

    @action(detail=False, methods=["get"])
    def search(self, request: Request) -> Response:
        serializer = CategorySearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return self.list(request)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request: Request) -> Response:
        serializer = StockThresholdSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        queryset = self.filter_queryset(self.get_queryset()).filter(
            stock_quantity__lte=serializer.validated_data["threshold"],
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    def get_queryset(self) -> QuerySet[Book]:
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category is not None:
            queryset = queryset.filter(category__iexact=category.strip())

        search = self.request.query_params.get("search", "").strip()
        if len(search) > 255:
            raise ValidationError({"search": "Search must be at most 255 characters."})
        if search:
            condition = Q(title__icontains=search) | Q(author__icontains=search)
            isbn_query = normalize_isbn(search)
            if isbn_query and all(character in "0123456789X" for character in isbn_query):
                condition |= Q(isbn__icontains=isbn_query)
            queryset = queryset.filter(condition)

        ordering = self.request.query_params.get("ordering", "id")
        if ordering not in {"id", "-id"}:
            raise ValidationError({"ordering": "Use id or -id."})
        queryset = queryset.order_by(ordering)

        low_stock = self.request.query_params.get("low_stock")
        if low_stock is not None:
            low_stock = low_stock.strip().lower()
            if low_stock not in {"true", "false", "1", "0"}:
                raise ValidationError({"low_stock": "Use true, false, 1 or 0."})
            if low_stock in {"true", "1"}:
                serializer = StockThresholdSerializer(data=self.request.query_params)
                serializer.is_valid(raise_exception=True)
                queryset = queryset.filter(stock_quantity__lte=serializer.validated_data["threshold"])

        return queryset
