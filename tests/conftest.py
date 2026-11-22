import pytest
from fakes import CONNECTIONS_ULM_MUC_29, CONTEXT, DAY_29, DAY_30, INDEX, WEATHER_MUC_29, FakeData

from agent.runlog import RunLog
from agent.tools import ALL_TOOLS, Toolbox


@pytest.fixture
def log(tmp_path):
    return RunLog(model="fake-model", log_dir=tmp_path)


@pytest.fixture
def data():
    return FakeData({
        "calendar/2026-10-29.json": DAY_29,
        "calendar/2026-10-30.json": DAY_30,
        "index.json": INDEX,
        "context.json": CONTEXT,
        "weather/muenchen/2026-10-29.json": WEATHER_MUC_29,
        "transit/ulm/muenchen/2026-10-29.json": CONNECTIONS_ULM_MUC_29,
    })


@pytest.fixture
def toolbox(data):
    return Toolbox(ALL_TOOLS, data)
