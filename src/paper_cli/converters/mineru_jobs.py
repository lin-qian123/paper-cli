from __future__ import annotations

from typing import Any


def resolve_local_jobs(
    config: dict[str, Any] | None,
    *,
    cli_jobs: int | None,
    pending_count: int,
) -> int:
    upper = max(1, int(pending_count or 1))
    if cli_jobs is not None:
        return _bounded(cli_jobs, upper)

    mineru_config = (config or {}).get("mineru", {}) if isinstance(config, dict) else {}
    configured = mineru_config.get("local_jobs", "auto")
    if isinstance(configured, int):
        return _bounded(configured, upper)
    if isinstance(configured, str) and configured.isdigit():
        return _bounded(int(configured), upper)
    return 1


def _bounded(value: int, upper: int) -> int:
    return max(1, min(int(value), upper))
