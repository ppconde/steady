from datetime import date

from steady import review, store
from steady.demo import demo_source


def test_week_review_uses_week_rules():
    today = date(2026, 11, 4)
    rid = review.run_review(demo_source(today), date(2026, 11, 2), today, "week")
    assert "previous 4 weeks" in store.get_review(rid)["text"]  # not "previous 3 days"
