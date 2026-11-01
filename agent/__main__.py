"""Entry point: python -m agent "<task>"."""
import json
import sys
import time

from openai import OpenAI

from .config import Config, load_config
from .runlog import RunLog
from .tools import TOOLS, run_tool

SYSTEM_PROMPT = (
    "You are a calendar assistant. For any question about appointments or the schedule "
    "of a day, call get_calendar_day for that date. Never guess calendar contents. "
    "Answer briefly in the language of the question, listing times, titles and locations. "
    "If the tool reports no data or no appointments, say so."
)

# Upper bound on model calls, so a model that keeps calling tools cannot loop forever.
MAX_STEPS = 5


def elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def run(task: str, config: Config, log: RunLog) -> str:
    # Only gzip: an outdated brotli package in the environment (e.g. conda base) breaks decoding.
    client = OpenAI(
        base_url=config.openai_base_url,
        api_key=config.openai_api_key,
        default_headers={"Accept-Encoding": "gzip, deflate"},
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for _ in range(MAX_STEPS):
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=config.model, messages=messages, tools=TOOLS, tool_choice="auto"
        )
        model_ms = elapsed_ms(start)
        message = response.choices[0].message

        if not message.tool_calls:
            answer = (message.content or "").strip()
            log.write("final", duration_ms=model_ms, answer=answer)
            return answer

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [call.model_dump() for call in message.tool_calls],
        })
        for call in message.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            log.write("tool_call", tool=name, args=args, duration_ms=model_ms)

            start = time.perf_counter()
            try:
                result = run_tool(name, args, config.data_base_url)
            except Exception as err:
                result = {"error": f"Tool failed: {err}"}
            ok = "error" not in result
            log.write("tool_result", tool=name, args=args, ok=ok,
                      duration_ms=elapsed_ms(start), result=result)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    raise RuntimeError(f"No final answer after {MAX_STEPS} model calls.")


def main() -> int:
    if len(sys.argv) < 2:
        return chat()
    return ask(" ".join(sys.argv[1:]))


def chat() -> int:
    """Interactive mode: each question is its own run with its own log file."""
    print("Calendar agent. Type 'exit' to quit.")
    while True:
        try:
            task = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if task.lower() in ("exit", "quit"):
            return 0
        if task:
            print("Agent: ", end="", flush=True)
            ask(task)


def ask(task: str) -> int:
    log = RunLog()
    start = time.perf_counter()
    try:
        config = load_config()
        log.model = config.model
        log.write("user_task", task=task)
        answer = run(task, config, log)
    except Exception as err:
        log.write("error", ok=False, duration_ms=elapsed_ms(start), task=task, error=str(err))
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
