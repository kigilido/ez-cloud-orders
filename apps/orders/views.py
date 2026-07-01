from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.orders.models import Order


@login_required
def order_list(request: HttpRequest) -> HttpResponse:
    orders = Order.objects.select_related("customer", "inbound_order").all()[:100]
    return render(request, "orders/order_list.html", {"orders": orders})
