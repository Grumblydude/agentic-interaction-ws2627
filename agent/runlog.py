"""One JSONL log file per run, in logs/ inside the repository."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import REPO_ROOT

LOG_DIR = REPO_ROOT / "logs"


class RunLog:
    def __init__(self, model: str | None = None, log_dir: Path | None = None):
        self.run_id = uuid.uuid4().hex
        self.model = model
        log_dir = log_dir or LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = log_dir / f"{stamp}_{self.run_id[:8]}.jsonl"

    def write(self, event: str, *, tool=None, args=None, ok=True, duration_ms=None, **extra):
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "run_id": self.run_id,
            "event": event,
            "tool": tool,
            "args": args,
            "ok": ok,
            "model": self.model,
            "duration_ms": duration_ms,
            **extra,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
