"""Read garmin-grafana's InfluxDB 1.x over its HTTP API."""
import base64
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import config
from .models import Activity, ExerciseSet, Night, Sample, WeighIn


def query(q: str) -> list[dict]:
    url = f"{config.INFLUX_URL}/query?" + urllib.parse.urlencode({"db": config.INFLUX_DB, "q": q, "epoch": "s"})
    req = urllib.request.Request(url)
    auth = base64.b64encode(f"{config.INFLUX_USER}:{config.INFLUX_PASSWORD}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    rows = []
    for result in body.get("results", []):
        if "error" in result:
            raise RuntimeError(result["error"])
        for s in result.get("series", []):
            rows += [dict(zip(s["columns"], v)) for v in s["values"]]
    return rows


def _t(ts) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


def _range(since: datetime, until: datetime) -> str:
    f = "%Y-%m-%dT%H:%M:%SZ"
    return f"time >= '{since.astimezone(timezone.utc):{f}}' AND time < '{until.astimezone(timezone.utc):{f}}'"


def activities(since: datetime, until: datetime) -> list[Activity]:
    out = {}
    for r in query(f'SELECT * FROM "ActivitySummary" WHERE {_range(since, until)}'):
        if r.get("activityName") == "END" or r.get("Activity_ID") is None:
            continue
        aid = str(r["Activity_ID"])
        out[aid] = Activity(id=aid, start=_t(r["time"]), duration_s=r.get("elapsedDuration") or 0,
                            sport=r.get("activityType") or "other", distance_m=r.get("distance"),
                            avg_hr=r.get("averageHR"), avg_speed=r.get("averageSpeed"),
                            training_load=r.get("activityTrainingLoad"), aerobic_te=r.get("aerobicTrainingEffect"))
    return sorted(out.values(), key=lambda a: a.start)


def samples(activity_id: str) -> list[Sample]:
    aid = str(int(activity_id))  # ids are numeric; keeps the query injection-free
    rows = query(f'SELECT "DurationSeconds","HeartRate","Speed" FROM "ActivityGPS" WHERE "ActivityID" = \'{aid}\'')
    return [Sample(r["DurationSeconds"] or 0, r.get("HeartRate"), r.get("Speed")) for r in rows]


def exercise_sets(since: datetime, until: datetime) -> list[ExerciseSet]:
    rows = query(f'SELECT * FROM "StrengthExerciseSet" WHERE {_range(since, until)}')
    return [ExerciseSet(activity_id=str(r.get("ActivityID") or r.get("Activity_ID")), time=_t(r["time"]),
                        exercise=r.get("ExerciseLabel") or "UNKNOWN", reps=int(r.get("Reps") or 0),
                        duration_s=float(r.get("Duration_s") or 0), weight_kg=float(r.get("Weight_kg") or 0))
            for r in rows]


def nights(since: datetime, until: datetime) -> list[Night]:
    out = {}
    q = f'SELECT "avgOvernightHrv","restingHeartRate","sleepTimeSeconds" FROM "SleepSummary" WHERE {_range(since, until)}'
    for r in query(q):
        day = _t(r["time"]).astimezone(config.TZ).date()
        out[day] = Night(day, r.get("avgOvernightHrv"), r.get("restingHeartRate"), r.get("sleepTimeSeconds"))
    return sorted(out.values(), key=lambda n: n.day)


def weigh_ins(since: datetime, until: datetime) -> list[WeighIn]:
    rows = query(f'SELECT "weight" FROM "BodyComposition" WHERE {_range(since, until)}')
    return [WeighIn(_t(r["time"]), r["weight"] / 1000) for r in rows if r.get("weight")]  # Garmin stores grams


def weight_goal() -> float | None:
    if config.TARGET_WEIGHT_KG:
        return config.TARGET_WEIGHT_KG
    rows = query('SELECT last("goal_kg") FROM "WeightGoal"')  # written by the patched sync, see sync/Dockerfile
    return rows[0]["last"] if rows else None


def _last(measurement: str, field: str) -> int | None:
    rows = query(f'SELECT last("{field}") FROM "{measurement}"')
    return rows[0]["time"] if rows else None


def fingerprint() -> str:
    return f'{_last("ActivitySummary", "activityType")}|{_last("SleepSummary", "sleepTimeSeconds")}'


def last_sync() -> datetime | None:
    ts = [t for t in (_last("ActivitySummary", "activityType"), _last("SleepSummary", "sleepTimeSeconds")) if t]
    return _t(max(ts)) if ts else None
