from datetime import date, datetime, timezone

from modform import influx
from modform.models import Activity


def fake(rows_by_measurement):
    def query(q):
        for m, rows in rows_by_measurement.items():
            if f'"{m}"' in q:
                return rows
        return []
    return query


RUN = {"time": 1730700000, "Activity_ID": 1, "activityName": "Run", "activityType": "running",
       "elapsedDuration": 1800, "distance": 5000, "averageHR": 140, "averageSpeed": 2.78,
       "activityTrainingLoad": 60, "aerobicTrainingEffect": 2.8}
END = {"time": 1730701800, "Activity_ID": 1, "activityName": "END", "activityType": "No Activity"}

SINCE = datetime(2024, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_end_markers_ignored(monkeypatch):
    monkeypatch.setattr(influx, "query", fake({"ActivitySummary": [RUN, END]}))
    assert len(influx.activities(SINCE, UNTIL)) == 1


def test_activity_parsing(monkeypatch):
    monkeypatch.setattr(influx, "query", fake({"ActivitySummary": [RUN]}))
    (a,) = influx.activities(SINCE, UNTIL)
    assert a == Activity(id="1", start=datetime.fromtimestamp(1730700000, timezone.utc), duration_s=1800,
                         sport="running", distance_m=5000, avg_hr=140, avg_speed=2.78,
                         training_load=60, aerobic_te=2.8)
    assert a.start.tzinfo == timezone.utc


def test_nights_local_date(monkeypatch):
    t = int(datetime(2026, 11, 2, 7, 10, tzinfo=timezone.utc).timestamp())
    monkeypatch.setattr(influx, "query", fake({"SleepSummary": [
        {"time": t, "avgOvernightHrv": 61, "restingHeartRate": None, "sleepTimeSeconds": 27000}]}))
    (n,) = influx.nights(SINCE, UNTIL)
    assert n.day == date(2026, 11, 2)
    assert n.hrv == 61 and n.rhr is None and n.sleep_s == 27000
