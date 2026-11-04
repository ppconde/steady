import dataclasses
from datetime import date, timedelta

from steady.analysis.report import build_report, week_row
from steady.analysis.sleep import sleep_summary
from steady.demo import FakeSource
from steady.findings import findings
from steady.models import Night

END = date(2026, 11, 1)


def ns(recent_h=7.5, before_h=7.0, score=80):
    return [Night(END - timedelta(days=i), 60, 48, (recent_h if i < 7 else before_h) * 3600,
                  deep_s=5400, light_s=14400, rem_s=6000, awake_s=1200, score=score) for i in range(35)][::-1]


def test_compares_recent_week_with_four_weeks_before():
    s = sleep_summary(ns(), END)
    assert s.avg_s == 7.5 * 3600 and s.before_s == 7.0 * 3600
    assert s.avg_score == 80 and s.last.day == END and s.last.deep_s == 5400


def test_needs_three_nights_per_window():
    s = sleep_summary(ns()[-2:], END)
    assert s.avg_s is None and s.before_s is None and s.last.day == END


def test_last_skips_nights_without_sleep():
    n = ns()
    n[-1] = Night(END, 61, 47, None)
    assert sleep_summary(n, END).last.day == END - timedelta(days=1)


def test_week_row_carries_sleep_per_day():
    row = week_row([], END - timedelta(days=6), today=END, nights=ns())
    assert row[0].sleep_s == 7.5 * 3600 and row[6].sleep_s == 7.5 * 3600


def test_report_has_sleep():
    r = build_report(FakeSource(night_list=ns()), END, today=END)
    assert r.sleep.avg_s == 7.5 * 3600 and r.week[6].sleep_s == 7.5 * 3600


def test_finding_says_average_and_change():
    r = build_report(FakeSource(night_list=ns()), END, today=END)
    assert "Sleep averaged 7h 30m over the last 7 nights, 30 min more than the 4 weeks before; sleep score 80." in findings(r)


def test_no_sleep_finding_without_data():
    r = build_report(FakeSource(), END, today=END)
    assert not any(f.startswith("Sleep averaged") for f in findings(r))
