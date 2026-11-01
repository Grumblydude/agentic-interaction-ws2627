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

The answer is printed to standard output.
