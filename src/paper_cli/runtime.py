from __future__ import annotations

import sys
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .indexes import append_run_event
from .models import utc_now_iso

RuntimeEventSink = Callable[[str, dict[str, Any]], None]


class RuntimeReporter:
    """Persist compact non-secret run events and mirror them to stderr."""

    def __init__(self, library_dir: Path, command: str, *, persist: bool = True):
        self.library_dir = library_dir
        self.command = command
        self.persist = persist
        self.run_id = f"run:{uuid.uuid4()}"
        self.started_at = time.monotonic()
        self._lock = threading.Lock()

    def emit(self, event: str, details: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "at": utc_now_iso(),
            "run_id": self.run_id,
            "command": self.command,
            "elapsed_seconds": round(time.monotonic() - self.started_at, 3),
        }
        if details:
            payload.update(details)
        with self._lock:
            if self.persist:
                append_run_event(self.library_dir, payload)
            readable = [
                f"paper[{self.command}]",
                event,
                f"run={self.run_id}",
                f"elapsed={payload['elapsed_seconds']:.1f}s",
            ]
            for key in ("path", "stage", "count", "error", "reason"):
                value = payload.get(key)
                if value not in (None, ""):
                    readable.append(f"{key}={value}")
            print(" ".join(readable), file=sys.stderr, flush=True)

    def started(self, details: dict[str, Any] | None = None) -> None:
        self.emit("run-started", details)

    def finished(self, *, ok: bool, details: dict[str, Any] | None = None) -> None:
        payload = {"ok": ok}
        if details:
            payload.update(details)
        self.emit("run-finished", payload)
