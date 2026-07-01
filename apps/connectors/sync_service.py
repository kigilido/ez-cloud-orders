"""
Orchestrates syncing all configured connectors.
Called by the Celery beat task every 30 minutes.
"""

import logging

logger = logging.getLogger(__name__)


def sync_all_sources() -> dict[str, tuple[int, int]]:
    """
    Run sync() on every connector. Returns dict of {source: (created, updated)}.
    Connectors with missing credentials log a warning and return (0, 0).
    """
    from apps.connectors.google_drive import GoogleDriveConnector
    from apps.connectors.sharepoint import SharePointConnector
    from apps.connectors.zoho import ZohoConnector

    connectors = [
        ZohoConnector(),
        SharePointConnector(),
        GoogleDriveConnector(),
    ]

    results = {}
    for connector in connectors:
        try:
            created, updated = connector.sync()
            results[connector.source_name] = (created, updated)
        except Exception as exc:
            logger.error("sync_all_sources: connector %s raised: %s", connector.source_name, exc)
            results[connector.source_name] = (0, 0)

    return results
