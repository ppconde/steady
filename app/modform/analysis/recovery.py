"""Recovery baselines, the owner's usual week, and the overtraining gauge."""
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median, stdev
from typing import Literal

from .. import config
from ..models import Activity, Night
from .running import effort

Gauge = Literal["fresh", "normal", "strained", "building_baseline"]


@dataclass(frozen=True)
class Baseline:
    hrv: tuple[float, float] | None  # (mean, sd)
    rhr: tuple[float, float] | None
    sleep: tuple[float, float] | None


def _band(vals: list[float]) -> tuple[float, float] | None:
    return (mean(vals), stdev(vals)) if len(vals) >= config.BASELINE_MIN_NIGHTS else None


def baseline(nights: list[Night], end: date, days: int = config.BASELINE_DAYS) -> Baseline:
    hi = end - timedelta(days=3)
    ns = [n for n in nights if hi - timedelta(days=days) < n.day <= hi]
    return Baseline(_band([n.hrv for n in ns if n.hrv is not None]),
                    _band([n.rhr for n in ns if n.rhr is not None]),
                    _band([n.sleep_s for n in ns if n.sleep_s is not None]))


def off_names(n: Night, b: Baseline) -> list[str]:
    off = []
    if n.hrv is not None and b.hrv and n.hrv < b.hrv[0] - b.hrv[1]:
        off.append("HRV")
    if n.rhr is not None and b.rhr and n.rhr > b.rhr[0] + b.rhr[1]:
        off.append("resting HR")
    if n.sleep_s is not None and b.sleep and n.sleep_s < b.sleep[0] - b.sleep[1]:
        off.append("sleep")
    return off


def signals_off(n: Night, b: Baseline) -> int:
    return len(off_names(n, b))


def _day(a: Activity) -> date:
    return a.start.astimezone(config.TZ).date()


def week_load(acts: list[Activity], end: date, days: int = 7) -> float:
    return sum(a.training_load or 0 for a in acts if end - timedelta(days=days) < _day(a) <= end)


def _prior_weeks(end: date, weeks: int) -> list[date]:
    monday = end - timedelta(days=end.weekday())
    return [monday - timedelta(weeks=w) for w in range(1, weeks + 1)]


def usual_week_load(acts: list[Activity], end: date, weeks: int = 8) -> float | None:
    loads, active = [], 0
    for mon in _prior_weeks(end, weeks):
        inside = [a for a in acts if mon <= _day(a) < mon + timedelta(days=7)]
        active += bool(inside)
        loads.append(sum(a.training_load or 0 for a in inside))
    return median(loads) if active >= 4 else None


def usual_hard_pairs(acts: list[Activity], end: date, weeks: int = 8) -> set[tuple[int, int]]:
    counts: dict[tuple[int, int], int] = {}
    for mon in _prior_weeks(end, weeks):
        hard = {_day(a).weekday() for a in acts
                if mon <= _day(a) < mon + timedelta(days=7) and effort(a) == "hard"}
        for d in range(6):
            if d in hard and d + 1 in hard:
                counts[(d, d + 1)] = counts.get((d, d + 1), 0) + 1
    return {p for p, c in counts.items() if c >= weeks / 2}


def gauge(nights: list[Night], acts: list[Activity], end: date) -> Gauge:
    b = baseline(nights, end)
    if b.hrv is None and b.rhr is None and b.sleep is None:
        return "building_baseline"
    judged = [signals_off(n, b) for n in nights if end - timedelta(days=3) < n.day <= end]
    load, usual = week_load(acts, end), usual_week_load(acts, end)
    heavy = usual is not None and load > config.LOAD_HIGH_FACTOR * usual
    if sum(o >= 2 for o in judged) >= 2 or (heavy and any(o >= 1 for o in judged)):
        return "strained"
    if not any(judged) and (usual is None or load <= usual):
        return "fresh"
    return "normal"
