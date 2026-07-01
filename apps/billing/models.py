from django.db import models


class Invoice(models.Model):
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="invoice",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="invoices/")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return self.invoice_number


class MonthEndStatement(models.Model):
    period_start = models.DateField()
    period_end = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    pushed_to_zoho_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    error_log = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to="statements/", blank=True)

    class Meta:
        ordering = ["-period_end"]

    def __str__(self) -> str:
        return f"Statement {self.period_start} — {self.period_end}"
