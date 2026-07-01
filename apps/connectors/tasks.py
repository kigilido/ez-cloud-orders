"""
Celery task for syncing all order sources.
Scheduled in config/celery.py to run every 30 minutes.
"""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(name="apps.connectors.tasks.sync_all_sources", bind=True, max_retries=3)
def sync_all_sources(self):
    """Sync all inbound order sources (Zoho, SharePoint, Google Drive)."""
    try:
        from apps.connectors.sync_service import sync_all_sources as run_sync
        results = run_sync()
        for source, (created, updated) in results.items():
            logger.info("Sync %s: +%d created, ~%d updated", source, created, updated)
        return results
    except Exception as exc:
        logger.error("sync_all_sources task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
