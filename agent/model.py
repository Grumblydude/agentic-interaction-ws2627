"""The language model behind the agent, reduced to what the loop needs."""
from dataclasses import dataclass
from typing import Protocol

import openai


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text exactly as the model produced it, possibly malformed


@dataclass(frozen=True)
class ModelReply:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()

    def as_message(self) -> dict:
        """The reply as an assistant message for the conversation history."""
        message: dict = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {"id": call.id, "type": "function",
                 "function": {"name": call.name, "arguments": call.arguments}}
                for call in self.tool_calls
            ]
        return message


class ModelError(Exception):
    """A model call failed. `recoverable` says whether asking again can help."""

    def __init__(self, message: str, *, recoverable: bool):
        super().__init__(message)
        self.recoverable = recoverable


class ChatModel(Protocol):
    name: str

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


# These do not go away by asking again: wrong key, no access, unknown model.
_PERMANENT_ERRORS = (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError)


class OpenAIChatModel:
    """Any OpenAI-compatible chat completions endpoint, e.g. Groq."""

    def __init__(self, *, base_url: str, api_key: str, model: str, client=None):
        self.name = model
        # Only gzip: an outdated brotli package in the environment (e.g. conda base) breaks decoding.
        # The SDK itself retries rate limits (429), server errors and connection errors with backoff.
        self._client = client or openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"Accept-Encoding": "gzip, deflate"},
            max_retries=3,
        )

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelReply:
        try:
            response = self._client.chat.completions.create(
                model=self.name, messages=messages, tools=tools, tool_choice="auto"
            )
        except _PERMANENT_ERRORS as err:
            raise ModelError(f"Model call failed: {err}", recoverable=False) from err
        except openai.APIError as err:
            # e.g. Groq's 400 "tool_use_failed" when the model writes a broken tool call
            raise ModelError(f"Model call failed: {err}", recoverable=True) from err

        if not response.choices:
            raise ModelError("Model returned no choices.", recoverable=True)
        message = response.choices[0].message
        calls = tuple(
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments or "")
            for call in message.tool_calls or ()
        )
        return ModelReply(content=(message.content or "").strip(), tool_calls=calls)
