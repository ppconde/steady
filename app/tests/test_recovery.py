from datetime import date, timedelta

from steady.analysis.recovery import gauge, usual_hard_pairs, usual_week_load, week_load
from steady.models import Night
from tests.helpers import act, utc

END = date(2026, 11, 1)  # a Sunday


def nights(n=45, last=None):
    """n nights ending END: HRV 60±3, RHR 48±1, sleep 7.5 h±0.3; `last` overrides the final nights."""
    out = []
    for i in range(n):
        d = END - timedelta(days=n - 1 - i)
        sgn = 1 if i % 2 else -1
        out.append(Night(d, 60 + 3 * sgn, 48 + sgn, (7.5 + 0.3 * sgn) * 3600))
    for k, night in enumerate(last or []):
        idx = len(out) - len(last) + k
        out[idx] = Night(out[idx].day, *night)
    return out


def weeks_of_load(current_load, usual=300):
    acts = []
    for w in range(1, 9):  # 8 full weeks before END's week, on Wednesdays
        acts.append(act(utc(2026, 10, 28, 9) - timedelta(weeks=w), load=usual))
    acts.append(act(utc(2026, 10, 28, 9), load=current_load))
    return acts


OK = (60, 48, 7.5 * 3600)
BAD = (45, 54, 7.5 * 3600)


def test_load_helpers():
    acts = weeks_of_load(200)
    assert week_load(acts, END) == 200
    assert usual_week_load(acts, END) == 300


def test_fresh():
    assert gauge(nights(last=[OK, OK, OK]), weeks_of_load(200), END) == "fresh"


def test_heavy_week_recovered_is_not_strained():
    assert gauge(nights(last=[OK, OK, OK]), weeks_of_load(450), END) == "normal"


def test_strained_by_recovery():
    assert gauge(nights(last=[BAD, OK, BAD]), weeks_of_load(200), END) == "strained"


def test_strained_by_load_and_one_signal():
    assert gauge(nights(last=[OK, (45, 48, 7.5 * 3600), OK]), weeks_of_load(450), END) == "strained"


def test_gauge_missing_nights():
    assert gauge(nights(last=[(None, None, None)] * 3), weeks_of_load(200), END) != "strained"


def test_building_baseline():
    assert gauge(nights(5), weeks_of_load(200), END) == "building_baseline"


def test_usual_hard_pairs():
    acts = []
    for w in range(1, 9):
        thu = utc(2026, 10, 29, 18) - timedelta(weeks=w)
        acts += [act(thu, sport="hiit", load=150), act(thu + timedelta(days=1), sport="volleyball", load=150)]
    assert (3, 4) in usual_hard_pairs(acts, END)


def test_no_recovery_data_is_not_fresh():
    assert gauge(nights(last=[(None, None, None)] * 3), weeks_of_load(200), END) == "normal"
