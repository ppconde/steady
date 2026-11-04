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
