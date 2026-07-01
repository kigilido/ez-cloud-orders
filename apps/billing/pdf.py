import io

from django.template.loader import render_to_string
from xhtml2pdf import pisa

from apps.billing.models import Invoice, MonthEndStatement
from apps.orders.models import Order


def _write_pdf(html: str) -> bytes:
    buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=buffer)
    return buffer.getvalue()


def render_invoice_pdf(order: Order, invoice_number: str) -> bytes:
    html = render_to_string(
        "invoice.html",
        {"order": order, "invoice_number": invoice_number},
    )
    return _write_pdf(html)


def render_statement_pdf(
    statement: MonthEndStatement,
    orders,
    invoices: list[Invoice],
) -> bytes:
    html = render_to_string(
        "statement.html",
        {
            "statement": statement,
            "orders": orders,
            "invoices": invoices,
            "order_count": orders.count(),
            "invoice_count": len(invoices),
        },
    )
    return _write_pdf(html)
