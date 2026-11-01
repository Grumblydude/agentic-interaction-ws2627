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
python -m agent "Was steht am 29.10.2026 im Kalender?"
```

The answer is printed to standard output, with exit code 0. On an error the message goes to
standard error and the exit code is 1.

### Interactive chat

Without a question, `python -m agent` starts a prompt where you can ask one question after
another. Each question is its own run with its own log; the agent does not remember earlier
questions. Type `exit` to quit.

On Windows, `.\chat.bat` (or a double-click) does the same and creates `.venv` on first use.

## How it works

1. The question goes to the model together with one tool, `get_calendar_day(date)`.
2. The model calls the tool. The agent fetches `{DATA_BASE_URL}/calendar/{date}.json` and
   returns the appointments to the model. HTTP 404 comes back as "no data", not as a crash.
3. The model answers from the result.

| File | Purpose |
|---|---|
| `agent/__main__.py` | Entry point and the model → tool → model loop |
| `agent/tools.py` | Tool description for the model and its implementation |
| `agent/config.py` | Reads settings from the environment and `.env` |
| `agent/runlog.py` | Writes the JSONL run log |

## Logs

Each run writes its own file `logs/<timestamp>_<run>.jsonl`, one JSON object per line with the
fields `ts`, `run_id`, `event` (`user_task`, `tool_call`, `tool_result`, `final`, `error`),
`tool`, `args`, `ok`, `model` and `duration_ms`. `logs/` is not committed.
