from datetime import date, datetime, timedelta, timezone

from steady.analysis.strength import strength_progress
from steady.models import ExerciseSet

END = date(2026, 11, 2)


def s(days_before, exercise, reps=0, dur=0, kg=0):
    t = datetime(END.year, END.month, END.day, 18, tzinfo=timezone.utc) - timedelta(days=days_before)
    return ExerciseSet("a", t, exercise, reps, dur, kg)


def test_compares_exercise_with_itself():
    sets = [s(35, "PUSH_UP", reps=18), s(5, "PUSH_UP", reps=22),
            s(35, "PLANK", dur=45), s(5, "PLANK", dur=60),
            s(35, "LUNGE", reps=20), s(5, "LUNGE", reps=18),
            s(5, "BURPEE", reps=15)]
    p = strength_progress(sets, END)
    assert (p.up, p.down, p.total) == (2, 1, 3)
    assert "BURPEE" not in [c.exercise for c in p.changes]
    assert p.direction == "up"


def test_weight_beats_reps():
    p = strength_progress([s(35, "KB_SWING", reps=20, kg=16), s(5, "KB_SWING", reps=15, kg=20)], END)
    (c,) = p.changes
    assert c.unit == "kg" and c.delta == 4


def test_no_sets():
    p = strength_progress([], END)
    assert p.total == 0 and p.direction is None
