"""Project URL configuration."""

from django.urls import include, path

from inventory.urls import exam_urlpatterns

urlpatterns = [
    path("", include((exam_urlpatterns, "books"), namespace="books")),
    path("api/inventory/", include("inventory.urls")),
]
