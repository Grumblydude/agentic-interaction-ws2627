"""Background facts for the system prompt, read from the data at startup, not written into the code."""
from .data import DataError, DataSource


def describe_data(data: DataSource) -> str:
    """Places with data (from index.json) and the user's home (from context.json).

    Returns "" for whatever cannot be loaded: the tools still work, the model just knows less.
    """
    lines = []

    index = _load(data, "index.json")
    cities = index.get("cities")
    if isinstance(cities, dict) and cities:
        listed = ", ".join(f"{pid} = {name}" for pid, name in cities.items())
        lines.append(f"Places with weather and train data (use these ids in tool calls): {listed}. "
                     "There is no such data for any other place.")

    home = _load(data, "context.json").get("home")
    if isinstance(home, str) and home:
        lines.append(f"The user lives in {home}; trips start there unless the user says otherwise.")

    return "\n".join(lines)


def _load(data: DataSource, path: str) -> dict:
    try:
        document = data.get_json(path)
    except DataError:
        return {}
    return document if isinstance(document, dict) else {}
