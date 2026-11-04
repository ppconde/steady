"""In-memory DataSource: used by tests and by `python -m modform --demo`."""
from dataclasses import dataclass, field
from datetime import datetime

from .models import Activity, ExerciseSet, Night, Sample


@dataclass
class FakeSource:
    acts: list[Activity] = field(default_factory=list)
    sets: list[ExerciseSet] = field(default_factory=list)
    night_list: list[Night] = field(default_factory=list)
    sample_map: dict[str, list[Sample]] = field(default_factory=dict)
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

    def fingerprint(self):
        return self.fp

    def last_sync(self):
        return self.synced
