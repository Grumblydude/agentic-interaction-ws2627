"""Entry point: python -m agent "<task>" answers one task; without a task it starts a chat."""
import sys
import time

from .config import load_config
from .data import HttpDataSource
from .loop import MAX_STEPS, AgentError, elapsed_ms, run_agent
from .model import ChatModel, OpenAIChatModel
from .runlog import RunLog
from .tools import ALL_TOOLS, Toolbox


def main(argv: list[str] | None = None) -> int:
    # When output is piped on Windows, the console code page cannot encode every character of an
    # answer (e.g. "→"). Replace those instead of crashing after the answer has been logged.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return chat()
    return ask(" ".join(argv))


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
    """Sets up model, tools and log from the configuration and answers one task."""
    log = RunLog()
    try:
        config = load_config()
    except RuntimeError as err:
        return _fail(log, task, str(err), reason="config", steps=0, duration_ms=0)

    log.model = config.model
    model = OpenAIChatModel(
        base_url=config.openai_base_url, api_key=config.openai_api_key, model=config.model
    )
    toolbox = Toolbox(ALL_TOOLS, HttpDataSource(config.data_base_url))
    return answer_task(task, model, toolbox, log)


def answer_task(task: str, model: ChatModel, toolbox: Toolbox, log: RunLog,
                max_steps: int = MAX_STEPS) -> int:
    """Runs one task. Answer to stdout and exit code 0, or error to stderr and exit code 1."""
    start = time.perf_counter()
    log.write("user_task", task=task)
    try:
        answer = run_agent(task, model, toolbox, log, max_steps=max_steps)
    except AgentError as err:
        return _fail(log, task, str(err), reason=err.reason, steps=err.steps,
                     duration_ms=elapsed_ms(start))
    except Exception as err:  # a bug must still end the run with a logged error, not a traceback
        return _fail(log, task, f"Unexpected error: {type(err).__name__}: {err}",
                     reason="exception", steps=None, duration_ms=elapsed_ms(start))

    print(answer)
    return 0


def _fail(log: RunLog, task: str, message: str, *, reason: str, steps: int | None,
          duration_ms: int) -> int:
    log.write("error", ok=False, duration_ms=duration_ms, fatal=True, reason=reason,
              steps=steps, task=task, error=message)
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
