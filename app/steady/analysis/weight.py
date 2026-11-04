"""Weight: recent average vs the weeks before, judged against the target."""
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Literal

from .. import config
from ..models import WeighIn

Status = Literal["closer", "further", "on_track", "steady"]
_DIRECTION = {"closer": "up", "on_track": "up", "further": "down", "steady": "flat"}


@dataclass(frozen=True)
class WeightTrend:
    latest: float | None
    avg: float | None  # average of the recent window
    before: float | None  # average of the window before it
    target: float | None
    status: Status | None
    direction: Literal["up", "down", "flat"] | None  # "up" = improving
    points: list  # (day, kg) for the last 6 weeks
    recent_days: int = 7
    before_days: int = 28


def weight_trend(ws: list[WeighIn], target: float | None, end: date, recent: int = 7,
                 before: int = 28) -> WeightTrend:
    def day(x: WeighIn) -> date:
        return x.time.astimezone(config.TZ).date()

    ws = sorted((x for x in ws if day(x) <= end), key=lambda x: x.time)

    def window(lo: date, hi: date) -> list[float]:
        return [x.kg for x in ws if lo < day(x) <= hi]

    cut = end - timedelta(days=recent)
    now, prev = window(cut, end), window(cut - timedelta(days=before), cut)
    avg, bef = (round(mean(v), 1) if v else None for v in (now, prev))
    status = None
    if target is not None and len(now) >= 2 and len(prev) >= 2:
        closer = round(abs(bef - target) - abs(avg - target), 2)
        status = ("closer" if closer >= config.WEIGHT_MOVE_KG else "further" if closer <= -config.WEIGHT_MOVE_KG
                  else "on_track" if abs(avg - target) <= config.WEIGHT_NEAR_KG else "steady")
    pts = [(day(x), x.kg) for x in ws if day(x) > end - timedelta(days=42)]
    return WeightTrend(ws[-1].kg if ws else None, avg, bef, target, status, _DIRECTION.get(status), pts, recent, before)
