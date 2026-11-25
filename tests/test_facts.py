"""Background facts for the system prompt, read from the data."""
from fakes import CONTEXT, INDEX, FakeData

from agent.data import DataError
from agent.facts import describe_data


def test_lists_places_with_ids_and_the_home():
    facts = describe_data(FakeData({"index.json": INDEX, "context.json": CONTEXT}))

    assert "ulm = Ulm, muenchen = München" in facts
    assert "The user lives in Ulm" in facts


def test_gives_the_current_time_of_the_data_with_weekday():
    facts = describe_data(FakeData({"index.json": INDEX, "context.json": CONTEXT}))

    assert "It is now Thursday, 29 October 2026, 07:20 (2026-10-29)" in facts
    assert "not your own clock" in facts


def test_gives_the_period_the_data_covers():
    facts = describe_data(FakeData({"index.json": INDEX}))

    assert "The data covers 2026-10-26 to 2026-11-08" in facts


def test_malformed_times_are_left_out():
    facts = describe_data(FakeData({
        "index.json": {"days": {"first": "26.10.2026", "last": None}},
        "context.json": {"now": "morning", "home": "Ulm"},
    }))

    assert facts == "The user lives in Ulm; trips start there unless the user says otherwise."


def test_missing_or_failing_data_gives_no_facts():
    assert describe_data(FakeData()) == ""
    assert describe_data(FakeData({"index.json": DataError("offline"),
                                   "context.json": DataError("offline")})) == ""


def test_unexpected_shapes_are_ignored():
    assert describe_data(FakeData({"index.json": ["ulm"], "context.json": {"home": 3}})) == ""
