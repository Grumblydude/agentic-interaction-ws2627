"""HttpDataSource, with a fake opener instead of the network."""
import io
import urllib.error

import pytest

from agent.data import DataError, HttpDataSource


class FakeOpener:
    def __init__(self, body: bytes = b"{}", error: Exception | None = None):
        self.body = body
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url, timeout):
        self.urls.append(url)
        if self.error:
            raise self.error
        return io.BytesIO(self.body)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example.test", code, "error", {}, None)


def test_joins_base_url_and_path():
    opener = FakeOpener()
    HttpDataSource("https://data.test/v1/", opener=opener).get_json("calendar/2026-10-29.json")

    assert opener.urls == ["https://data.test/v1/calendar/2026-10-29.json"]


def test_returns_parsed_json():
    source = HttpDataSource("https://data.test", opener=FakeOpener(b'{"events": []}'))

    assert source.get_json("x.json") == {"events": []}


def test_404_means_no_data():
    source = HttpDataSource("https://data.test", opener=FakeOpener(error=http_error(404)))

    assert source.get_json("x.json") is None


@pytest.mark.parametrize("error", [
    http_error(500),
    urllib.error.URLError("name resolution failed"),
    TimeoutError(),
])
def test_other_failures_raise_data_error(error):
    source = HttpDataSource("https://data.test", opener=FakeOpener(error=error))

    with pytest.raises(DataError):
        source.get_json("x.json")


def test_invalid_json_raises_data_error():
    source = HttpDataSource("https://data.test", opener=FakeOpener(b"<html>"))

    with pytest.raises(DataError):
        source.get_json("x.json")
