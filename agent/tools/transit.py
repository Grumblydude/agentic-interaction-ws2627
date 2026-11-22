"""get_connections: train connections between two places on one day."""
from ..data import DataSource
from .args import known_places, require_date, require_place, unknown_place
from .base import Tool, ToolError

NO_DATA_MESSAGE = (
    "There are no connections in the data for this route and day, so they are unknown. "
    "Do not make up trains, times or prices."
)


def get_connections(args: dict, data: DataSource) -> dict:
    day = require_date(args)
    places = known_places(data)
    origin, origin_known = require_place(args, "origin", places)
    destination, destination_known = require_place(args, "destination", places)
    if not origin_known:
        return unknown_place(origin, places)
    if not destination_known:
        return unknown_place(destination, places)
    if origin == destination:
        raise ToolError("origin and destination are the same place.")

    result = data.get_json(f"transit/{origin}/{destination}/{day}.json")
    if result is None:
        return {"origin": origin, "destination": destination, "date": day,
                "no_data": True, "message": NO_DATA_MESSAGE}
    return result


CONNECTIONS_TOOL = Tool(
    name="get_connections",
    description=(
        "Returns the train connections from one place to another on one day: departure, "
        "arrival, train, number of changes and price in EUR. Use it for questions about "
        "how to travel between places."
    ),
    parameters={
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Place id to start from, e.g. ulm."},
            "destination": {"type": "string", "description": "Place id to travel to."},
            "date": {"type": "string", "description": "The day, formatted as YYYY-MM-DD."},
        },
        "required": ["origin", "destination", "date"],
        "additionalProperties": False,
    },
    handler=get_connections,
)
