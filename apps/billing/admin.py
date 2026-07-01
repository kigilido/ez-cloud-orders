from django.contrib import admin

from apps.billing.models import Invoice, MonthEndStatement


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "generated_at", "sent_at")
    search_fields = ("invoice_number",)


@admin.register(MonthEndStatement)
class MonthEndStatementAdmin(admin.ModelAdmin):
    list_display = ("period_start", "period_end", "status", "generated_at", "emailed_at")
    list_filter = ("status",)
    readonly_fields = ("generated_at", "pushed_to_zoho_at", "emailed_at", "error_log")
