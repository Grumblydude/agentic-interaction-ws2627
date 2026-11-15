"""OpenAIChatModel: mapping SDK replies and classifying SDK errors, with a fake client."""
from types import SimpleNamespace

import openai
import pytest

try:  # openai 3.x is built on httpx2, older versions on httpx
    import httpx2 as httpx
except ImportError:
    import httpx

from agent.model import ModelError, ModelReply, OpenAIChatModel, ToolCall

REQUEST = httpx.Request("POST", "https://api.test/v1/chat/completions")


class FakeClient:
    def __init__(self, response=None, error=None):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def sdk_response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def sdk_tool_call(call_id, name, arguments):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def make_model(client) -> OpenAIChatModel:
    return OpenAIChatModel(base_url="https://api.test/v1", api_key="test", model="m", client=client)


def status_error(cls, code):
    return cls("failed", response=httpx.Response(code, request=REQUEST), body=None)


def test_maps_answer():
    reply = make_model(FakeClient(sdk_response(content="  Hello \n"))).complete([], [])

    assert reply == ModelReply(content="Hello")


def test_maps_tool_calls():
    response = sdk_response(tool_calls=[sdk_tool_call("c1", "get_calendar_day", '{"date": "2026-10-29"}')])

    reply = make_model(FakeClient(response)).complete([], [])

    assert reply.content == ""
    assert reply.tool_calls == (ToolCall("c1", "get_calendar_day", '{"date": "2026-10-29"}'),)


def test_sends_model_name_and_tools():
    client = FakeClient(sdk_response(content="x"))
    make_model(client).complete([{"role": "user", "content": "hi"}], [{"type": "function"}])

    assert client.calls[0]["model"] == "m"
    assert client.calls[0]["tools"] == [{"type": "function"}]


@pytest.mark.parametrize("error", [
    status_error(openai.AuthenticationError, 401),
    status_error(openai.PermissionDeniedError, 403),
    status_error(openai.NotFoundError, 404),
])
def test_permanent_errors_are_not_recoverable(error):
    with pytest.raises(ModelError) as caught:
        make_model(FakeClient(error=error)).complete([], [])

    assert caught.value.recoverable is False


@pytest.mark.parametrize("error", [
    status_error(openai.BadRequestError, 400),  # e.g. Groq "tool_use_failed"
    status_error(openai.RateLimitError, 429),
    status_error(openai.InternalServerError, 500),
    openai.APIConnectionError(request=REQUEST),
    openai.APITimeoutError(request=REQUEST),
])
def test_temporary_errors_are_recoverable(error):
    with pytest.raises(ModelError) as caught:
        make_model(FakeClient(error=error)).complete([], [])

    assert caught.value.recoverable is True


def test_no_choices_is_recoverable():
    with pytest.raises(ModelError) as caught:
        make_model(FakeClient(SimpleNamespace(choices=[]))).complete([], [])

    assert caught.value.recoverable is True


def test_reply_as_history_message():
    reply = ModelReply(tool_calls=(ToolCall("c1", "get_calendar_day", '{"date": "2026-10-29"}'),))

    assert reply.as_message() == {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "get_calendar_day", "arguments": '{"date": "2026-10-29"}'}}],
    }
