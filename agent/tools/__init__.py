"""The tools the agent offers the model.

To add a tool: write its handler and `Tool` in a module of its own (see calendar.py) and add it
to ALL_TOOLS. The loop needs no change.
"""
from .base import Tool, Toolbox, ToolError, ToolOutcome
from .calendar import CALENDAR_TOOL
from .transit import CONNECTIONS_TOOL
from .weather import WEATHER_TOOL

ALL_TOOLS: tuple[Tool, ...] = (CALENDAR_TOOL, WEATHER_TOOL, CONNECTIONS_TOOL)

__all__ = ["ALL_TOOLS", "Tool", "Toolbox", "ToolError", "ToolOutcome"]
