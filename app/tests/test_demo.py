from datetime import date

from steady.analysis.report import build_report
from steady.demo import demo_source


def test_demo_fills_every_tile():
    today = date(2026, 11, 4)
    r = build_report(demo_source(today), today, today=today)
    assert r.verdict == "yes" and r.gauge in ("fresh", "normal")
    assert r.running.current and len(r.running.points) >= 4
    assert r.strength.total >= 4
    assert any(c.sessions for c in r.week)
