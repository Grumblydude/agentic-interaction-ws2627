"""Background facts for the system prompt, read from the data."""
from fakes import CONTEXT, INDEX, FakeData

from agent.data import DataError
from agent.facts import describe_data


def test_lists_places_with_ids_and_the_home():
    facts = describe_data(FakeData({"index.json": INDEX, "context.json": CONTEXT}))

    assert "ulm = Ulm, muenchen = München" in facts
    assert "The user lives in Ulm" in facts


def test_missing_or_failing_data_gives_no_facts():
    assert describe_data(FakeData()) == ""
    assert describe_data(FakeData({"index.json": DataError("offline"),
                                   "context.json": DataError("offline")})) == ""


def test_unexpected_shapes_are_ignored():
    assert describe_data(FakeData({"index.json": ["ulm"], "context.json": {"home": 3}})) == ""
