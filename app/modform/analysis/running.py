"""Effort per activity and the 'pace at 140 bpm' running trend."""
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Callable, Literal

from .. import config
from ..models import Activity, Sample

Effort = Literal["easy", "moderate", "hard"]


def effort(a: Activity) -> Effort:
    if a.training_load is not None:
        if a.training_load < config.EFFORT_LOAD_MODERATE:
            return "easy"
        return "moderate" if a.training_load < config.EFFORT_LOAD_HARD else "hard"
    if a.aerobic_te is not None:
        return "easy" if a.aerobic_te < 2.5 else "moderate" if a.aerobic_te < 3.5 else "hard"
    return "easy"


def is_strength(a: Activity) -> bool:
    return "strength" in a.sport or "hiit" in a.sport


def is_run(a: Activity) -> bool:
    return "running" in a.sport


def after_strength(run: Activity, others: list[Activity], window_h: float = config.AFTER_STRENGTH_H) -> bool:
    for o in others:
        if o is run or not is_strength(o):
            continue
        gap = (run.start - (o.start + timedelta(seconds=o.duration_s))).total_seconds()
        if 0 <= gap <= window_h * 3600:
            return True
    return False


def pace_at_hr(samples: list[Sample], lo: int = config.HR_LO, hi: int = config.HR_HI,
               min_s: int = config.HR_MIN_S) -> float | None:
    """Seconds per km while HR was in [lo, hi], time-weighted so 1 s and smart-recording (1-7 s) both work."""
    ss = sorted(samples, key=lambda s: s.t_s)
    secs = dist = 0.0
    for i, s in enumerate(ss):
        gap = ss[i + 1].t_s - s.t_s if i + 1 < len(ss) else (s.t_s - ss[i - 1].t_s if i else 1)
        dt = min(max(gap, 0), 10)  # pauses longer than 10 s don't count
        if s.hr is not None and lo <= s.hr <= hi and s.speed and s.speed > 0.5:
            secs += dt
            dist += s.speed * dt
    return 1000 * secs / dist if secs >= min_s else None


@dataclass(frozen=True)
class RunningTrend:
    current: float | None  # s/km
    change: float | None  # s/km, negative = faster
    points: list[tuple[date, float]]
    direction: Literal["up", "down", "flat"] | None  # "up" = improving


def running_trend(acts: list[Activity], samples_for: Callable[[str], list[Sample]], end: date,
                  weeks: int = 6) -> RunningTrend:
    first = end - timedelta(weeks=weeks)
    points = []
    for a in acts:
        day = a.start.astimezone(config.TZ).date()
        if not is_run(a) or not (first < day <= end) or after_strength(a, acts):
            continue
        p = pace_at_hr(samples_for(a.id))
        if p is None and a.avg_speed and a.avg_hr and config.HR_LO <= a.avg_hr <= config.HR_HI:
            p = 1000 / a.avg_speed
        if p is not None:
            points.append((day, p))
    points.sort()
    vals = [p for _, p in points]
    current = mean(vals[-3:]) if vals else None
    change = mean(vals[-3:]) - mean(vals[:3]) if len(vals) >= 4 else None
    direction = None if change is None else "up" if change <= -3 else "down" if change >= 3 else "flat"
    return RunningTrend(current, change, points, direction)
