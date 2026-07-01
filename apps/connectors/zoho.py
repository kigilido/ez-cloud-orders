"""
Zoho connector — pulls orders from Zoho CRM / Books / Inventory.

⚠️  AWAITING CLIENT CONFIRMATION:
  - Which Zoho product (CRM, Books, Inventory)?
  - Which module/table contains the orders?
  - Field mapping from Zoho fields → our InboundOrder fields

HOW TO ACTIVATE:
  1. Add to .env:
       ZOHO_CLIENT_ID=
       ZOHO_CLIENT_SECRET=
       ZOHO_REFRESH_TOKEN=
       ZOHO_ORG_ID=
       ZOHO_MODULE=Contacts   ← update to actual module name
  2. Run: python manage.py shell -c "from apps.connectors.zoho import ZohoConnector; ZohoConnector().sync()"
"""

import logging
import os
from typing import Any

import requests
from django.conf import settings

from apps.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_API_BASE = "https://www.zohoapis.com/crm/v3"


class ZohoConnector(BaseConnector):
    source_name = "zoho"

    def __init__(self) -> None:
        self.client_id = getattr(settings, "ZOHO_CLIENT_ID", "")
        self.client_secret = getattr(settings, "ZOHO_CLIENT_SECRET", "")
        self.refresh_token = getattr(settings, "ZOHO_REFRESH_TOKEN", "")
        self.org_id = getattr(settings, "ZOHO_ORG_ID", "")
        self.module = getattr(settings, "ZOHO_MODULE", "Contacts")  # TBD with client
        self._access_token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Exchange refresh token for a short-lived access token."""
        resp = requests.post(
            ZOHO_TOKEN_URL,
            params={
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    @property
    def access_token(self) -> str:
        if not self._access_token:
            self._access_token = self._get_access_token()
        return self._access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Zoho-oauthtoken {self.access_token}"}

    # ── Fetch ─────────────────────────────────────────────────────────────

    def fetch_records(self) -> list[dict[str, Any]]:
        """
        GET /crm/v3/{module}/search

        TODO: Update criteria once client confirms the Zoho module and
              the field name that marks an order as "active" / "current month".
        """
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.warning("ZohoConnector: credentials not configured — skipping sync.")
            return []

        records: list[dict] = []
        page = 1

        while True:
            resp = requests.get(
                f"{ZOHO_API_BASE}/{self.module}",
                headers=self._headers(),
                params={"page": page, "per_page": 200},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("data", [])
            records.extend(batch)

            if not data.get("info", {}).get("more_records"):
                break
            page += 1

        return records

    # ── Normalize ─────────────────────────────────────────────────────────

    def normalize(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Map Zoho fields → InboundOrder fields.

        TODO: Update field names once client confirms the Zoho module structure.
              Current mapping is a placeholder — adjust keys to match actual Zoho fields.
        """
        return {
            "external_id": str(record.get("id", "")),
            # TODO: replace with actual Zoho phone field name
            "phone_number": self._clean_phone(record.get("Phone", "") or record.get("Mobile", "")),
            "raw_data": record,
        }

    @staticmethod
    def _clean_phone(phone: str) -> str:
        return "".join(c for c in str(phone) if c.isdigit())
