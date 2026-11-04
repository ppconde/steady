"""The written review: Claude when available, the findings template otherwise."""
import json
import logging
import re
from typing import Literal

import anthropic

from . import config
from .analysis.report import Report, report_json
from .findings import template_text

log = logging.getLogger(__name__)
NUM = re.compile(r"\d+(?:[.:,]\d+)*")
SYSTEM = ("You write a short weekly training review for one person from their Garmin data. "
          "Write one friendly paragraph of at most 150 words. The verdicts in the findings are final; "
          "don't contradict them. You may point out patterns visible in the summary. "
          "Use only numbers that appear in the input. No medical advice, no plans or future workouts, no diet or calorie advice.")


def numbers_ok(text: str, source: str) -> bool:
    return set(NUM.findall(text)) <= set(NUM.findall(source))


def _payload(fs: list[str], report: Report) -> str:
    bullets = "\n".join(f"- {f}" for f in fs)
    return f"Goal: {config.GOAL}\n\nFindings:\n{bullets}\n\nSummary:\n{json.dumps(report_json(report))}"


def write_review(fs: list[str], report: Report, client=None) -> tuple[str, Literal["claude", "template"]]:
    fallback = (template_text(fs), "template")
    if not config.ANTHROPIC_API_KEY:
        return fallback
    payload = _payload(fs, report)
    client = client or anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=60.0, max_retries=2)
    try:
        msg = client.beta.messages.create(
            model=config.CLAUDE_MODEL, max_tokens=2000, output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=SYSTEM, messages=[{"role": "user", "content": payload}])
    except anthropic.APIError as e:  # covers connection and timeout errors
        log.warning("review: Claude call failed (%s), using template", type(e).__name__)
        return fallback
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    if msg.stop_reason in ("refusal", "max_tokens") or not text:
        log.warning("review: stop_reason=%s, empty=%s, using template", msg.stop_reason, not text)
        return fallback
    if not numbers_ok(text, payload):
        log.warning("review: text had numbers not in the input, using template")
        return fallback
    return text, "claude"
