"""The agent loop: model call, tool calls, model call, ... until the model answers.

Every step is one model call. A failed step (a tool error, a broken model reply, a model call
that fails for a temporary reason) is logged and the loop goes on. The run ends with an answer,
or with an AgentError when the step limit is reached or the model cannot be used at all.
"""
import json
import time

from .model import ChatModel, ModelError, ToolCall
from .runlog import RunLog
from .tools import Toolbox, ToolOutcome

SYSTEM_PROMPT = (
    "You are a calendar assistant. For any question about appointments or the schedule "
    "of a day, call get_calendar_day for that date; for several days, call it once per day. "
    "Never guess calendar contents. If a tool returns an error, retry with corrected "
    "arguments or say what could not be looked up. When you have everything, answer briefly "
    "in plain text without Markdown, listing times, titles and locations. Always answer in "
    "the language of the user's question, even if the calendar data is in another language. "
    "An empty list of events means the day is free; no_data means the calendar has no data "
    "for that day, which is not the same, so say that the day could not be checked."
)

# Upper bound on model calls per run, so a model that keeps calling tools cannot loop forever.
MAX_STEPS = 8


class AgentError(Exception):
    """The run ended without an answer. `reason` is a short code for the log."""

    def __init__(self, message: str, *, reason: str, steps: int):
        super().__init__(message)
        self.reason = reason
        self.steps = steps


def elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def run_agent(task: str, model: ChatModel, toolbox: Toolbox, log: RunLog,
              max_steps: int = MAX_STEPS) -> str:
    """Runs the task to an answer and returns it, or raises AgentError."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        start = time.perf_counter()
        try:
            reply = model.complete(messages, toolbox.schemas())
        except ModelError as err:
            if not err.recoverable:
                raise AgentError(str(err), reason="model_error", steps=step) from err
            log.write("error", ok=False, duration_ms=elapsed_ms(start),
                      step=step, fatal=False, error=str(err))
            continue
        model_ms = elapsed_ms(start)

        if reply.tool_calls:
            messages.append(reply.as_message())
            for call in reply.tool_calls:
                messages.append(_run_tool_call(call, toolbox, log, step, model_ms))
            continue

        if reply.content:
            log.write("final", duration_ms=model_ms, step=step, answer=reply.content)
            return reply.content

        log.write("error", ok=False, duration_ms=model_ms, step=step, fatal=False,
                  error="Model returned neither an answer nor a tool call.")

    raise AgentError(f"No final answer after {max_steps} steps.", reason="step_limit", steps=max_steps)


def _run_tool_call(call: ToolCall, toolbox: Toolbox, log: RunLog, step: int, model_ms: int) -> dict:
    """Runs one tool call, logs it and returns the tool message for the conversation."""
    args, problem = _parse_arguments(call.arguments)
    extra = {"raw_arguments": call.arguments} if problem else {}
    log.write("tool_call", tool=call.name, args=args, duration_ms=model_ms, step=step, **extra)

    start = time.perf_counter()
    outcome = ToolOutcome(False, {"error": problem}) if problem else toolbox.run(call.name, args)
    log.write("tool_result", tool=call.name, args=args, ok=outcome.ok,
              duration_ms=elapsed_ms(start), step=step, result=outcome.result)

    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": json.dumps(outcome.result, ensure_ascii=False),
    }


def _parse_arguments(text: str) -> tuple[dict, str | None]:
    """Returns (arguments, None), or ({}, problem) if the model wrote no valid JSON object."""
    if not text.strip():
        return {}, None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}, f"Arguments are not valid JSON: {text!r}"
    if not isinstance(value, dict):
        return {}, "Arguments must be a JSON object."
    return value, None
