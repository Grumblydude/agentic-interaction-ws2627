# agentic-interaction-ws2627

Agent for the course *Agentic Human-AI Interaction*, winter term 2026/27, Ulm University.

## Setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then put your API key into .env
```

`.env` holds `OPENAI_BASE_URL`, `MODEL`, `OPENAI_API_KEY` and `DATA_BASE_URL`.
Environment variables take precedence over `.env`.

## Run

From the repository root:

```bash
python -m agent "How do I get to Munich on 29 Oct 2026, and do I need an umbrella?"
```

The answer is printed to standard output, with exit code 0. If the run ends without an answer
(step limit reached, model unusable, missing settings), the message goes to standard error and
the exit code is 1.

### Interactive chat

Without a question, `python -m agent` starts a chat. It is one conversation, so follow-ups work
("And do I need an umbrella there?", "Which of those trains arrives before 9:30?"). Type `new`
to start a fresh conversation and `exit` to quit.

- The whole chat is one run with one log file. Every question in it is logged from `user_task`
  to `final` or `error`, and the step limit applies to each question on its own.
- A question that fails (e.g. step limit) is dropped from the conversation, and the chat goes on.
- Every question resends the conversation so far. In a long chat, use `new` to stay within the
  free tier's 8,000 tokens per minute.

`python -m agent "<question>"` is not affected: one task, one run, one log, as before.

On Windows, `.\chat.bat` (or a double-click) checks Python, creates `.venv` if needed, installs
missing packages, activates `.venv` and starts the chat.

## How it works

### Tools

| Tool | Reads from `DATA_BASE_URL` | For |
|---|---|---|
| `get_calendar_day(date)` | `calendar/{date}.json` | Appointments of one day |
| `get_weather(city, date)` | `weather/{city}/{date}.json` | Condition, temperature, rain probability, wind |
| `get_connections(origin, destination, date)` | `transit/{origin}/{destination}/{date}.json` | Trains: departure, arrival, changes, price |

At startup the agent reads `index.json` (places with data and their ids, e.g. `muenchen` for
München) and `context.json` (the user's home, Ulm) and adds both to the system prompt. Nothing
about places is written into the code, and a question like "How do I get to Munich?" starts at
home.

**Gaps.** The data has weather and trains only for a few days. Whenever there is nothing, the
tool says so instead of returning values, and the model is told to report it as unknown:

| Case | Tool result |
|---|---|
| Day without data (HTTP 404) | `{"no_data": true, "message": "... Do not guess ..."}` |
| Place not in `index.json`, e.g. `berlin` | `{"no_data": true, ...}` listing the places that have data, without a request |
| Calendar day with an empty list | The day is free, which is not the same as `no_data` |

Place ids are matched in lower case. If `index.json` cannot be read, only plain ids like `ulm` are
accepted, so an argument cannot change the request path.

### The loop

Every step is one model call. The loop runs until the model answers without calling a tool:

1. The task goes to the model together with the tool descriptions.
2. If the model calls tools, the agent runs each call and sends the results back. That is the
   next step. The model can call several tools in one step or one after another.
3. If the model answers, the run ends with that answer.

**A visible end.** A run takes at most `MAX_STEPS` (8) model calls. If there is still no answer
then, the run ends as an error (`reason: "step_limit"`, exit code 1), never as a success.

**Errors along the way** do not abort the run. They are logged and the loop goes on:

| What goes wrong | What happens |
|---|---|
| Data cannot be fetched (network, HTTP 5xx, bad JSON) | Tool result `{"error": ...}` with `ok: false`; the model decides what to do |
| Invalid or broken arguments, unknown tool | Same: the error goes back to the model, which can correct itself |
| A bug inside a tool | Same, so one tool cannot crash the run |
| Model call fails temporarily (e.g. Groq `tool_use_failed`, timeout) | Logged as `error` with `fatal: false`; the step counts and the loop asks again |
| Model returns neither answer nor tool call | Same as a temporary failure |
| Rate limit (429), server error, connection error | First retried by the OpenAI SDK with backoff, then as above |
| Wrong API key, no access, unknown model | Asking again cannot help: the run ends at once (`reason: "model_error"`) |

HTTP 404 from the data means "no data". It comes back as `{"no_data": true}` with `ok: true`,
not as a failure.

### Code

| File | Purpose |
|---|---|
| `agent/__main__.py` | Command line, wiring, exit codes |
| `agent/loop.py` | The agent loop, step limit, system prompt |
| `agent/model.py` | Model calls via the OpenAI SDK, reduced to `ModelReply`; sorts errors into temporary and permanent |
| `agent/tools/base.py` | `Tool` and `Toolbox`: runs a tool by name and turns every failure into a result |
| `agent/tools/calendar.py` | `get_calendar_day(date)` |
| `agent/tools/weather.py` | `get_weather(city, date)` |
| `agent/tools/transit.py` | `get_connections(origin, destination, date)` |
| `agent/tools/args.py` | Shared checks for dates and place ids |
| `agent/facts.py` | Places and home from the data, for the system prompt |
| `agent/data.py` | Reads JSON from `DATA_BASE_URL`; 404 becomes "no data" |
| `agent/config.py` | Reads settings from the environment and `.env` |
| `agent/runlog.py` | Writes the JSONL run log |

**Adding a tool:** write its handler and `Tool` in a new module under `agent/tools/` (see
`calendar.py`), add it to `ALL_TOOLS` in `agent/tools/__init__.py` and add tests. The loop stays
as it is.

## Logs

Each run writes its own file `logs/<timestamp>_<run>.jsonl`, one JSON object per line with the
fields `ts`, `run_id`, `event` (`user_task`, `tool_call`, `tool_result`, `final`, `error`),
`tool`, `args`, `ok`, `model` and `duration_ms`. `logs/` is not committed.

Additional fields show how a run went:

- `step` on every event inside the loop: which model call it belongs to.
- How the run ended is always the **last line**: either `final` (with `answer`) or `error` with
  `fatal: true`, a `reason` (`step_limit`, `model_error`, `config`, `exception`) and `steps`.
- `error` with `fatal: false` is a failed step the run recovered from.
- `tool_result` carries the `result` the model saw; `tool_call` with broken arguments also has
  `raw_arguments`.

Show the newest log in PowerShell:

```powershell
Get-Content (Get-ChildItem logs\*.jsonl | Sort-Object LastWriteTime | Select-Object -Last 1)
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests use a scripted fake model and in-memory data, so they need no API key or network and
cost no tokens. GitHub Actions runs them on every push (`.github/workflows/tests.yml`).

| File | Covers |
|---|---|
| `tests/test_loop.py` | Several steps, two different tools in one task, step limit, every kind of error along the way |
| `tests/test_cli.py` | Exit codes, stdout/stderr and the last log line; the chat keeps one conversation |
| `tests/test_tools.py` | Calendar tool, argument checks, toolbox error handling |
| `tests/test_travel_tools.py` | Weather and connections: data, days and places without data, argument checks |
| `tests/test_facts.py` | Places and home for the system prompt |
| `tests/test_data.py` | URL building, 404, network and JSON errors |
| `tests/test_model.py` | Mapping SDK replies, temporary vs. permanent SDK errors |
| `tests/test_live.py` | End to end against the real model; only with `AGENT_LIVE_TESTS=1` |

The live tests make real model calls. The free tier allows 8,000 tokens per minute, so run them
on their own:

```bash
AGENT_LIVE_TESTS=1 python -m pytest tests/test_live.py      # PowerShell: $env:AGENT_LIVE_TESTS=1
```

### Tasks to try by hand

Check the log after each run: which tools were called, with which arguments, and how it ended.

| Task | What the log should show |
|---|---|
| `"How do I get to Munich on 29 Oct 2026, and do I need an umbrella?"` | `get_connections` (ulm → muenchen) and `get_weather`, then `final` naming a train and the weather |
| `"How do I get back from Munich to Ulm on 30 Oct 2026, and will it rain in Munich?"` | Both results with `no_data: true`; the answer says both are unknown, with no times or weather |
| `"What is the weather in Berlin on 29 Oct 2026?"` | No values: the answer says there is no data for Berlin |
| `"What is on 29 Oct 2026 and on 30 Oct 2026?"` | Two `get_calendar_day` calls, then `final` |
| `"Was steht am 29.10.2026 im Kalender?"` | The question from exercise 1: one call, then `final` |
| `"What is on 29 Oct 2026 and on 24 Dec 2026?"` | One result with `no_data: true`; the answer says 24 Dec could not be checked, not that it is free |
| Same task with `DATA_BASE_URL=https://nonexistent.invalid/v1` | `tool_result` with `ok: false`, still a `final` answer, exit code 0 |
| `"Go through every day from 26 Oct to 8 Nov 2026 one at a time and list all appointments."` | Probably hits the step limit: last line `error`, `reason: "step_limit"`, exit code 1 |
