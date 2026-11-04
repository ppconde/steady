"""Scheduled reviews at REVIEW_TIMES, skipped when no new data has synced."""
import logging
import threading
import time
from datetime import date, datetime

from . import config, influx, store
from .analysis.report import build_report
from .findings import findings
from .writer import write_review

log = logging.getLogger(__name__)


def run_review(src, start: date | None, end: date, kind: str) -> int:
    fp = src.fingerprint()
    report = build_report(src, end, start)
    fs = findings(report)
    text, source = write_review(fs, report)
    return store.save_review(start, end, kind, text, source, fp)


def scheduled_tick(now: datetime, src=influx) -> bool:
    if now.astimezone(config.TZ).strftime("%H:%M") not in config.REVIEW_TIMES:
        return False
    if src.fingerprint() == store.last_fingerprint():
        return False
    end = now.astimezone(config.TZ).date()
    job = store.start_job(None, end)
    if job is None:
        return False
    review = None
    try:
        review = run_review(src, None, end, "scheduled")
    finally:
        store.finish_job(job, review)
    return True


def loop(src=influx) -> threading.Thread:
    def run():
        while True:
            try:
                scheduled_tick(datetime.now(config.TZ), src)
            except Exception:
                log.exception("scheduled review failed")
            time.sleep(30)

    t = threading.Thread(target=run, daemon=True, name="scheduler")
    t.start()
    return t
