"""Write one review on request: report → findings → Claude (or template) → saved."""
from datetime import date

from . import store
from .analysis.report import build_report
from .findings import findings
from .writer import write_review


def run_review(src, start: date, end: date, kind: str) -> int:
    """kind "week": a Mon–Sun week, judged with the week-view rules. "custom": any other range."""
    fp = src.fingerprint()
    report = build_report(src, end, None if kind == "week" else start)
    fs = findings(report)
    text, source = write_review(fs, report)
    return store.save_review(start, end, kind, text, source, fp)
