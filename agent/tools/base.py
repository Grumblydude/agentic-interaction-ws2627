"""What a tool is, and the toolbox that runs tools by name for the agent loop."""
from dataclasses import dataclass
from typing import Callable, Iterable

from ..data import DataError, DataSource


class ToolError(Exception):
    """An expected failure of a tool, e.g. invalid arguments. The message goes back to the model."""


# A handler gets the parsed arguments and the data source and returns a JSON-serialisable dict.
Handler = Callable[[dict, DataSource], dict]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema of the arguments, shown to the model
    handler: Handler

    def schema(self) -> dict:
        """The tool description in the format of the chat completions API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True)
class ToolOutcome:
    ok: bool
    result: dict  # goes back to the model as JSON; on failure it holds an "error" message


class Toolbox:
    """The tools of one run, together with the data source they read from."""

    def __init__(self, tools: Iterable[Tool], data: DataSource):
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name {tool.name!r}.")
            self._tools[tool.name] = tool
        self._data = data

    def schemas(self) -> list[dict]:
        return [tool.schema() for tool in self._tools.values()]

    def run(self, name: str, args: dict) -> ToolOutcome:
        """Runs one tool call. Never raises: every failure becomes an outcome the model can react to."""
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(self._tools) or "none"
            return ToolOutcome(False, {"error": f"Unknown tool {name!r}. Available tools: {available}."})
        try:
            return ToolOutcome(True, tool.handler(args, self._data))
        except (ToolError, DataError) as err:
            return ToolOutcome(False, {"error": str(err)})
        except Exception as err:  # a bug in one tool must not end the whole run
            return ToolOutcome(False, {"error": f"Tool failed unexpectedly: {type(err).__name__}: {err}"})
