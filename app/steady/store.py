"""SQLite: saved reviews and the one-at-a-time review job."""
import sqlite3
from datetime import date, datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, created_at TEXT, start TEXT, end TEXT,
  kind TEXT CHECK(kind IN ('week','custom')), text TEXT, source TEXT, fingerprint TEXT);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, created_at TEXT, start TEXT, end TEXT,
  status TEXT CHECK(status IN ('running','done')), review_id INTEGER);
"""
STALE = timedelta(minutes=10)


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(config.DB_PATH, isolation_level=None)  # autocommit; BEGIN IMMEDIATE where needed
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def save_review(start: date | None, end: date, kind: str, text: str, source: str, fingerprint: str,
                now: datetime | None = None) -> int:
    created = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    with _db() as c:
        return c.execute("INSERT INTO reviews(created_at,start,end,kind,text,source,fingerprint) VALUES(?,?,?,?,?,?,?)",
                         (created, _iso(start), end.isoformat(), kind, text, source, fingerprint)).lastrowid


def review_for_week(week_start: date) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM reviews WHERE kind='week' AND start=? ORDER BY created_at DESC, id DESC LIMIT 1",
                      (week_start.isoformat(),)).fetchone()
    return dict(r) if r else None


def custom_reviews() -> list[dict]:
    with _db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM reviews WHERE kind='custom' ORDER BY created_at DESC, id DESC")]


def get_review(review_id: int) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    return dict(r) if r else None


def start_job(start: date | None, end: date) -> int | None:
    c = _db()
    try:
        c.execute("BEGIN IMMEDIATE")
        stale = (datetime.now(timezone.utc) - STALE).isoformat()
        c.execute("UPDATE jobs SET status='done' WHERE status='running' AND created_at < ?", (stale,))
        if c.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
            c.execute("ROLLBACK")
            return None
        jid = c.execute("INSERT INTO jobs(created_at,start,end,status) VALUES(?,?,?,'running')",
                        (_now(), _iso(start), end.isoformat())).lastrowid
        c.execute("COMMIT")
        return jid
    finally:
        c.close()


def finish_job(job_id: int, review_id: int | None) -> None:
    with _db() as c:
        c.execute("UPDATE jobs SET status='done', review_id=? WHERE id=?", (review_id, job_id))


def get_job(job_id: int) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not r:
        return None
    job = dict(r)
    if job["status"] == "running" and job["created_at"] < (datetime.now(timezone.utc) - STALE).isoformat():
        job["status"] = "done"  # its worker died (restart); start_job sweeps the row itself
    return job


def clear_running() -> None:
    """At startup no review thread can be alive, so every 'running' job is an orphan."""
    with _db() as c:
        c.execute("UPDATE jobs SET status='done' WHERE status='running'")
