"""Read access to the mock data under DATA_BASE_URL."""
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol


class DataError(Exception):
    """The data could not be fetched or read: network problem, HTTP error other than 404, bad JSON."""


class DataSource(Protocol):
    """Where tools get their data from. Tests use an in-memory fake instead of HTTP."""

    def get_json(self, path: str) -> Any | None:
        """Returns the JSON document at `path`, or None if there is no data (HTTP 404)."""
        ...


class HttpDataSource:
    """Fetches JSON documents relative to DATA_BASE_URL."""

    def __init__(self, base_url: str, timeout: float = 15, opener: Callable = urllib.request.urlopen):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._open = opener

    def get_json(self, path: str) -> Any | None:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with self._open(url, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as err:  # subclass of URLError, so it must come first
            if err.code == 404:
                return None
            raise DataError(f"HTTP {err.code} for {url}") from err
        except urllib.error.URLError as err:
            raise DataError(f"Could not reach {url}: {err.reason}") from err
        except TimeoutError as err:
            raise DataError(f"Timed out reading {url}") from err
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise DataError(f"No valid JSON at {url}") from err
