import calendar
import logging
from datetime import date

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db.models import QuerySet
from django.utils import timezone

from apps.billing.models import Invoice, MonthEndStatement
from apps.billing.pdf import render_invoice_pdf, render_statement_pdf
from apps.orders.models import Order, OrderSource

logger = logging.getLogger(__name__)


class BillingService:
    """Generate invoices, consolidated statement, push to Zoho, and email reports."""

    def run(
        self,
        period_start: date | None = None,
        period_end: date | None = None,
        *,
        force: bool = False,
    ) -> MonthEndStatement:
        period_start, period_end = self.resolve_period(period_start, period_end)

        if not force:
            existing = MonthEndStatement.objects.filter(
                period_start=period_start,
                period_end=period_end,
                status="complete",
            ).first()
            if existing:
                logger.info(
                    "Month-end already complete for %s — %s",
                    period_start,
                    period_end,
                )
                return existing

        statement = MonthEndStatement.objects.create(
            period_start=period_start,
            period_end=period_end,
            status="running",
        )

        try:
            orders = self.get_orders_for_period(period_start, period_end)
            invoices = [self.generate_invoice(order) for order in orders]

            self.generate_statement_pdf(statement, orders, invoices)
            self.push_statement_to_zoho(statement, orders)
            self.email_source_reports(statement, orders, invoices)

            Order.objects.filter(pk__in=orders.values_list("pk", flat=True)).update(
                billed_at=timezone.now(),
            )

            statement.status = "complete"
            statement.save(update_fields=["status"])
        except Exception as exc:
            logger.exception("Month-end billing failed")
            statement.status = "error"
            statement.error_log = str(exc)
            statement.save(update_fields=["status", "error_log"])

        return statement

    @staticmethod
    def resolve_period(
        period_start: date | None = None,
        period_end: date | None = None,
        reference: date | None = None,
    ) -> tuple[date, date]:
        ref = reference or date.today()
        if period_end is None:
            last_day = calendar.monthrange(ref.year, ref.month)[1]
            period_end = ref.replace(day=last_day)
        if period_start is None:
            period_start = period_end.replace(day=1)
        return period_start, period_end

    @staticmethod
    def is_last_day_of_month(reference: date | None = None) -> bool:
        ref = reference or date.today()
        last_day = calendar.monthrange(ref.year, ref.month)[1]
        return ref.day == last_day

    @staticmethod
    def get_orders_for_period(period_start: date, period_end: date) -> QuerySet[Order]:
        return (
            Order.objects.filter(
                created_at__date__gte=period_start,
                created_at__date__lte=period_end,
            )
            .select_related("customer")
            .order_by("created_at")
        )

    def generate_invoice(self, order: Order) -> Invoice:
        invoice_number = order.invoice_number or f"INV-{order.pk:06d}"
        pdf_bytes = render_invoice_pdf(order, invoice_number)
        filename = f"{invoice_number}.pdf"

        invoice, created = Invoice.objects.get_or_create(
            order=order,
            defaults={"invoice_number": invoice_number},
        )
        if not created and invoice.invoice_number != invoice_number:
            invoice.invoice_number = invoice_number

        invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
        invoice.save()

        order.invoice_number = invoice.invoice_number
        order.save(update_fields=["invoice_number"])
        return invoice

    def generate_statement_pdf(
        self,
        statement: MonthEndStatement,
        orders: QuerySet[Order],
        invoices: list[Invoice],
    ) -> None:
        pdf_bytes = render_statement_pdf(statement, orders, invoices)
        filename = f"statement_{statement.period_start}_{statement.period_end}.pdf"
        statement.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    def push_statement_to_zoho(
        self,
        statement: MonthEndStatement,
        orders: QuerySet[Order],
    ) -> None:
        if not settings.ZOHO_CLIENT_ID:
            logger.warning("Zoho not configured; skipping statement push.")
            return
        # TODO: push consolidated statement PDF via Zoho API once product/module confirmed
        logger.info(
            "Would push statement %s (%s orders) to Zoho",
            statement.pk,
            orders.count(),
        )
        statement.pushed_to_zoho_at = timezone.now()
        statement.save(update_fields=["pushed_to_zoho_at"])

    def email_source_reports(
        self,
        statement: MonthEndStatement,
        orders: QuerySet[Order],
        invoices: list[Invoice],
    ) -> None:
        invoices_by_order = {invoice.order_id: invoice for invoice in invoices}
        emailed = False

        emailed |= self._email_invoices_for_source(
            orders.filter(source=OrderSource.SHAREPOINT),
            invoices_by_order,
            settings.SHAREPOINT_REPORT_EMAIL,
            "SharePoint",
        )
        emailed |= self._email_invoices_for_source(
            orders.filter(source=OrderSource.GOOGLE_DRIVE),
            invoices_by_order,
            settings.GOOGLE_DRIVE_REPORT_EMAIL,
            "Google Drive",
        )

        if emailed:
            statement.emailed_at = timezone.now()
            statement.save(update_fields=["emailed_at"])

    @staticmethod
    def _email_invoices_for_source(
        orders: QuerySet[Order],
        invoices_by_order: dict[int, Invoice],
        recipient: str,
        source_label: str,
    ) -> bool:
        if not orders.exists():
            return False
        if not recipient:
            logger.warning("No report email configured for %s; skipping.", source_label)
            return False

        period = orders.first().created_at.strftime("%B %Y")
        email = EmailMessage(
            subject=f"EZ Cloud Orders — {source_label} invoices ({period})",
            body=f"Attached are {orders.count()} invoice PDF(s) for {source_label} orders.",
            from_email=settings.EMAIL_HOST_USER or None,
            to=[recipient],
        )

        attached = 0
        for order in orders:
            invoice = invoices_by_order.get(order.pk)
            if invoice and invoice.pdf_file:
                email.attach(
                    invoice.pdf_file.name.split("/")[-1],
                    invoice.pdf_file.read(),
                    "application/pdf",
                )
                invoice.sent_at = timezone.now()
                invoice.save(update_fields=["sent_at"])
                attached += 1

        if attached:
            email.send(fail_silently=False)
            logger.info("Emailed %s %s invoice(s) to %s", attached, source_label, recipient)
            return True

        return False


billing_service = BillingService()
