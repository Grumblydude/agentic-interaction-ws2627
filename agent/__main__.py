"""Entry point: python -m agent "<task>" answers one task; without a task it starts a chat."""
import sys
import time

from .config import load_config
from .data import HttpDataSource
from .facts import describe_data
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
    """Interactive mode: one conversation, so follow-up questions see the earlier ones.

    The whole chat is one run with one log file; every question in it is logged from
    user_task to final (or error). 'new' starts a fresh conversation, 'exit' ends the chat.
    """
    print("Assistant for calendar, weather and trains. 'new' starts over, 'exit' quits.")
    log = RunLog()
    session = None  # set up on the first question, so 'exit' needs no configuration
    messages: list[dict] = []
    while True:
        try:
            task = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if task.lower() in ("exit", "quit"):
            return 0
        if task.lower() in ("new", "/new"):
            messages.clear()
            print("New conversation.")
            continue
        if not task:
            continue

        if session is None:
            try:
                session = _connect(log)
            except RuntimeError as err:
                return _fail(log, task, str(err), reason="config", steps=0, duration_ms=0)
        model, toolbox, facts = session

        print("Agent: ", end="", flush=True)
        before = len(messages)
        if answer_task(task, model, toolbox, log, facts=facts, messages=messages) != 0:
            # Forget the failed question, so the conversation stays as it was before it.
            del messages[before:]


def ask(task: str) -> int:
    """Sets up model, tools and log from the configuration and answers one task."""
    log = RunLog()
    try:
        model, toolbox, facts = _connect(log)
    except RuntimeError as err:
        return _fail(log, task, str(err), reason="config", steps=0, duration_ms=0)
    return answer_task(task, model, toolbox, log, facts=facts)


def _connect(log: RunLog) -> tuple[ChatModel, Toolbox, str]:
    """Model, tools and system-prompt facts from the configuration. RuntimeError if settings are missing."""
    config = load_config()
    log.model = config.model
    model = OpenAIChatModel(
        base_url=config.openai_base_url, api_key=config.openai_api_key, model=config.model
    )
    data = HttpDataSource(config.data_base_url)
    return model, Toolbox(ALL_TOOLS, data), describe_data(data)


def answer_task(task: str, model: ChatModel, toolbox: Toolbox, log: RunLog,
                max_steps: int = MAX_STEPS, facts: str = "",
                messages: list[dict] | None = None) -> int:
    """Runs one task. Answer to stdout and exit code 0, or error to stderr and exit code 1."""
    start = time.perf_counter()
    log.write("user_task", task=task)
    try:
        answer = run_agent(task, model, toolbox, log, max_steps=max_steps, facts=facts,
                           messages=messages)
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
