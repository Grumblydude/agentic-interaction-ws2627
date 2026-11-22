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


def run_chat(monkeypatch, tmp_path, lines, model, toolbox) -> int:
    """Runs the chat with the given input lines and a fake model instead of the configuration."""
    monkeypatch.setattr(agent.runlog, "LOG_DIR", tmp_path)
    monkeypatch.setattr(cli, "_connect", lambda log: (model, toolbox, ""))
    answers = iter(lines)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    return cli.main([])


def test_chat_keeps_the_conversation_in_one_log(monkeypatch, tmp_path, toolbox, capsys):
    model = ScriptedModel(calendar_calls("2026-10-29"), answer("Standup at 9."), answer("Only that."))

    code = run_chat(monkeypatch, tmp_path, ["What is on 29 Oct?", "Anything else?", "exit"],
                    model, toolbox)

    assert code == 0
    assert "Standup at 9." in [m["content"] for m in model.requests[-1]]
    (log_file,) = tmp_path.glob("*.jsonl")
    assert events(log_file).count("user_task") == 2
    assert len({record["run_id"] for record in read_log(log_file)}) == 1
    assert "Only that." in capsys.readouterr().out


def test_chat_new_starts_a_fresh_conversation(monkeypatch, tmp_path, toolbox):
    model = ScriptedModel(answer("first"), answer("second"))

    run_chat(monkeypatch, tmp_path, ["one", "new", "two", "exit"], model, toolbox)

    assert [m["content"] for m in model.requests[-1]][1:] == ["two"]


def test_chat_forgets_a_failed_question_and_goes_on(monkeypatch, tmp_path, toolbox):
    model = ScriptedModel(ModelError("invalid API key", recoverable=False), answer("ok"))

    code = run_chat(monkeypatch, tmp_path, ["broken", "works", "exit"], model, toolbox)

    assert code == 0
    assert [m["content"] for m in model.requests[-1]][1:] == ["works"]
    (log_file,) = tmp_path.glob("*.jsonl")
    assert events(log_file) == ["user_task", "error", "user_task", "final"]
