from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "phone_number", "valid_until", "family_number")
    search_fields = ("phone_number", "last_name", "first_name", "medicaid_id", "family_number")
    list_filter = ("valid_until",)
