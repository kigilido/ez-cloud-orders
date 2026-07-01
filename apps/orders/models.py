from django.conf import settings
from django.db import models


class OrderSource(models.TextChoices):
    ZOHO = "zoho", "Zoho"
    SHAREPOINT = "sharepoint", "SharePoint"
    GOOGLE_DRIVE = "google_drive", "Google Drive"
    OTHER = "other", "Other"


class InboundOrder(models.Model):
    source = models.CharField(max_length=20, choices=OrderSource.choices)
    external_id = models.CharField(max_length=200)
    customer = models.ForeignKey(
        "customers.Customer",
        null=True,
        on_delete=models.SET_NULL,
        related_name="inbound_orders",
    )
    phone_number = models.CharField(max_length=20)
    raw_data = models.JSONField()
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["source", "external_id"]
        ordering = ["-synced_at"]

    def __str__(self) -> str:
        return f"{self.get_source_display()} — {self.external_id}"


class Order(models.Model):
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    inbound_order = models.ForeignKey(
        InboundOrder,
        on_delete=models.PROTECT,
        related_name="outbound_orders",
    )
    source = models.CharField(max_length=20, choices=OrderSource.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    pos_order_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default="pending")
    invoice_number = models.CharField(max_length=50, blank=True)
    billed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.pk} — {self.customer}"
