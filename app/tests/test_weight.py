from datetime import date, datetime, time, timezone

from steady import config, influx
from steady.analysis.weight import weight_trend
from steady.models import WeighIn
from tests.test_influx import SINCE, UNTIL, fake

END = date(2026, 11, 4)


def w(day: int, kg: float, month: int = 11) -> WeighIn:
    return WeighIn(datetime.combine(date(2026, month, day), time(8), config.TZ).astimezone(timezone.utc), kg)


BEFORE = [w(10, 80.0, 10), w(20, 80.0, 10)]  # inside the 28 days before the last 7


def test_moved_toward_target_is_improving():
    t = weight_trend(BEFORE + [w(1, 79.7), w(3, 79.7)], 75, END)
    assert (t.status, t.direction, t.avg, t.before) == ("closer", "up", 79.7, 80.0)


def test_moved_away_is_slipping():
    t = weight_trend(BEFORE + [w(1, 80.3), w(3, 80.3)], 75, END)
    assert (t.status, t.direction) == ("further", "down")


def test_small_move_far_from_target_is_flat():
    assert weight_trend(BEFORE + [w(1, 79.8), w(3, 79.8)], 75, END).status == "steady"


def test_within_1kg_and_holding_is_on_track():
    t = weight_trend([w(10, 75.8, 10), w(20, 75.9, 10), w(1, 75.9), w(3, 75.8)], 75, END)
    assert (t.status, t.direction) == ("on_track", "up")


def test_target_above_counts_gaining_as_closer():
    assert weight_trend(BEFORE + [w(1, 80.5), w(3, 80.5)], 85, END).status == "closer"


def test_needs_two_weigh_ins_per_window():
    t = weight_trend(BEFORE + [w(3, 79.0)], 75, END)
    assert (t.status, t.direction, t.latest) == (None, None, 79.0)


def test_no_target_no_vote_but_trend_shown():
    t = weight_trend(BEFORE + [w(1, 79.7), w(3, 79.7)], None, END)
    assert (t.direction, t.avg, len(t.points)) == (None, 79.7, 4)


def test_ignores_weigh_ins_after_end():
    assert weight_trend(BEFORE + [w(5, 70.0)], 75, END).latest == 80.0


def test_influx_weigh_ins_grams_to_kg(monkeypatch):
    monkeypatch.setattr(influx, "query", fake({"BodyComposition": [{"time": 1793800000, "weight": 78400.0},
                                                                   {"time": 1793800100, "weight": None}]}))
    assert [x.kg for x in influx.weigh_ins(SINCE, UNTIL)] == [78.4]


def test_influx_weight_goal(monkeypatch):
    monkeypatch.setattr(influx, "query", fake({"WeightGoal": [{"time": 1793800000, "last": 75.0}]}))
    assert influx.weight_goal() == 75.0
    monkeypatch.setattr(influx, "query", fake({}))
    assert influx.weight_goal() is None
