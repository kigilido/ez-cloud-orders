from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("billing/month-end/", views.month_end, name="month_end"),
    path(
        "customer/<int:customer_id>/order/<int:inbound_order_id>/",
        views.order_confirm,
        name="order_confirm",
    ),
    path(
        "billing/statement/<int:statement_id>/",
        views.statement_detail,
        name="statement_detail",
    ),
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_add, name="user_add"),
    path("users/<int:user_id>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:user_id>/toggle/", views.user_toggle, name="user_toggle"),
]
