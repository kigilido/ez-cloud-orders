import logging
from datetime import date

from celery import shared_task

from apps.billing.services import billing_service

logger = logging.getLogger(__name__)


@shared_task(name="apps.billing.tasks.run_month_end")
def run_month_end() -> int | None:
    """
    Celery beat fires on days 28–31; only run on the actual last day of the month.
    """
    today = date.today()
    if not billing_service.is_last_day_of_month(today):
        logger.info("Skipping month-end: %s is not the last day of the month.", today)
        return None

    period_start, period_end = billing_service.resolve_period(reference=today)
    statement = billing_service.run(
        period_start=period_start,
        period_end=period_end,
    )
    return statement.pk
