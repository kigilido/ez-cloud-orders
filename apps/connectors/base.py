"""
Abstract base class for all inbound order source connectors.
"""
from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Base class for all order source connectors.

    Subclasses must set:
      source_name: str  — must match an OrderSource choice value

    Subclasses must implement:
      fetch_records() -> list[dict]
      normalize(record) -> dict  (must include 'external_id' and 'phone_number')
    """

    source_name: str = ""

    @abstractmethod
    def fetch_records(self) -> list[dict[str, Any]]:
        """Pull raw records from the external source."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Map a raw source record to InboundOrder fields.

        Return dict must include:
          external_id: str
          phone_number: str
          raw_data: dict
        """
        raise NotImplementedError

    def sync(self) -> tuple[int, int]:
        """
        Fetch, normalize, and upsert all records into InboundOrder.
        Returns (created_count, updated_count).
        """
        from apps.orders.models import InboundOrder

        created = 0
        updated = 0

        try:
            records = self.fetch_records()
        except Exception as exc:
            logger.error("Connector %s failed to fetch records: %s", self.source_name, exc)
            return 0, 0

        for raw in records:
            try:
                normalized = self.normalize(raw)
                external_id = normalized.pop("external_id")
                _, is_new = InboundOrder.objects.update_or_create(
                    source=self.source_name,
                    external_id=external_id,
                    defaults=normalized,
                )
                if is_new:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                logger.error(
                    "Connector %s failed on record %s: %s",
                    self.source_name, raw, exc,
                )

        logger.info(
            "Connector %s sync complete: %d created, %d updated",
            self.source_name, created, updated,
        )
        return created, updated
