from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MinerUEnvironment:
    executable: str | None
    exists: bool
    version: str | None = None
    error: str | None = None


def resolve_mineru_environment(
    config: dict[str, Any] | None = None,
    *,
    cli_executable: str | None = None,
    probe: bool = False,
) -> MinerUEnvironment:
    mineru_config = (config or {}).get("mineru", {}) if isinstance(config, dict) else {}
    requested = cli_executable or mineru_config.get("executable") or "mineru"
    resolved = _resolve_executable(str(requested))
    if resolved is None:
        return MinerUEnvironment(
            executable=str(requested),
            exists=False,
            error=f"MinerU executable was not found: {requested}",
        )
    version = None
    error = None
    if probe:
        try:
            version = probe_mineru_version(resolved)
        except Exception as exc:
            error = str(exc)
    return MinerUEnvironment(executable=resolved, exists=True, version=version, error=error)


def _resolve_executable(value: str) -> str | None:
    path = Path(value).expanduser()
    if path.is_absolute() or "/" in value:
        return str(path) if path.exists() and path.is_file() else None
    return shutil.which(value)


def probe_mineru_version(executable: str, timeout: float = 10) -> str | None:
    completed = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
    if completed.returncode != 0 and not output:
        raise RuntimeError(f"MinerU version probe failed with exit code {completed.returncode}")
    match = re.search(r"(\d+(?:\.\d+)+)", output)
    return match.group(1) if match else (output or None)


def config_requests_local_mineru_check(config: dict[str, Any]) -> bool:
    mineru_config = config.get("mineru", {}) if isinstance(config, dict) else {}
    executable = mineru_config.get("executable")
    return bool(
        executable
        and (
            executable != "mineru"
            or mineru_config.get("local_backend")
            or mineru_config.get("local_jobs") not in (None, "auto")
        )
    )
