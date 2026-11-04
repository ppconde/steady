from datetime import datetime, timedelta, timezone

from modform.models import Activity


def act(start, sport="running", minutes=30, load=None, te=None, hr=None, speed=None, dist=None, aid=None):
    if isinstance(start, str):
        start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    return Activity(id=aid or f"{sport}-{start.isoformat()}", start=start, duration_s=minutes * 60, sport=sport,
                    distance_m=dist, avg_hr=hr, avg_speed=speed, training_load=load, aerobic_te=te)


def utc(y, m, d, h=12, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


DAY = timedelta(days=1)
