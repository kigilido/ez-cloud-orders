"""
SharePoint connector — pulls order files from a SharePoint folder via Microsoft Graph API.

HOW TO ACTIVATE:
  1. Register an app in Azure Active Directory (app registration)
  2. Grant it: Sites.Read.All (or Files.Read.All) permission
  3. Add to .env:
       AZURE_TENANT_ID=
       AZURE_CLIENT_ID=
       AZURE_CLIENT_SECRET=
       SHAREPOINT_SITE_ID=      ← from Graph: /v1.0/sites?search=<site-name>
       SHAREPOINT_FOLDER_ID=    ← from Graph: /v1.0/sites/{site-id}/drive/root/children
  4. Run: python manage.py shell -c "from apps.connectors.sharepoint import SharePointConnector; SharePointConnector().sync()"
"""

import logging
from typing import Any

import requests
from django.conf import settings

from apps.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class SharePointConnector(BaseConnector):
    source_name = "sharepoint"

    def __init__(self) -> None:
        self.tenant_id = getattr(settings, "AZURE_TENANT_ID", "")
        self.client_id = getattr(settings, "AZURE_CLIENT_ID", "")
        self.client_secret = getattr(settings, "AZURE_CLIENT_SECRET", "")
        self.site_id = getattr(settings, "SHAREPOINT_SITE_ID", "")
        self.folder_id = getattr(settings, "SHAREPOINT_FOLDER_ID", "")
        self._access_token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        url = GRAPH_TOKEN_URL.format(tenant_id=self.tenant_id)
        resp = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
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
        return {"Authorization": f"Bearer {self.access_token}"}

    # ── Fetch ─────────────────────────────────────────────────────────────

    def fetch_records(self) -> list[dict[str, Any]]:
        """
        List all files in the configured SharePoint folder, download each one,
        and parse its content into records.
        """
        if not all([self.tenant_id, self.client_id, self.client_secret, self.site_id]):
            logger.warning("SharePointConnector: credentials not configured — skipping sync.")
            return []

        # List files in folder
        url = f"{GRAPH_API_BASE}/sites/{self.site_id}/drive/items/{self.folder_id}/children"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        files = resp.json().get("value", [])

        records: list[dict] = []
        for file_meta in files:
            try:
                file_records = self._parse_file(file_meta)
                records.extend(file_records)
            except Exception as exc:
                logger.error("SharePoint: failed to parse file %s: %s", file_meta.get("name"), exc)

        return records

    def _parse_file(self, file_meta: dict) -> list[dict]:
        """
        Download a file and parse it.

        TODO: Implement actual file parsing once client confirms file format
              (Excel, CSV, Word, etc.) and the column layout.

        Currently returns the file metadata as a single record placeholder.
        """
        file_id = file_meta.get("id", "")
        file_name = file_meta.get("name", "")

        # Download file content
        download_url = file_meta.get("@microsoft.graph.downloadUrl")
        if not download_url:
            content_url = f"{GRAPH_API_BASE}/sites/{self.site_id}/drive/items/{file_id}/content"
            resp = requests.get(content_url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            file_content = resp.content
        else:
            file_content = requests.get(download_url, timeout=30).content

        # TODO: parse file_content based on file type
        # For now, return a placeholder record using the file itself as the record
        return [
            {
                "_file_id": file_id,
                "_file_name": file_name,
                "_raw_bytes_length": len(file_content),
                # TODO: add actual fields once format is confirmed
                "Phone": "",
            }
        ]

    # ── Normalize ─────────────────────────────────────────────────────────

    def normalize(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        TODO: Update field mapping once client confirms the SharePoint file format.
        """
        return {
            "external_id": str(record.get("_file_id", "")),
            "phone_number": self._clean_phone(record.get("Phone", "")),
            "raw_data": record,
        }

    @staticmethod
    def _clean_phone(phone: str) -> str:
        return "".join(c for c in str(phone) if c.isdigit())
