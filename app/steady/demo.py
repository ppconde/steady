"""In-memory DataSource: used by tests and by `python -m steady --demo`."""
from dataclasses import dataclass, field
from datetime import datetime

from .models import Activity, ExerciseSet, Night, Sample, WeighIn


@dataclass
class FakeSource:
    acts: list[Activity] = field(default_factory=list)
    sets: list[ExerciseSet] = field(default_factory=list)
    night_list: list[Night] = field(default_factory=list)
    sample_map: dict[str, list[Sample]] = field(default_factory=dict)
    weights: list[WeighIn] = field(default_factory=list)
    goal: float | None = None
    fp: str = "1|1"
    synced: datetime | None = None

    def activities(self, since, until):
        return [a for a in self.acts if since <= a.start < until]

    def samples(self, activity_id):
        return self.sample_map.get(activity_id, [])

    def exercise_sets(self, since, until):
        return [s for s in self.sets if since <= s.time < until]

    def nights(self, since, until):
        return [n for n in self.night_list if since.date() <= n.day < until.date()]

    def weigh_ins(self, since, until):
        return [w for w in self.weights if since <= w.time < until]

    def weight_goal(self):
        return self.goal

    def fingerprint(self):
        return self.fp

    def last_sync(self):
        return self.synced


def demo_source(today=None) -> FakeSource:
    """Ten weeks of a plausible routine: run Mon, HIIT Tue, HIIT + run Thu, volleyball Fri and Sun."""
    from datetime import date, time, timedelta, timezone

    from . import config
    from .models import Activity, ExerciseSet, Night, Sample

    today = today or datetime.now(config.TZ).date()
    src = FakeSource(fp="demo", synced=datetime.now(timezone.utc) - timedelta(hours=3), goal=77.0)
    first = today - timedelta(days=70)

    def at(d, h, m=0):
        return datetime.combine(d, time(h, m), config.TZ).astimezone(timezone.utc)

    for i in range(71):
        d = first + timedelta(days=i)
        wk, dow, k = i // 7, d.weekday(), f"{d.isoformat()}"
        slept = 26400 + 600 * (i % 4 - 2) + 15 * i  # creeping up a little
        src.night_list.append(Night(d, 60 + (3 if i % 2 else -3), 48 + (i % 3 == 0), slept,
                                    0.19 * slept, 0.55 * slept, 0.22 * slept, 1200 + 300 * (i % 3), 72 + i % 9 + i // 10))
        if i % 3 == 0:  # a weigh-in every third morning, drifting toward the goal
            src.weights.append(WeighIn(at(d, 7), round(80.6 - 0.04 * i + (0.3 if i % 2 else -0.2), 1)))
        if dow in (0, 3):
            pace = 345 - 1.5 * wk + (0 if dow == 0 else 8)
            a = Activity(f"run-{k}", at(d, 7 if dow == 0 else 19, 0 if dow == 0 else 50), 1800 + 300 * (dow == 0),
                         "running", 1000 * (1800 / pace), 140, 1000 / pace, 45, 2.4)
            src.acts.append(a)
            src.sample_map[a.id] = [Sample(t, 138 + t % 5, 1000 / pace) for t in range(0, int(a.duration_s))]
        if dow in (1, 3):
            a = Activity(f"hiit-{k}", at(d, 18), 2700, "hiit", None, 150, None, 130, 3.6)
            src.acts.append(a)
            for n, (ex, reps, kg, dur) in enumerate([("PUSH_UP/PUSH_UP", 16 + wk // 2, 0, 0),
                                                     ("PLANK/PLANK", 0, 0, 40 + 2 * wk),
                                                     ("KETTLEBELL_SWING/KETTLEBELL_SWING", 15, 16 + 2 * (wk // 4), 0),
                                                     ("LUNGE/LUNGE", 20 - (wk > 6), 0, 0),
                                                     ("SQUAT/AIR_SQUAT", 20 + wk // 3, 0, 0)]):
                src.sets.append(ExerciseSet(a.id, a.start + timedelta(minutes=3 * n), ex, reps, dur, kg))
        if dow in (4, 6):
            src.acts.append(Activity(f"vb-{k}", at(d, 20), 5400, "volleyball", None, 135, None,
                                     130 if dow == 4 else 90, 3.0))
    return src
