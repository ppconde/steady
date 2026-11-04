"""Data shared by every module. All times tz-aware UTC unless named `day`."""
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Activity:
    id: str
    start: datetime
    duration_s: float
    sport: str  # Garmin typeKey, e.g. "running", "hiit", "volleyball"
    distance_m: float | None
    avg_hr: float | None
    avg_speed: float | None  # m/s
    training_load: float | None
    aerobic_te: float | None


@dataclass(frozen=True)
class Sample:
    t_s: float
    hr: float | None
    speed: float | None  # m/s


@dataclass(frozen=True)
class ExerciseSet:
    activity_id: str
    time: datetime
    exercise: str
    reps: int
    duration_s: float
    weight_kg: float


@dataclass(frozen=True)
class Night:
    day: date  # local date the sleep ended
    hrv: float | None
    rhr: float | None
    sleep_s: float | None
