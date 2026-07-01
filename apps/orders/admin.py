from django.contrib import admin

from apps.orders.models import InboundOrder, Order


@admin.register(InboundOrder)
class InboundOrderAdmin(admin.ModelAdmin):
    list_display = ("external_id", "source", "phone_number", "customer", "synced_at")
    list_filter = ("source",)
    search_fields = ("external_id", "phone_number")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "customer", "source", "status", "created_at", "pos_order_id")
    list_filter = ("source", "status")
    search_fields = ("customer__last_name", "customer__phone_number", "pos_order_id")
