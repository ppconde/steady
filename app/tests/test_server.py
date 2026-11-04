import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from steady import scheduler, server
from steady.demo import FakeSource


@pytest.fixture
def base():
    srv = server.make_server(FakeSource(), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def test_week_endpoint_shape(base):
    status, body = call(f"{base}/api/week?end=2026-11-02")
    assert status == 200 and set(body) == {"report", "review", "last_sync"}
    assert len(body["report"]["week"]) == 7


def test_review_busy(base, monkeypatch):
    real = scheduler.write_review
    monkeypatch.setattr(scheduler, "write_review", lambda *a: (time.sleep(1), real(*a))[1])
    r = {"start": "2026-10-01", "end": "2026-10-31"}
    s1, b1 = call(f"{base}/api/review", r)
    s2, _ = call(f"{base}/api/review", r)
    assert (s1, s2) == (202, 409)
    for _ in range(40):
        s, job = call(f"{base}/api/review/{b1['job_id']}")
        if job["status"] == "done":
            break
        time.sleep(0.1)
    assert job["review"]["source"] == "template"
    assert call(f"{base}/api/reviews")[1][0]["id"] == job["review"]["id"]


@pytest.mark.parametrize("body", [{"start": "2026-11-02", "end": "2026-11-01"},
                                  {"start": "2024-01-01", "end": "2026-11-01"},
                                  {"start": "nope", "end": "2026-11-01"}, {}])
def test_review_bad_range(base, body):
    assert call(f"{base}/api/review", body)[0] == 400


def test_static_traversal_blocked(base):
    assert call(f"{base}/static/../server.py")[0] == 404
    assert call(f"{base}/static/%2e%2e/server.py")[0] == 404
