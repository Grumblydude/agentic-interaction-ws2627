"""The weather and connections tools: data, gaps without invented values, argument checks."""
import pytest
from fakes import CONNECTIONS_ULM_MUC_29, INDEX, WEATHER_MUC_29, FakeData

from agent.data import DataError
from agent.tools import ALL_TOOLS, Toolbox

# --- weather ----------------------------------------------------------------------------------


def test_weather_reads_place_and_day(toolbox, data):
    outcome = toolbox.run("get_weather", {"city": "muenchen", "date": "2026-10-29"})

    assert outcome.ok
    assert outcome.result == WEATHER_MUC_29
    assert "weather/muenchen/2026-10-29.json" in data.requested


def test_weather_accepts_ids_in_any_case(toolbox):
    outcome = toolbox.run("get_weather", {"city": " Muenchen ", "date": "2026-10-29"})

    assert outcome.result == WEATHER_MUC_29


def test_weather_for_a_day_without_data_is_no_data(toolbox):
    outcome = toolbox.run("get_weather", {"city": "ulm", "date": "2026-10-31"})

    assert outcome.ok
    assert outcome.result["no_data"] is True
    assert "Do not guess" in outcome.result["message"]
    assert "temp_c" not in outcome.result


@pytest.mark.parametrize("city", ["berlin", "munich", "München"])
def test_weather_for_an_unknown_place_lists_the_known_ones_without_fetching(toolbox, data, city):
    outcome = toolbox.run("get_weather", {"city": city, "date": "2026-10-29"})

    assert outcome.ok
    assert outcome.result["no_data"] is True
    assert "muenchen (München)" in outcome.result["message"]
    assert not any(path.startswith("weather/") for path in data.requested)


@pytest.mark.parametrize("args", [
    {"city": "ulm", "date": "29.10.2026"},
    {"city": "ulm"},
    {"date": "2026-10-29"},
    {"city": "", "date": "2026-10-29"},
    {"city": 7, "date": "2026-10-29"},
])
def test_weather_rejects_invalid_arguments(toolbox, args):
    outcome = toolbox.run("get_weather", args)

    assert not outcome.ok
    assert "error" in outcome.result


# --- connections ------------------------------------------------------------------------------


def test_connections_read_route_and_day(toolbox, data):
    outcome = toolbox.run("get_connections",
                          {"origin": "ulm", "destination": "muenchen", "date": "2026-10-29"})

    assert outcome.ok
    assert outcome.result == CONNECTIONS_ULM_MUC_29
    assert "transit/ulm/muenchen/2026-10-29.json" in data.requested


def test_connections_for_a_route_and_day_without_data_are_no_data(toolbox):
    outcome = toolbox.run("get_connections",
                          {"origin": "muenchen", "destination": "ulm", "date": "2026-11-05"})

    assert outcome.ok
    assert outcome.result["no_data"] is True
    assert "Do not make up" in outcome.result["message"]
    assert "connections" not in outcome.result


@pytest.mark.parametrize("args", [
    {"origin": "berlin", "destination": "muenchen", "date": "2026-10-29"},
    {"origin": "ulm", "destination": "hamburg", "date": "2026-10-29"},
])
def test_connections_to_or_from_an_unknown_place_are_no_data(toolbox, data, args):
    outcome = toolbox.run("get_connections", args)

    assert outcome.ok
    assert outcome.result["no_data"] is True
    assert not any(path.startswith("transit/") for path in data.requested)


def test_connections_need_two_different_places(toolbox):
    outcome = toolbox.run("get_connections",
                          {"origin": "ulm", "destination": "ulm", "date": "2026-10-29"})

    assert not outcome.ok
    assert "same place" in outcome.result["error"]


# --- without a list of places -----------------------------------------------------------------


def test_without_index_any_plain_place_id_is_tried():
    data = FakeData({"weather/ulm/2026-10-29.json": {"condition": "sonnig"}})
    toolbox = Toolbox(ALL_TOOLS, data)

    assert toolbox.run("get_weather", {"city": "ulm", "date": "2026-10-29"}).result == {
        "condition": "sonnig"}
    assert toolbox.run("get_weather", {"city": "berlin", "date": "2026-10-29"}).result["no_data"]


@pytest.mark.parametrize("city", ["../calendar", "ulm/x", "Ulm München"])
def test_without_index_place_ids_cannot_change_the_path(city):
    data = FakeData()
    toolbox = Toolbox(ALL_TOOLS, data)

    outcome = toolbox.run("get_weather", {"city": city, "date": "2026-10-29"})

    assert not outcome.ok
    assert not any(path.startswith("weather/") for path in data.requested)


def test_unreachable_index_is_a_failed_tool_call():
    data = FakeData({"index.json": DataError("offline"), "weather/ulm/2026-10-29.json": {}})

    outcome = Toolbox(ALL_TOOLS, data).run("get_weather", {"city": "ulm", "date": "2026-10-29"})

    assert (outcome.ok, outcome.result) == (False, {"error": "offline"})


def test_index_fixture_matches_the_real_shape():
    assert set(INDEX["cities"]) == {"ulm", "muenchen"}
