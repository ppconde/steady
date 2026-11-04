from datetime import date, timedelta

import pytest

from steady.analysis.running import after_strength, effort, pace_at_hr, running_trend
from steady.models import Sample
from tests.helpers import act, utc


def test_effort_thresholds():
    assert effort(act(utc(2026, 11, 1), load=30)) == "easy"
    assert effort(act(utc(2026, 11, 1), load=80)) == "moderate"
    assert effort(act(utc(2026, 11, 1), load=150)) == "hard"


def test_effort_fallbacks():
    assert effort(act(utc(2026, 11, 1), te=3.0)) == "moderate"
    assert effort(act(utc(2026, 11, 1))) == "easy"


def test_after_strength_window():
    hiit = act(utc(2026, 10, 30, 18, 0), sport="hiit", minutes=45)
    assert after_strength(act(utc(2026, 10, 30, 18, 50)), [hiit]) is True
    assert after_strength(act(utc(2026, 10, 30, 21, 0)), [hiit]) is False
    assert after_strength(act(utc(2026, 10, 30, 17, 0)), [hiit]) is False


def test_pace_at_hr():
    assert pace_at_hr([Sample(i, 140, 3.0) for i in range(400)]) == pytest.approx(333.3, abs=0.1)
    assert pace_at_hr([Sample(i, 140, 3.0) for i in range(200)]) is None


def test_running_trend_excludes_post_hiit():
    end = date(2026, 11, 2)
    runs, paces = [], {}
    for i in range(5):  # one run a week, each 5 s/km faster
        r = act(utc(2026, 9, 28, 8) + timedelta(days=7 * i), aid=f"r{i}")
        runs.append(r)
        paces[r.id] = 360 - 5 * i
    hiit = act(utc(2026, 10, 29, 18), sport="hiit", minutes=45, aid="h")
    slow = act(utc(2026, 10, 29, 18, 50), aid="slow")
    paces["slow"] = 420

    def samples_for(aid):
        return [Sample(i, 140, 1000 / paces[aid]) for i in range(400)] if aid in paces else []

    t = running_trend(runs + [hiit, slow], samples_for, end)
    assert len(t.points) == 5
    assert 420 not in [round(p) for _, p in t.points]
    assert t.direction == "up"
    assert t.change < 0


def test_pace_at_hr_smart_recording():
    # Garmin smart recording: a sample every 5 s; 80 samples = 400 s in band
    assert pace_at_hr([Sample(5 * i, 140, 3.0) for i in range(80)]) == pytest.approx(333.3, abs=0.1)
    assert pace_at_hr([Sample(5 * i, 140, 3.0) for i in range(40)]) is None
