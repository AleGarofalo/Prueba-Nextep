"""Project URL configuration; inventory routes will be added later."""

from django.urls import include, path

urlpatterns = [
    path("api/inventory/", include("inventory.urls")),
]
