import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("ez_cloud_orders")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # ── Sync all order sources every 30 minutes ──────────────────────────
    # Pulls new records from Zoho, SharePoint, Google Drive → InboundOrder
    # Connectors with no credentials configured will log a warning and skip.
    "sync-all-sources": {
        "task": "apps.connectors.tasks.sync_all_sources",
        "schedule": timedelta(minutes=30),
    },

    # ── Month-end billing on last day of month at 23:59 ──────────────────
    # day_of_month="28-31" fires every day 28–31;
    # the task itself checks whether today is the actual last day.
    "run-month-end": {
        "task": "apps.billing.tasks.run_month_end",
        "schedule": crontab(hour=23, minute=59, day_of_month="28-31"),
    },
}

# Sensible defaults
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.timezone = "America/New_York"
app.conf.enable_utc = True

# Retry failed tasks with exponential back-off (max 3 retries)
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
