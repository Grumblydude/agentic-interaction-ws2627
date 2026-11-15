"""Test doubles: a scripted model and an in-memory DATA_BASE_URL, so tests need no network or key."""
import json
from pathlib import Path

from agent.model import ModelReply, ToolCall


class FakeData:
    """Maps paths to JSON documents. A missing path is "no data" (like HTTP 404);
    an exception as value is raised, like a failing request."""

    def __init__(self, documents: dict | None = None):
        self.documents = documents or {}
        self.requested: list[str] = []

    def get_json(self, path: str):
        self.requested.append(path)
        value = self.documents.get(path)
        if isinstance(value, Exception):
            raise value
        return value


class ScriptedModel:
    """Returns the scripted replies in order. An exception in the script is raised instead.
    `repeat_last=True` keeps returning the last reply, for step-limit tests."""

    name = "fake-model"

    def __init__(self, *replies, repeat_last: bool = False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.requests: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        self.requests.append([dict(message) for message in messages])
        if not self.replies:
            raise AssertionError("ScriptedModel ran out of replies.")
        reply = self.replies[0] if self.repeat_last and len(self.replies) == 1 else self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def calendar_calls(*dates: str) -> ModelReply:
    """A model reply that calls get_calendar_day once per date, all in one step."""
    return ModelReply(tool_calls=tuple(
        ToolCall(id=f"call_{date}", name="get_calendar_day", arguments=json.dumps({"date": date}))
        for date in dates
    ))


def raw_call(name: str, arguments: str, call_id: str = "call_raw") -> ModelReply:
    """A model reply with one tool call whose arguments are given as raw text."""
    return ModelReply(tool_calls=(ToolCall(id=call_id, name=name, arguments=arguments),))


def answer(text: str) -> ModelReply:
    return ModelReply(content=text)


def read_log(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def events(path: Path) -> list[str]:
    return [record["event"] for record in read_log(path)]


DAY_29 = {
    "date": "2026-10-29",
    "events": [
        {"id": "t-1", "start": "09:00", "end": "10:00", "title": "Standup", "location": "O27/3302"},
    ],
}
DAY_30 = {
    "date": "2026-10-30",
    "events": [
        {"id": "t-2", "start": "14:00", "end": "15:00", "title": "Review", "location": "online"},
    ],
}
