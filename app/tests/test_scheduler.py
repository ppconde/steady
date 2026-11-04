from datetime import datetime

from modform import config, scheduler, store
from modform.demo import FakeSource


def at(h, m):
    return datetime(2026, 11, 4, h, m, 10, tzinfo=config.TZ)


def test_skip_when_nothing_new():
    store.save_review(None, at(7, 0).date(), "scheduled", "x", "template", "1|1")
    assert scheduler.scheduled_tick(at(7, 30), FakeSource(fp="1|1")) is False
    assert len(store.custom_reviews()) == 0 and store.review_for_week(at(7, 0).date()).get("text") == "x"


def test_runs_at_review_time():
    src = FakeSource(fp="2|2")
    assert scheduler.scheduled_tick(at(10, 0), src) is False
    assert scheduler.scheduled_tick(at(7, 30), src) is True
    assert store.last_fingerprint() == "2|2"
    assert scheduler.scheduled_tick(at(7, 30), src) is False  # same data, no second review
