"""Settings from the environment, with .env as fallback."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ("OPENAI_BASE_URL", "MODEL", "OPENAI_API_KEY", "DATA_BASE_URL")


@dataclass(frozen=True)
class Config:
    openai_base_url: str
    model: str
    openai_api_key: str
    data_base_url: str


def load_config() -> Config:
    # override=False: variables already set in the environment win over .env.
    load_dotenv(REPO_ROOT / ".env", override=False)
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)} (see .env.example)")
    return Config(
        openai_base_url=os.environ["OPENAI_BASE_URL"],
        model=os.environ["MODEL"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        data_base_url=os.environ["DATA_BASE_URL"].rstrip("/"),
    )
