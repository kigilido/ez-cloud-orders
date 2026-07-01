"""
Google Drive connector — reads order spreadsheets from a Google Drive folder.

Uses a Google Service Account (JSON key file) for authentication.

HOW TO ACTIVATE:
  1. Create a Google Cloud project, enable Drive API + Sheets API
  2. Create a Service Account, download the JSON key
  3. Share your Google Drive folder with the service account email
  4. Add to .env:
       GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
       GOOGLE_DRIVE_FOLDER_ID=    ← folder ID from the Drive URL
  5. pip install google-api-python-client google-auth --break-system-packages
  6. Run: python manage.py shell -c "from apps.connectors.google_drive import GoogleDriveConnector; GoogleDriveConnector().sync()"

KNOWN FIELDS (from client sample file):
  Family #, Medicaid ID, Last Name, First Name, Address,
  City/State/Zip, Phone, Valid Until, Date, Invoice #, Notes
"""

import logging
import os
from datetime import date
from typing import Any

from django.conf import settings

from apps.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class GoogleDriveConnector(BaseConnector):
    source_name = "google_drive"

    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]

    def __init__(self) -> None:
        self.service_account_json = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self.folder_id = getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", "")
        self._drive_service = None
        self._sheets_service = None

    # ── Auth ──────────────────────────────────────────────────────────────

    def _build_services(self):
        """Build authenticated Google API clients."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Google API client not installed. Run:\n"
                "pip install google-api-python-client google-auth --break-system-packages"
            )

        if not self.service_account_json or not os.path.exists(self.service_account_json):
            raise FileNotFoundError(
                f"Google service account JSON not found: {self.service_account_json!r}\n"
                "Set GOOGLE_SERVICE_ACCOUNT_JSON in your .env file."
            )

        creds = service_account.Credentials.from_service_account_file(
            self.service_account_json,
            scopes=self.SCOPES,
        )
        self._drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    @property
    def drive(self):
        if not self._drive_service:
            self._build_services()
        return self._drive_service

    @property
    def sheets(self):
        if not self._sheets_service:
            self._build_services()
        return self._sheets_service

    # ── Fetch ─────────────────────────────────────────────────────────────

    def fetch_records(self) -> list[dict[str, Any]]:
        """List all Google Sheets in the configured folder and read their rows."""
        if not self.service_account_json or not self.folder_id:
            logger.warning("GoogleDriveConnector: credentials not configured — skipping sync.")
            return []

        # List spreadsheet files in the folder
        result = (
            self.drive.files()
            .list(
                q=(
                    f"'{self.folder_id}' in parents "
                    "and mimeType='application/vnd.google-apps.spreadsheet' "
                    "and trashed=false"
                ),
                fields="files(id, name)",
            )
            .execute()
        )
        files = result.get("files", [])

        all_records: list[dict] = []
        for f in files:
            try:
                rows = self._read_sheet(f["id"], f["name"])
                all_records.extend(rows)
            except Exception as exc:
                logger.error("GoogleDrive: failed to read sheet %s: %s", f.get("name"), exc)

        return all_records

    def _read_sheet(self, spreadsheet_id: str, sheet_name: str) -> list[dict]:
        """Read all rows from a Google Sheet and return list of dicts."""
        result = (
            self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="A1:Z")
            .execute()
        )
        values = result.get("values", [])
        if len(values) < 2:
            return []  # No data rows

        # First row = headers
        headers = [h.strip() for h in values[0]]
        records = []
        for row_idx, row in enumerate(values[1:], start=2):
            # Pad row to header length
            padded = row + [""] * (len(headers) - len(row))
            record = dict(zip(headers, padded))
            record["_spreadsheet_id"] = spreadsheet_id
            record["_row_index"] = row_idx
            records.append(record)

        return records

    # ── Normalize ─────────────────────────────────────────────────────────

    def normalize(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Map Google Drive sheet columns → InboundOrder fields.

        Known columns from client sample:
          Family #, Medicaid ID, Last Name, First Name, Address,
          City/State/Zip, Phone, Valid Until, Date, Invoice #, Notes
        """
        spreadsheet_id = record.get("_spreadsheet_id", "")
        row_index = record.get("_row_index", 0)

        # Unique ID: spreadsheet + row
        external_id = f"{spreadsheet_id}:row{row_index}"

        return {
            "external_id": external_id,
            "phone_number": self._clean_phone(record.get("Phone", "")),
            "raw_data": record,
        }

    @staticmethod
    def _clean_phone(phone: str) -> str:
        return "".join(c for c in str(phone) if c.isdigit())
