"""The agent loop: several steps, a visible end, and errors along the way."""
import json

import pytest
from fakes import ScriptedModel, answer, calendar_calls, events, raw_call, read_log, tool_calls

from agent.data import DataError
from agent.loop import AgentError, run_agent
from agent.model import ModelError, ModelReply


def tool_messages(request: list[dict]) -> list[dict]:
    return [json.loads(m["content"]) for m in request if m["role"] == "tool"]


# --- several steps ----------------------------------------------------------------------------

def test_task_over_two_days_runs_through_several_steps(toolbox, data, log):
    model = ScriptedModel(
        calendar_calls("2026-10-29"),
        calendar_calls("2026-10-30"),
        answer("29 Oct: Standup. 30 Oct: Review."),
    )

    result = run_agent("What is on 29 Oct and 30 Oct?", model, toolbox, log)

    assert result == "29 Oct: Standup. 30 Oct: Review."
    assert data.requested == ["calendar/2026-10-29.json", "calendar/2026-10-30.json"]
    assert events(log.path) == ["tool_call", "tool_result", "tool_call", "tool_result", "final"]
    assert read_log(log.path)[-1]["step"] == 3


def test_model_sees_the_results_of_earlier_steps(toolbox, log):
    model = ScriptedModel(calendar_calls("2026-10-29"), calendar_calls("2026-10-30"), answer("ok"))

    run_agent("task", model, toolbox, log)

    last_request = model.requests[-1]
    titles = [r["events"][0]["title"] for r in tool_messages(last_request)]
    assert titles == ["Standup", "Review"]


def test_several_tool_calls_in_one_step(toolbox, log):
    model = ScriptedModel(calendar_calls("2026-10-29", "2026-10-30"), answer("both days"))

    assert run_agent("task", model, toolbox, log) == "both days"

    request = model.requests[-1]
    assert [m["tool_call_id"] for m in request if m["role"] == "tool"] == [
        "call_2026-10-29", "call_2026-10-30"]
    assert read_log(log.path)[-1]["step"] == 2


def test_answer_without_tool_call_ends_after_one_step(toolbox, data, log):
    model = ScriptedModel(answer("Hello"))

    assert run_agent("Hi", model, toolbox, log) == "Hello"
    assert data.requested == []
    assert events(log.path) == ["final"]


def test_task_with_two_different_tools(toolbox, data, log):
    model = ScriptedModel(
        tool_calls(("get_connections", {"origin": "ulm", "destination": "muenchen", "date": "2026-10-29"}),
                   ("get_weather", {"city": "muenchen", "date": "2026-10-29"})),
        answer("ICE 596 at 08:12. Rain 60 %, take an umbrella."),
    )

    assert run_agent("To Munich on 29 Oct, umbrella?", model, toolbox, log).startswith("ICE 596")

    results = [r for r in read_log(log.path) if r["event"] == "tool_result"]
    assert [(r["tool"], r["ok"]) for r in results] == [("get_connections", True), ("get_weather", True)]
    assert [r["train"] for r in tool_messages(model.requests[-1])[0]["connections"]] == ["ICE 596"]
    assert tool_messages(model.requests[-1])[1]["rain_probability"] == 0.6


def test_facts_are_added_to_the_system_prompt(toolbox, log):
    model = ScriptedModel(answer("ok"))

    run_agent("task", model, toolbox, log, facts="The user lives in Ulm.")

    system = model.requests[0][0]
    assert system["role"] == "system"
    assert system["content"].endswith("\n\nThe user lives in Ulm.")


# --- a visible end ----------------------------------------------------------------------------

def test_step_limit_ends_as_error_not_as_success(toolbox, log):
    model = ScriptedModel(calendar_calls("2026-10-29"), repeat_last=True)

    with pytest.raises(AgentError) as caught:
        run_agent("task", model, toolbox, log, max_steps=3)

    assert caught.value.reason == "step_limit"
    assert caught.value.steps == 3
    assert len(model.requests) == 3
    assert "final" not in events(log.path)


def test_failed_steps_count_towards_the_step_limit(toolbox, log):
    model = ScriptedModel(ModelError("temporary", recoverable=True), repeat_last=True)

    with pytest.raises(AgentError) as caught:
        run_agent("task", model, toolbox, log, max_steps=4)

    assert caught.value.reason == "step_limit"
    assert len(model.requests) == 4


def test_permanent_model_error_ends_the_run_at_once(toolbox, log):
    model = ScriptedModel(ModelError("invalid API key", recoverable=False), answer("never reached"))

    with pytest.raises(AgentError) as caught:
        run_agent("task", model, toolbox, log)

    assert caught.value.reason == "model_error"
    assert len(model.requests) == 1


# --- errors along the way ---------------------------------------------------------------------

def test_failing_tool_does_not_abort_the_run(toolbox, data, log):
    data.documents["calendar/2026-10-29.json"] = DataError("HTTP 500 for calendar/2026-10-29.json")
    model = ScriptedModel(
        calendar_calls("2026-10-29"),
        calendar_calls("2026-10-30"),
        answer("29 Oct could not be loaded. 30 Oct: Review."),
    )

    run_agent("task", model, toolbox, log)

    results = [r for r in read_log(log.path) if r["event"] == "tool_result"]
    assert [r["ok"] for r in results] == [False, True]
    assert "HTTP 500" in results[0]["result"]["error"]
    assert events(log.path)[-1] == "final"


def test_missing_day_is_reported_as_no_data(toolbox, log):
    model = ScriptedModel(calendar_calls("2026-12-24"), answer("No data for that day."))

    run_agent("task", model, toolbox, log)

    result = [r for r in read_log(log.path) if r["event"] == "tool_result"][0]
    assert result["ok"] is True
    assert result["result"]["no_data"] is True


def test_invalid_argument_goes_back_to_the_model(toolbox, log):
    model = ScriptedModel(
        raw_call("get_calendar_day", '{"date": "29.10.2026"}'),
        calendar_calls("2026-10-29"),
        answer("Standup"),
    )

    assert run_agent("task", model, toolbox, log) == "Standup"
    error = tool_messages(model.requests[1])[0]["error"]
    assert "YYYY-MM-DD" in error


def test_broken_json_arguments_go_back_to_the_model(toolbox, log):
    model = ScriptedModel(raw_call("get_calendar_day", '{"date": '), answer("sorry"))

    run_agent("task", model, toolbox, log)

    call = [r for r in read_log(log.path) if r["event"] == "tool_call"][0]
    assert call["raw_arguments"] == '{"date": '
    assert "not valid JSON" in tool_messages(model.requests[1])[0]["error"]


def test_unknown_tool_goes_back_to_the_model(toolbox, log):
    model = ScriptedModel(raw_call("book_ticket", '{"train": "ICE 596"}'), answer("cannot book"))

    run_agent("task", model, toolbox, log)

    error = tool_messages(model.requests[1])[0]["error"]
    assert "Unknown tool 'book_ticket'" in error
    assert "get_calendar_day, get_weather, get_connections" in error


def test_temporary_model_error_is_logged_and_the_run_goes_on(toolbox, log):
    model = ScriptedModel(ModelError("tool_use_failed", recoverable=True), answer("ok"))

    assert run_agent("task", model, toolbox, log) == "ok"

    first, last = read_log(log.path)
    assert (first["event"], first["fatal"], first["ok"]) == ("error", False, False)
    assert (last["event"], last["step"]) == ("final", 2)


def test_empty_reply_counts_as_failed_step(toolbox, log):
    model = ScriptedModel(ModelReply(), answer("ok"))

    assert run_agent("task", model, toolbox, log) == "ok"
    assert events(log.path) == ["error", "final"]
