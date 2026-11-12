"""Inventory API routes."""

from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import BookViewSet

app_name = "inventory"
router = DefaultRouter()
router.register("books", BookViewSet, basename="book")

urlpatterns = router.urls

# Exact exam paths, without a required trailing slash.
exam_router = SimpleRouter(trailing_slash=False)
exam_router.register("books", BookViewSet, basename="book")
exam_urlpatterns = exam_router.urls
