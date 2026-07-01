from django.urls import path

from apps.customers import views

app_name = "customers"

urlpatterns = [
    path("search/", views.search_by_phone, name="search"),
]
