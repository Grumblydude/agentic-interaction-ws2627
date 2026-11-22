"""get_weather: the weather forecast for one place and day."""
from ..data import DataSource
from .args import known_places, require_date, require_place, unknown_place
from .base import Tool

NO_DATA_MESSAGE = (
    "There is no weather data for this place and day, so the weather is unknown. "
    "Do not guess or invent weather values."
)


def get_weather(args: dict, data: DataSource) -> dict:
    day = require_date(args)
    places = known_places(data)
    city, known = require_place(args, "city", places)
    if not known:
        return unknown_place(city, places)

    result = data.get_json(f"weather/{city}/{day}.json")
    if result is None:
        return {"city": city, "date": day, "no_data": True, "message": NO_DATA_MESSAGE}
    return result


WEATHER_TOOL = Tool(
    name="get_weather",
    description=(
        "Returns the weather forecast for one place and day: condition, temperature in °C, "
        "rain probability (0 to 1) and wind in km/h. Use it for questions about weather, rain, "
        "or what to wear or take along."
    ),
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "Place id, e.g. ulm."},
            "date": {"type": "string", "description": "The day, formatted as YYYY-MM-DD."},
        },
        "required": ["city", "date"],
        "additionalProperties": False,
    },
    handler=get_weather,
)
