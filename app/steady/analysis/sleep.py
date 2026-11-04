"""Sleep: last night's breakdown and the recent average vs the weeks before. Descriptive only."""
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean

from ..models import Night

MIN_NIGHTS = 3


@dataclass(frozen=True)
class SleepSummary:
    last: Night | None  # most recent night with a sleep time
    avg_s: float | None  # mean sleep over the recent window
    before_s: float | None  # mean sleep over the window before it
    avg_score: float | None
    recent_days: int = 7
    before_days: int = 28


def sleep_summary(ns: list[Night], end: date, recent: int = 7, before: int = 28) -> SleepSummary:
    slept = [n for n in ns if n.sleep_s and n.day <= end]
    cut, start = end - timedelta(days=recent), end - timedelta(days=recent + before)
    now = [n for n in slept if n.day > cut]
    then = [n for n in slept if start < n.day <= cut]

    def avg(xs):
        return mean(xs) if len(xs) >= MIN_NIGHTS else None

    scores = [n.score for n in now if n.score is not None]
    return SleepSummary(slept[-1] if slept else None, avg([n.sleep_s for n in now]), avg([n.sleep_s for n in then]),
                        avg(scores), recent, before)
