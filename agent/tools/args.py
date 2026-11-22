"""Argument checks shared by the tools. Invalid arguments raise ToolError, which goes back to the model."""
import re
from datetime import date

from ..data import DataSource
from .base import ToolError

# Strictly YYYY-MM-DD. date.fromisoformat alone would also accept e.g. 20261029.
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Place ids end up in the URL path, so only plain ids like "ulm" or "muenchen" are allowed.
_PLACE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def require_date(args: dict, key: str = "date") -> str:
    day = args.get(key)
    if not isinstance(day, str) or not _DATE.fullmatch(day):
        raise ToolError(f"Invalid {key} {day!r}, expected YYYY-MM-DD.")
    try:
        date.fromisoformat(day)
    except ValueError:
        raise ToolError(f"Invalid {key} {day!r}, no such day.") from None
    return day


def known_places(data: DataSource) -> dict[str, str]:
    """Place id -> display name, from the "cities" of index.json. Empty if the index has none."""
    index = data.get_json("index.json")
    cities = index.get("cities") if isinstance(index, dict) else None
    return cities if isinstance(cities, dict) else {}


def require_place(args: dict, key: str, places: dict[str, str]) -> tuple[str, bool]:
    """Returns (place id, known). Unknown means the data has nothing for this place."""
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"Missing {key}, expected a place id such as 'ulm'.")
    place = value.strip().lower()
    if places:
        return place, place in places
    if not _PLACE_ID.fullmatch(place):
        raise ToolError(f"Invalid {key} {value!r}, expected a place id such as 'ulm'.")
    return place, True


def unknown_place(place: str, places: dict[str, str]) -> dict:
    listed = ", ".join(f"{pid} ({name})" for pid, name in places.items())
    return {
        "place": place,
        "no_data": True,
        "message": (f"There is no data for the place {place!r}. Places with data: {listed}. "
                    "If one of them was meant, call again with its id; otherwise say that "
                    "there is no data for this place. Do not invent values."),
    }
