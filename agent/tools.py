"""Tools the model can call, with their descriptions for the model."""
import json
import urllib.error
import urllib.request
from datetime import date

CALENDAR_TOOL = {
    "type": "function",
    "function": {
        "name": "get_calendar_day",
        "description": (
            "Returns all appointments in the user's calendar for one day: "
            "start and end time, title, location and whether it is all-day. "
            "Use it whenever a question concerns the calendar, appointments or "
            "the schedule of a specific date. An empty list means the day is free."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The day to look up, formatted as YYYY-MM-DD, e.g. 2026-10-29.",
                }
            },
            "required": ["date"],
            "additionalProperties": False,
        },
    },
}

TOOLS = [CALENDAR_TOOL]


def get_calendar_day(data_base_url: str, date_str: str) -> dict:
    """Fetches {DATA_BASE_URL}/calendar/{date}.json. HTTP 404 is a result, not a crash."""
    try:
        date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return {"error": f"Invalid date {date_str!r}, expected YYYY-MM-DD."}

    url = f"{data_base_url}/calendar/{date_str}.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return {"date": date_str, "error": "No calendar data for this day."}
        raise


def run_tool(name: str, args: dict, data_base_url: str) -> dict:
    if name == "get_calendar_day":
        return get_calendar_day(data_base_url, args.get("date"))
    return {"error": f"Unknown tool {name!r}."}
