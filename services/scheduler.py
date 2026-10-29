import atexit
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask

from services.pipeline_runtime import scheduled_pipeline_job
from services.settings import load_settings

SCHEDULER_KEY = "scheduler"


def init_scheduler(app: Flask) -> None:
    if not app.config.get("SCHEDULER_ENABLED"):
        app.extensions[SCHEDULER_KEY] = None
        return

    scheduler = BackgroundScheduler()
    scheduler.start()
    app.extensions[SCHEDULER_KEY] = scheduler

    def shutdown() -> None:
        if scheduler.running:
            scheduler.shutdown(wait=False)

    atexit.register(shutdown)
    configure_cronjob(app)


def get_scheduler(app: Flask) -> Optional[BackgroundScheduler]:
    return app.extensions.get(SCHEDULER_KEY)


def configure_cronjob(app: Flask) -> None:
    scheduler = get_scheduler(app)
    if not scheduler:
        return

    settings = load_settings()
    scheduler.remove_all_jobs()

    if not settings.get("cronjob_enabled", False):
        print("[CRONJOB] Cronjob is disabled")
        return

    interval_hours = settings.get("cronjob_interval_hours", 24)
    job_time = settings.get("cronjob_time", "09:00")

    try:
        hour, minute = map(int, job_time.split(":"))

        if interval_hours == 24:
            trigger = CronTrigger(hour=hour, minute=minute)
        else:
            trigger = CronTrigger(hour=f"*/{interval_hours}", minute=minute)

        job_fn: Callable[[], None] = lambda: _cron_job_with_context(app)
        scheduler.add_job(job_fn, trigger, id="pipeline_cronjob", replace_existing=True)
        print(f"[CRONJOB] Scheduled to run every {interval_hours} hours starting at {job_time}")
    except Exception as e:
        print(f"[CRONJOB] Error configuring cronjob: {e}")


def _cron_job_with_context(app: Flask) -> None:
    with app.app_context():
        scheduled_pipeline_job(app)
