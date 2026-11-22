"""get_calendar_day: all appointments of one day."""
from ..data import DataSource
from .args import require_date
from .base import Tool


def get_calendar_day(args: dict, data: DataSource) -> dict:
    day = require_date(args)
    result = data.get_json(f"calendar/{day}.json")
    if result is None:
        return {"date": day, "no_data": True, "message": NO_DATA_MESSAGE}
    return result


# "No data" means unknown, not free: the model has to tell those apart in its answer.
NO_DATA_MESSAGE = (
    "The calendar has no data for this day, so it is unknown whether there are appointments. "
    "Do not say the day is free."
)


CALENDAR_TOOL = Tool(
    name="get_calendar_day",
    description=(
        "Returns all appointments in the user's calendar for one day: "
        "start and end time, title, location and whether it is all-day. "
        "Use it whenever a question concerns the calendar, appointments or "
        "the schedule of a specific date. An empty list means the day is free."
    ),
    parameters={
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
    handler=get_calendar_day,
)
