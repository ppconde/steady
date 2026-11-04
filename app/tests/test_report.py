from datetime import date, timedelta

from steady.analysis.report import build_report, verdict, week_row
from steady.analysis.running import RunningTrend
from steady.analysis.strength import StrengthProgress
from steady.demo import FakeSource
from tests.helpers import act, utc


def rt(d):
    return RunningTrend(None, None, [], d)


def sp(d):
    return StrengthProgress(0, 0, 0, [], d)


def test_verdict_rule():
    assert verdict(rt("up"), sp("up")) == "yes"
    assert verdict(rt("down"), sp("down")) == "no"
    assert verdict(rt("up"), sp("down")) == "mixed"
    assert verdict(rt("up"), sp(None)) == "yes"
    assert verdict(rt(None), sp(None)) == "not_enough_data"
    assert verdict(rt("flat"), sp("flat")) == "mixed"


MON = date(2026, 10, 26)


def test_week_row_double_day_and_rest():
    thu = utc(2026, 10, 29, 18)
    acts = [act(thu, sport="hiit", minutes=45, load=150), act(thu + timedelta(minutes=50), dist=5000, load=40)]
    row = week_row(acts, MON, today=date(2026, 11, 1))
    assert len(row[3].sessions) == 2 and row[3].effort == "hard"
    assert row[2].effort == "rest" and row[2].sessions == []


def test_week_row_future_days_empty():
    row = week_row([act(utc(2026, 10, 31, 9))], MON, today=date(2026, 10, 28))
    assert all(c.future and c.sessions == [] and c.effort is None for c in row[3:])
    assert not row[2].future


def test_week_uses_local_timezone():
    # 23:30 UTC on Sunday 5 Jul is 00:30 Monday in Lisbon (UTC+1 in summer)
    a = act(utc(2026, 7, 5, 23, 30))
    assert week_row([a], date(2026, 7, 6), today=date(2026, 7, 12))[0].sessions
    assert not week_row([a], date(2026, 6, 29), today=date(2026, 7, 12))[6].sessions


def test_other_sport_label():
    row = week_row([act(utc(2026, 10, 27, 9), sport="hiking", minutes=120)], MON, today=date(2026, 11, 1))
    assert row[1].sessions[0].label.startswith("Hiking")


def test_past_week_ignores_later_data():
    end = date(2026, 11, 1)
    base = [act(utc(2026, 10, 27, 9), load=50)]
    a = build_report(FakeSource(acts=base), end, today=date(2026, 11, 20))
    b = build_report(FakeSource(acts=base + [act(utc(2026, 11, 3, 9), load=200)]), end, today=date(2026, 11, 20))
    assert a == b
