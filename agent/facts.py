"""Background facts for the system prompt, read from the data at startup, not written into the code."""
from datetime import date, datetime

from .data import DataError, DataSource


def describe_data(data: DataSource) -> str:
    """The current time and home (from context.json), the period and places with data (index.json).

    Returns "" for whatever cannot be loaded: the tools still work, the model just knows less.
    """
    lines = []
    index = _load(data, "index.json")
    context = _load(data, "context.json")

    # The mock data has its own "now". Without it, the model takes "today" from its own clock,
    # which lies outside the data, so every question about today or tomorrow found nothing.
    now = _parse(context.get("now"), datetime.fromisoformat)
    if now:
        lines.append(f"It is now {now:%A, %d %B %Y, %H:%M} ({now:%Y-%m-%d}). Use this for today, "
                     "tomorrow, weekdays and other relative dates, not your own clock. "
                     "Times before now have already passed: do not offer trains that have left.")

    days = index.get("days") if isinstance(index.get("days"), dict) else {}
    first = _parse(days.get("first"), date.fromisoformat)
    last = _parse(days.get("last"), date.fromisoformat)
    if first and last:
        lines.append(f"The data covers {first:%Y-%m-%d} to {last:%Y-%m-%d}. Weather and trains "
                     "exist only for some of these days: look them up, do not assume either way.")

    cities = index.get("cities")
    if isinstance(cities, dict) and cities:
        listed = ", ".join(f"{pid} = {name}" for pid, name in cities.items())
        lines.append(f"Places with weather and train data (use these ids in tool calls): {listed}. "
                     "There is no such data for any other place.")

    home = context.get("home")
    if isinstance(home, str) and home:
        lines.append(f"The user lives in {home}; trips start there unless the user says otherwise.")

    return "\n".join(lines)


def _load(data: DataSource, path: str) -> dict:
    try:
        document = data.get_json(path)
    except DataError:
        return {}
    return document if isinstance(document, dict) else {}


def _parse(value, parser):
    """The parsed date or time, or None if the value is missing or malformed."""
    if not isinstance(value, str):
        return None
    try:
        return parser(value)
    except ValueError:
        return None
