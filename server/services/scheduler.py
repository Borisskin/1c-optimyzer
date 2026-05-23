"""APScheduler — единый scheduler для cron-задач сервера.

Запускается при FastAPI startup, останавливается при shutdown.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("optimyzer.scheduler")
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    return _scheduler


def start() -> None:
    """Регистрирует все задачи и стартует scheduler.

    Импорты внутри функции — чтобы избежать circular imports и не загружать
    модули если scheduler выключен (например в тестах).
    """
    from api.db import SessionLocal
    from services.credits_service import deactivate_expired
    from services.recurring_billing import run_recurring_billing

    sched = get_scheduler()
    if sched.running:
        return

    # 03:00 МСК ежедневно — recurring Pro charges
    sched.add_job(
        run_recurring_billing,
        trigger="cron",
        hour=3,
        minute=0,
        id="recurring_billing",
        replace_existing=True,
        max_instances=1,
    )

    # 04:00 МСК ежедневно — деактивировать expired Credits
    def _deactivate_expired_credits():
        db = SessionLocal()
        try:
            n = deactivate_expired(db)
            logger.info("Deactivated %d expired credits packages", n)
        finally:
            db.close()

    sched.add_job(
        _deactivate_expired_credits,
        trigger="cron",
        hour=4,
        minute=0,
        id="deactivate_expired_credits",
        replace_existing=True,
        max_instances=1,
    )

    # 05:00 МСК ежедневно — удалить telemetry events старше 90 дней (Phase 1.6)
    def _telemetry_cleanup():
        from services.telemetry_service import cleanup_old_events
        db = SessionLocal()
        try:
            n = cleanup_old_events(db, max_age_days=90)
            logger.info("Telemetry cleanup removed %d events", n)
        finally:
            db.close()

    sched.add_job(
        _telemetry_cleanup,
        trigger="cron",
        hour=5,
        minute=0,
        id="telemetry_cleanup",
        replace_existing=True,
        max_instances=1,
    )

    sched.start()
    logger.info("APScheduler started, %d jobs", len(sched.get_jobs()))


def stop() -> None:
    sched = get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("APScheduler stopped")
