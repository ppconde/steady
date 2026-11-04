import sqlite3
from datetime import date, datetime, timedelta, timezone

from steady import config, store

D = date(2026, 11, 2)


def test_single_job_at_a_time():
    j = store.start_job(None, D)
    assert j is not None and store.start_job(None, D) is None
    store.finish_job(j, None)
    assert store.get_job(j)["status"] == "done"
    assert store.start_job(None, D) is not None


def test_stale_job_recovered():
    store.start_job(None, D)
    old = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(config.DB_PATH) as c:
        c.execute("UPDATE jobs SET created_at = ?", (old,))
    assert store.start_job(None, D) is not None


def test_review_for_week_picks_last_week_review():
    mon = date(2026, 11, 2)
    a = store.save_review(mon, D, "week", "first", "template", "1", now=datetime(2026, 11, 3, 7, 30, tzinfo=timezone.utc))
    b = store.save_review(mon, D, "week", "second", "claude", "2", now=datetime(2026, 11, 4, 7, 30, tzinfo=timezone.utc))
    store.save_review(D, D, "custom", "c", "claude", "2", now=datetime(2026, 11, 5, 7, 30, tzinfo=timezone.utc))
    assert store.review_for_week(mon)["id"] == b != a
    assert store.review_for_week(mon - timedelta(days=7)) is None
    assert [r["text"] for r in store.custom_reviews()] == ["c"]


def test_get_job_reports_stale_as_done():
    j = store.start_job(None, D)
    old = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(config.DB_PATH) as c:
        c.execute("UPDATE jobs SET created_at = ?", (old,))
    assert store.get_job(j)["status"] == "done"


def test_startup_clears_running_jobs():
    j = store.start_job(None, D)
    store.clear_running()
    assert store.get_job(j)["status"] == "done"
    assert store.start_job(None, D) is not None
