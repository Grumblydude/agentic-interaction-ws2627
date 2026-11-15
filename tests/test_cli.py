"""How a run ends, as seen from outside: exit code, stdout/stderr and the last log line."""
import pytest
from fakes import ScriptedModel, answer, calendar_calls, events, read_log

import agent.__main__ as cli
import agent.runlog
from agent.model import ModelError


def test_answer_exits_0_and_logs_final(toolbox, log, capsys):
    model = ScriptedModel(calendar_calls("2026-10-29"), answer("Standup at 9."))

    code = cli.answer_task("Was steht am 29.10.2026 im Kalender?", model, toolbox, log)

    assert code == 0
    assert capsys.readouterr().out == "Standup at 9.\n"
    assert events(log.path) == ["user_task", "tool_call", "tool_result", "final"]


def test_step_limit_exits_1_and_logs_error(toolbox, log, capsys):
    model = ScriptedModel(calendar_calls("2026-10-29"), repeat_last=True)

    code = cli.answer_task("task", model, toolbox, log, max_steps=2)

    out = capsys.readouterr()
    assert code == 1
    assert out.out == ""
    assert out.err.startswith("Error: No final answer after 2 steps.")
    last = read_log(log.path)[-1]
    assert (last["event"], last["ok"], last["fatal"], last["reason"], last["steps"]) == (
        "error", False, True, "step_limit", 2)


def test_permanent_model_error_exits_1(toolbox, log):
    model = ScriptedModel(ModelError("invalid API key", recoverable=False))

    assert cli.answer_task("task", model, toolbox, log) == 1
    assert read_log(log.path)[-1]["reason"] == "model_error"


def test_unexpected_exception_exits_1_with_logged_error(toolbox, log, capsys):
    model = ScriptedModel(RuntimeError("bug"))

    assert cli.answer_task("task", model, toolbox, log) == 1
    assert "RuntimeError: bug" in capsys.readouterr().err
    assert read_log(log.path)[-1]["reason"] == "exception"


def test_missing_configuration_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(agent.runlog, "LOG_DIR", tmp_path)

    def no_config():
        raise RuntimeError("Missing settings: OPENAI_API_KEY (see .env.example)")

    monkeypatch.setattr(cli, "load_config", no_config)

    assert cli.main(["What is on 29 Oct 2026?"]) == 1
    assert "Missing settings" in capsys.readouterr().err
    (log_file,) = tmp_path.glob("*.jsonl")
    assert read_log(log_file)[-1]["reason"] == "config"


@pytest.mark.parametrize("line", ["exit", "quit"])
def test_chat_ends_on_exit(monkeypatch, line):
    monkeypatch.setattr("builtins.input", lambda prompt: line)

    assert cli.main([]) == 0
