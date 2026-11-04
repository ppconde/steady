import dataclasses
from datetime import date, timedelta

from modform.analysis.report import build_report
from modform.analysis.running import RunningTrend
from modform.analysis.strength import StrengthProgress
from modform.demo import FakeSource
from modform.findings import findings, template_text
from tests.helpers import act, utc

END = date(2026, 11, 1)


def base(**kw):
    return dataclasses.replace(build_report(FakeSource(), END, today=END), **kw)


def test_usual_pair_not_warned():
    thu = utc(2026, 10, 29, 18)
    r = build_report(FakeSource(acts=[act(thu, sport="hiit", load=150),
                                      act(thu + timedelta(days=1), sport="volleyball", load=150)]), END, today=END)
    fs = findings(dataclasses.replace(r, usual_pairs={(3, 4)}))
    assert not any(w in f.lower() for f in fs for w in ("warning", "careful", "⚠"))
    assert any("usual" in f for f in fs)


def test_unusual_pair_mentioned():
    thu = utc(2026, 10, 29, 18)
    r = build_report(FakeSource(acts=[act(thu, sport="hiit", load=150),
                                      act(thu + timedelta(days=1), sport="volleyball", load=150)]), END, today=END)
    assert any("Thu" in f and "Fri" in f for f in findings(r))


def test_numbers_formatted():
    fs = findings(base(running=RunningTrend(322, -9, [], "up")))
    assert any("5:22/km" in f and "9 s/km faster" in f for f in fs)


def test_not_enough_data():
    fs = findings(base(strength=StrengthProgress(0, 0, 0, [], None)))
    assert any("Not enough exercise data" in f for f in fs)
    assert any("No comparable runs" in f for f in fs)


def test_template_joins():
    assert template_text(["A.", "B."]) == "A. B."


def test_strength_wording_follows_period():
    from modform.analysis.strength import ExerciseChange
    st = StrengthProgress(1, 0, 1, [ExerciseChange("PUSH_UP", "reps", 18, 22)], "up")
    week = findings(base(strength=st))
    assert any("previous 4 weeks" in f for f in week)
    custom = build_report(FakeSource(), date(2026, 10, 31), start=date(2026, 10, 1), today=END)
    fs = findings(dataclasses.replace(custom, strength=st))
    assert any("previous 31 days" in f for f in fs) and not any("4 weeks" in f for f in fs)
    custom = build_report(FakeSource(), date(2026, 10, 28), start=date(2026, 10, 1), today=END)
    assert any("previous 4 weeks" in f for f in findings(dataclasses.replace(custom, strength=st)))


def test_missing_nights_said():
    fs = findings(base(gauge="normal", missing_nights=2))
    assert any("2 of the last 3 nights" in f for f in fs)
