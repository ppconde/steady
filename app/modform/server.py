"""Stdlib HTTP server: the dashboard's static files and its small JSON API."""
import json
import logging
import mimetypes
import re
import threading
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import config, scheduler, store
from .analysis.report import build_report, report_json

log = logging.getLogger(__name__)
STATIC = (Path(__file__).parent / "static").resolve()
MAX_RANGE_DAYS = 366


def _today() -> date:
    return datetime.now(config.TZ).date()


def _date(s) -> date | None:
    try:
        return date.fromisoformat(s) if isinstance(s, str) and len(s) == 10 else None
    except ValueError:
        return None


def _run_job(src, job: int, start: date, end: date) -> None:
    review = None
    try:
        review = scheduler.run_review(src, start, end, "custom")
    except Exception:
        log.exception("custom review failed")
    finally:
        store.finish_job(job, review)


def make_server(src, host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            log.debug(fmt, *args)

        def _json(self, status: int, body) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _file(self, rel: str) -> None:
            p = (STATIC / unquote(rel)).resolve()
            if not p.is_relative_to(STATIC) or not p.is_file():
                return self._json(404, {"error": "not found"})
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlsplit(self.path)
            path = url.path
            if path == "/":
                return self._file("index.html")
            if path.startswith("/static/"):
                return self._file(path.removeprefix("/static/"))
            if path == "/api/week":
                today = _today()
                end = _date(parse_qs(url.query).get("end", [""])[0]) or today + timedelta(days=6 - today.weekday())
                report = build_report(src, min(end, today), today=today)
                synced = src.last_sync()
                return self._json(200, {"report": report_json(report),
                                        "review": store.review_for_week(end - timedelta(days=end.weekday())),
                                        "last_sync": synced.isoformat() if synced else None})
            if path == "/api/reviews":
                return self._json(200, store.custom_reviews())
            if m := re.fullmatch(r"/api/review/(\d+)", path):
                job = store.get_job(int(m[1]))
                if not job:
                    return self._json(404, {"error": "not found"})
                review = store.get_review(job["review_id"]) if job["review_id"] else None
                return self._json(200, {"status": job["status"], "review": review})
            self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/review":
                return self._json(404, {"error": "not found"})
            try:
                n = min(int(self.headers.get("Content-Length") or 0), 4096)
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"error": "bad json"})
            start, end = _date(body.get("start")) if isinstance(body, dict) else None, \
                _date(body.get("end")) if isinstance(body, dict) else None
            if not start or not end or start > end or (end - start).days + 1 > MAX_RANGE_DAYS:
                return self._json(400, {"error": "start and end must be dates, start ≤ end, at most 366 days"})
            job = store.start_job(start, end)
            if job is None:
                return self._json(409, {"error": "busy"})
            threading.Thread(target=_run_job, args=(src, job, start, end), daemon=True).start()
            self._json(202, {"job_id": job})

    return ThreadingHTTPServer((host, port), Handler)
