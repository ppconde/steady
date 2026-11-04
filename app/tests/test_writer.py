from datetime import date
from types import SimpleNamespace

import anthropic
import httpx2

from steady import config, writer
from steady.analysis.report import build_report
from steady.demo import FakeSource
from steady.findings import template_text

FS = ["Pace at 140 bpm is 5:22/km."]
R = build_report(FakeSource(), date(2026, 11, 1), today=date(2026, 11, 1))


class Fake:
    def __init__(self, result=None, exc=None):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.result, self.exc = result, exc

    def _create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return self.result


def reply(text, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])


def test_no_key_uses_template(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    fake = Fake(reply("x"))
    assert writer.write_review(FS, R, fake) == (template_text(FS), "template")
    assert fake.calls == []


def test_timeout_falls_back(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "k")
    fake = Fake(exc=anthropic.APITimeoutError(request=httpx2.Request("POST", "https://x")))
    assert writer.write_review(FS, R, fake) == (template_text(FS), "template")


def test_refusal_falls_back(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "k")
    assert writer.write_review(FS, R, Fake(reply("Nice week, pace 5:22/km.", "refusal")))[1] == "template"


def test_invented_number_rejected(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "k")
    assert writer.write_review(FS, R, Fake(reply("pace 5:10/km")))[1] == "template"


def test_claude_text_used(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "k")
    fake = Fake(reply("Nice week, pace 5:22/km."))
    assert writer.write_review(FS, R, fake) == ("Nice week, pace 5:22/km.", "claude")
    (kw,) = fake.calls
    assert kw["model"] == config.CLAUDE_MODEL and kw["fallbacks"] == "default"
    assert "5:22/km" in kw["messages"][0]["content"]


def test_numbers_ok():
    assert writer.numbers_ok("7 of 11, 5:22", "7 of 11 up, 5:22/km")
    assert not writer.numbers_ok("12 sets", "7 of 11")
