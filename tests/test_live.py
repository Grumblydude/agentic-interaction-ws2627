"""End to end against the real model and DATA_BASE_URL, through `python -m agent`.

These cost tokens (free tier: 8,000 per minute), so they only run on request:
    AGENT_LIVE_TESTS=1 python -m pytest tests/test_live.py
"""
import os
import subprocess
import sys

import pytest
from fakes import read_log

from agent.config import REPO_ROOT
from agent.runlog import LOG_DIR

pytestmark = pytest.mark.skipif(
    os.environ.get("AGENT_LIVE_TESTS") != "1", reason="set AGENT_LIVE_TESTS=1 to call the real model"
)


def run_agent_cli(task: str):
    before = set(LOG_DIR.glob("*.jsonl"))
    process = subprocess.run(
        [sys.executable, "-m", "agent", task],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    (log_file,) = set(LOG_DIR.glob("*.jsonl")) - before
    return process, read_log(log_file)


def test_two_days_need_several_tool_calls():
    process, log = run_agent_cli("What is on 29 Oct 2026 and on 30 Oct 2026?")

    assert process.returncode == 0, process.stderr
    dates = {record["args"].get("date") for record in log if record["event"] == "tool_call"}
    assert {"2026-10-29", "2026-10-30"} <= dates
    assert log[-1]["event"] == "final"


def test_question_from_exercise_1_still_works():
    process, log = run_agent_cli("Was steht am 29.10.2026 im Kalender?")

    assert process.returncode == 0, process.stderr
    assert process.stdout.strip()
    assert log[-1]["event"] == "final"
