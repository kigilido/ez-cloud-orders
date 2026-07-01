import logging
import uuid

from apps.connectors.base import BaseConnector
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class POSStubConnector(BaseConnector):
    """
    STUB — POS system not yet confirmed by client.
    create_order() logs to database and returns a placeholder ID.
    """

    def sync(self) -> list:
        return []

    def create_order(self, order: Order) -> str:
        placeholder_id = f"POS-STUB-{uuid.uuid4().hex[:12].upper()}"
        order.pos_order_id = placeholder_id
        order.status = "submitted"
        order.save(update_fields=["pos_order_id", "status"])
        logger.info("POS stub created order %s for Order #%s", placeholder_id, order.pk)
        return placeholder_id
