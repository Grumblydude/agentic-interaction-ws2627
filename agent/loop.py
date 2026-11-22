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
    "You are a personal assistant with tools for the user's calendar, the weather and train "
    "connections. Look up every fact you state with a tool; for several days or places, call "
    "the tool once per day or place. For the weather on a trip, check both the start and the destination. "
    "Never guess or invent appointments, trains, times, prices "
    "or weather. If a tool returns an error, retry with corrected arguments or say what could "
    "not be looked up. no_data means the data has nothing for that place or day: say that it "
    "is unknown instead of filling the gap. In the calendar, an empty list of events means the "
    "day is free, which is not the same as no_data. When you have everything, answer briefly "
    "in plain text without Markdown, with the times, titles, trains and places that matter. "
    "Always answer in the language of the user's question, even if the data is in another "
    "language."
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
              max_steps: int = MAX_STEPS, facts: str = "",
              messages: list[dict] | None = None) -> str:
    """Runs the task to an answer and returns it, or raises AgentError.

    `facts` is appended to the system prompt, e.g. which places have data (see facts.py).
    `messages` continues an earlier conversation (the chat): pass the same list for every
    follow-up. It is extended in place with the task, the tool calls and the answer.
    The step limit applies to each task on its own.
    """
    if messages is None:
        messages = []
    if not messages:
        system_prompt = f"{SYSTEM_PROMPT}\n\n{facts}" if facts else SYSTEM_PROMPT
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": task})

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
            messages.append(reply.as_message())  # so a follow-up question sees this answer
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
