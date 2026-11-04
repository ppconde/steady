"""Per-exercise progress: best set this period vs the same-length period before."""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from .. import config
from ..models import ExerciseSet

Unit = Literal["kg", "reps", "s"]


@dataclass(frozen=True)
class ExerciseChange:
    exercise: str
    unit: Unit
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass(frozen=True)
class StrengthProgress:
    up: int
    down: int
    total: int
    changes: list[ExerciseChange]  # biggest relative changes first, max 4
    direction: Literal["up", "down", "flat"] | None


def _best(sets: list[ExerciseSet]) -> dict[str, tuple[Unit, float]]:
    by_ex: dict[str, list[ExerciseSet]] = {}
    for x in sets:
        by_ex.setdefault(x.exercise, []).append(x)
    out = {}
    for ex, xs in by_ex.items():
        if any(x.weight_kg > 0 for x in xs):
            out[ex] = ("kg", max(x.weight_kg for x in xs))
        elif any(x.reps > 0 for x in xs):
            out[ex] = ("reps", max(x.reps for x in xs))
        else:
            out[ex] = ("s", max(x.duration_s for x in xs))
    return out


def strength_progress(sets: list[ExerciseSet], end: date, days: int = 28) -> StrengthProgress:
    def period(lo: date, hi: date):
        return [x for x in sets if lo < x.time.astimezone(config.TZ).date() <= hi]

    now = _best(period(end - timedelta(days=days), end))
    before = _best(period(end - timedelta(days=2 * days), end - timedelta(days=days)))
    changes = [ExerciseChange(ex, u, before[ex][1], v) for ex, (u, v) in now.items()
               if ex in before and before[ex][0] == u]
    up = sum(c.delta > 0 for c in changes)
    down = sum(c.delta < 0 for c in changes)
    changes.sort(key=lambda c: abs(c.delta) / max(c.before, 1), reverse=True)
    direction = None if not changes else "up" if up > down else "down" if down > up else "flat"
    return StrengthProgress(up, down, len(changes), changes[:4], direction)
