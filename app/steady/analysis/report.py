"""Everything the dashboard shows for one period, computed as of its end date."""
import dataclasses
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from typing import Literal, Protocol

from .. import config
from ..models import Activity, ExerciseSet, Night, Sample, WeighIn
from .recovery import Gauge, baseline, gauge, off_names, usual_hard_pairs, usual_week_load, week_load
from .running import RunningTrend, effort, is_run, is_strength, running_trend
from .strength import StrengthProgress, strength_progress
from .weight import WeightTrend, weight_trend

Verdict = Literal["yes", "no", "mixed", "not_enough_data"]
_RANK = {"easy": 1, "moderate": 2, "hard": 3}


class DataSource(Protocol):
    def activities(self, since: datetime, until: datetime) -> list[Activity]: ...
    def samples(self, activity_id: str) -> list[Sample]: ...
    def exercise_sets(self, since: datetime, until: datetime) -> list[ExerciseSet]: ...
    def nights(self, since: datetime, until: datetime) -> list[Night]: ...
    def weigh_ins(self, since: datetime, until: datetime) -> list[WeighIn]: ...
    def weight_goal(self) -> float | None: ...
    def fingerprint(self) -> str: ...
    def last_sync(self) -> datetime | None: ...


def verdict(*trends) -> Verdict:
    """Yes when most of the signals with data point up, no when most point down."""
    ds = [t.direction for t in trends if t.direction is not None]
    if not ds:
        return "not_enough_data"
    if 2 * ds.count("up") > len(ds):
        return "yes"
    if 2 * ds.count("down") > len(ds):
        return "no"
    return "mixed"


@dataclass(frozen=True)
class Session:
    sport: str
    label: str
    effort: str


@dataclass(frozen=True)
class DayCell:
    day: date
    sessions: list[Session]
    effort: str | None  # hardest session, "rest", or None for days still to come
    future: bool


def _label(a: Activity) -> str:
    if is_run(a):
        name = "Run"
        if a.distance_m:
            return f"Run · {a.distance_m / 1000:.1f}".removesuffix(".0") + " km"
    elif "hiit" in a.sport:
        name = "HIIT"
    elif is_strength(a):
        name = "Strength"
    else:
        name = a.sport.replace("_", " ").title()
    return f"{name} · {round(a.duration_s / 60)} min"


def _local_day(a: Activity) -> date:
    return a.start.astimezone(config.TZ).date()


def week_row(acts: list[Activity], week_start: date, today: date) -> list[DayCell]:
    cells = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        future = day > today
        todays = [] if future else sorted((a for a in acts if _local_day(a) == day), key=lambda a: a.start)
        sessions = [Session(a.sport, _label(a), effort(a)) for a in todays]
        hardest = max((s.effort for s in sessions), key=_RANK.get, default="rest")
        cells.append(DayCell(day, sessions, None if future else hardest, future))
    return cells


@dataclass(frozen=True)
class Report:
    start: date
    end: date
    verdict: Verdict
    gauge: Gauge
    running: RunningTrend
    strength: StrengthProgress
    weight: WeightTrend
    week: list[DayCell]
    usual_pairs: set
    week_load: float
    usual_load: float | None
    latest: Night | None
    missing_nights: int  # of the 3 judged nights, how many had no recovery data
    off_signals: list[str]  # signals outside the usual band on any judged night
    compare_days: int  # strength compares this many days with the same length before


def _utc(d: date) -> datetime:
    return datetime.combine(d, time(), config.TZ).astimezone(timezone.utc)


def build_report(src: DataSource, end: date, start: date | None = None, today: date | None = None) -> Report:
    today = today or datetime.now(config.TZ).date()
    if start is None:  # week view / week review
        start, days, weeks = end - timedelta(days=end.weekday()), 28, 6
        recent = 7
    else:  # custom range: compare with the same-length period before
        days = (end - start).days + 1
        weeks = max(6, ceil(days / 7))
        recent = days
    lookback = max(2 * days, 7 * weeks, 7 * 9, config.BASELINE_DAYS + 4)
    since, until = _utc(end - timedelta(days=lookback)), _utc(end + timedelta(days=1))

    acts = [a for a in src.activities(since, until) if _local_day(a) <= end]
    sets = src.exercise_sets(since, until)
    nights = [n for n in src.nights(since, until) if n.day <= end]
    running = running_trend(acts, src.samples, end, weeks)
    strength = strength_progress(sets, end, days)
    weight = weight_trend(src.weigh_ins(since, until), src.weight_goal(), end, recent, max(days, recent))
    judged = [n for n in nights if end - timedelta(days=3) < n.day <= end
              and (n.hrv, n.rhr, n.sleep_s) != (None, None, None)]
    return Report(start=start, end=end, verdict=verdict(running, strength, weight), gauge=gauge(nights, acts, end),
                  running=running, strength=strength, weight=weight,
                  week=week_row(acts, end - timedelta(days=end.weekday()), today),
                  usual_pairs=usual_hard_pairs(acts, end), week_load=week_load(acts, end),
                  usual_load=usual_week_load(acts, end), latest=nights[-1] if nights else None,
                  missing_nights=3 - len(judged),
                  compare_days=days,
                  off_signals=sorted({x for n in judged for x in off_names(n, baseline(nights, end))}))


def _plain(o):
    if isinstance(o, (set, frozenset)):
        return sorted(_plain(x) for x in o)
    if isinstance(o, (list, tuple)):
        return [_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, float):
        return round(o, 1)
    return o


def report_json(r: Report) -> dict:
    """JSON-safe dict: sets → sorted lists, dates → ISO strings, floats to 1 decimal."""
    return _plain(dataclasses.asdict(r))
