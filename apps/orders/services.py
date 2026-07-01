from datetime import date

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q, QuerySet

from apps.connectors.pos_stub import POSStubConnector
from apps.core.utils import normalize_phone
from apps.customers.models import Customer
from apps.orders.models import InboundOrder, Order


def get_duplicate_orders(customer: Customer) -> QuerySet[Order]:
    """Return orders for this customer created in the current calendar month."""
    first_of_month = date.today().replace(day=1)
    return Order.objects.filter(
        customer=customer,
        created_at__date__gte=first_of_month,
    )


def has_duplicate_warning(customer: Customer) -> bool:
    return get_duplicate_orders(customer).exists()


def get_pending_inbound_orders(customer: Customer) -> QuerySet[InboundOrder]:
    """Inbound orders for this customer that do not yet have an outbound order."""
    normalized = normalize_phone(customer.phone_number)
    processed_ids = Order.objects.values_list("inbound_order_id", flat=True)
    phone_filter = Q(phone_number__icontains=normalized) if normalized else Q()
    return (
        InboundOrder.objects.filter(Q(customer=customer) | phone_filter)
        .exclude(pk__in=processed_ids)
        .distinct()
        .order_by("-synced_at")
    )


def create_order(
    *,
    customer: Customer,
    inbound_order: InboundOrder,
    created_by: AbstractBaseUser | None = None,
    force: bool = False,
) -> tuple[Order | None, str | None]:
    """
    Create an outbound order. Returns (order, error_message).
    When duplicates exist and force is False, returns (None, warning message).
    """
    if not force and has_duplicate_warning(customer):
        count = get_duplicate_orders(customer).count()
        return (
            None,
            f"This customer already has {count} order(s) this month. "
            "Confirm to proceed anyway.",
        )

    order = Order.objects.create(
        customer=customer,
        inbound_order=inbound_order,
        source=inbound_order.source,
        created_by=created_by,
    )
    POSStubConnector().create_order(order)
    return order, None
