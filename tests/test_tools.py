"""The toolbox and the calendar tool."""
import pytest
from fakes import DAY_29, FakeData

from agent.data import DataError
from agent.tools import ALL_TOOLS, Tool, Toolbox
from agent.tools.calendar import NO_DATA_MESSAGE


def test_calendar_reads_the_day_from_the_data_source(toolbox, data):
    outcome = toolbox.run("get_calendar_day", {"date": "2026-10-29"})

    assert outcome.ok
    assert outcome.result == DAY_29
    assert data.requested == ["calendar/2026-10-29.json"]


@pytest.mark.parametrize("bad", ["29.10.2026", "20261029", "2026-13-01", "2026-02-30", "", None, 20261029])
def test_calendar_rejects_invalid_dates_without_fetching(toolbox, data, bad):
    outcome = toolbox.run("get_calendar_day", {"date": bad})

    assert not outcome.ok
    assert "Invalid date" in outcome.result["error"]
    assert data.requested == []


def test_calendar_rejects_missing_date(toolbox):
    outcome = toolbox.run("get_calendar_day", {})

    assert not outcome.ok


def test_calendar_reports_no_data_for_unknown_day(toolbox):
    outcome = toolbox.run("get_calendar_day", {"date": "2026-12-24"})

    assert outcome.ok
    assert outcome.result == {"date": "2026-12-24", "no_data": True, "message": NO_DATA_MESSAGE}
    assert "not say the day is free" in NO_DATA_MESSAGE


def test_data_error_becomes_failed_outcome():
    toolbox = Toolbox(ALL_TOOLS, FakeData({"calendar/2026-10-29.json": DataError("offline")}))

    outcome = toolbox.run("get_calendar_day", {"date": "2026-10-29"})

    assert (outcome.ok, outcome.result) == (False, {"error": "offline"})


def test_bug_in_a_tool_becomes_failed_outcome():
    def broken(args, data):
        raise KeyError("oops")

    toolbox = Toolbox([Tool("broken", "", {"type": "object"}, broken)], FakeData())

    outcome = toolbox.run("broken", {})

    assert not outcome.ok
    assert "KeyError" in outcome.result["error"]


def test_unknown_tool_lists_the_available_ones(toolbox):
    outcome = toolbox.run("book_ticket", {})

    assert not outcome.ok
    assert "get_calendar_day" in outcome.result["error"]


def test_duplicate_tool_names_are_rejected():
    tool = ALL_TOOLS[0]
    with pytest.raises(ValueError):
        Toolbox([tool, tool], FakeData())


def test_every_tool_has_a_valid_schema(toolbox):
    for schema in toolbox.schemas():
        assert schema["type"] == "function"
        function = schema["function"]
        assert function["name"] and function["description"]
        assert function["parameters"]["type"] == "object"
        for name in function["parameters"].get("required", []):
            assert name in function["parameters"]["properties"]
