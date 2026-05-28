from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .config import load_config
from .converters.mineru_env import (
    config_requests_local_mineru_check,
    resolve_mineru_environment,
)
from .indexes import find_paper_dirs
from .metadata import valid_creators
from .models import read_paper


@dataclass
class Issue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _strict_conversion_issues(library_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        state = record.status.get("conversion")
        if state == "failed":
            issues.append(Issue("failed-conversion", str(bundle_dir), "Conversion failed"))
        elif state != "done":
            issues.append(Issue("pending-conversion", str(bundle_dir), "Conversion is not done"))
        issues.extend(_strict_conversion_file_issues(bundle_dir))

    jobs_path = library_dir / "indexes" / "jobs.jsonl"
    if not jobs_path.exists():
        return issues
    started: list[dict] = []
    finished_keys: set[tuple[str, int]] = set()
    for line_number, line in enumerate(jobs_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(Issue("invalid-job-json", f"{jobs_path}:{line_number}", str(exc)))
            continue
        key = (str(event.get("paper_id") or ""), int(event.get("attempt") or 0))
        if event.get("event") == "conversion-started":
            started.append(event)
        elif event.get("event") == "conversion-finished":
            finished_keys.add(key)
    for event in started:
        key = (str(event.get("paper_id") or ""), int(event.get("attempt") or 0))
        if key not in finished_keys:
            issues.append(
                Issue(
                    "dangling-conversion-job",
                    str(jobs_path),
                    (
                        f"Started conversion has no matching finish event: "
                        f"{event.get('paper_id')} attempt {event.get('attempt')}"
                    ),
                )
            )
    return issues


def _strict_conversion_file_issues(bundle_dir: Path) -> list[Issue]:
    path = bundle_dir / "conversion.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Issue("invalid-conversion-json", str(path), str(exc))]
    if payload.get("state") != "running":
        return []

    issues: list[Issue] = []
    if payload.get("converter") == "mineru-api-batch" and (
        not payload.get("batch_id") or not payload.get("data_id")
    ):
        issues.append(
            Issue(
                "missing-batch-conversion-mapping",
                str(path),
                "Running MinerU batch conversion is missing batch_id or data_id",
            )
        )

    submitted_at = payload.get("submitted_at")
    if submitted_at:
        try:
            submitted = datetime.fromisoformat(str(submitted_at).replace("Z", "+00:00"))
            if submitted.tzinfo is None:
                submitted = submitted.replace(tzinfo=UTC)
            max_wait = float(os.environ.get("MINERU_MAX_WAIT_SECONDS", 30 * 60))
            if (datetime.now(UTC) - submitted).total_seconds() > max_wait:
                issues.append(
                    Issue(
                        "stale-running-conversion",
                        str(path),
                        f"Running conversion is older than {max_wait:g} seconds",
                    )
                )
        except ValueError:
            issues.append(
                Issue("invalid-conversion-timestamp", str(path), "submitted_at is invalid")
            )
    return issues


def run_doctor(library_dir: Path, *, strict: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not (library_dir / "paper-cli.yaml").exists():
        issues.append(
            Issue(
                "missing-library-config",
                str(library_dir / "paper-cli.yaml"),
                "Missing paper-cli.yaml; run paper init for this library",
            )
        )
    seen_ids: dict[str, Path] = {}
    for bundle_dir in find_paper_dirs(library_dir):
        metadata_path = bundle_dir / "paper.yaml"
        try:
            yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
            record = read_paper(bundle_dir)
        except Exception as exc:
            issues.append(Issue("invalid-paper-yaml", str(metadata_path), str(exc)))
            continue

        if record.id in seen_ids:
            issues.append(
                Issue(
                    "duplicate-id", str(bundle_dir), f"Duplicate id also in {seen_ids[record.id]}"
                )
            )
        else:
            seen_ids[record.id] = bundle_dir

        creators = record.metadata.get("creators", [])
        if not valid_creators(creators):
            issues.append(
                Issue(
                    "invalid-creators",
                    str(metadata_path),
                    "metadata.creators must be a list of objects with non-empty name",
                )
            )

        if not (bundle_dir / "original.pdf").exists():
            issues.append(Issue("missing-original-pdf", str(bundle_dir), "Missing original.pdf"))
        if record.status.get("conversion") == "done" and not (bundle_dir / "paper.md").exists():
            issues.append(
                Issue(
                    "missing-paper-md",
                    str(bundle_dir),
                    "Conversion is done but paper.md is missing",
                )
            )

    index_path = library_dir / "indexes" / "papers.jsonl"
    if index_path.exists():
        indexed_count = len(
            [line for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        )
        actual_count = len(find_paper_dirs(library_dir))
        if indexed_count != actual_count:
            issues.append(
                Issue(
                    "stale-index",
                    str(index_path),
                    f"Index has {indexed_count}, actual {actual_count}",
                )
            )
    if strict:
        issues.extend(_strict_mineru_environment_issues(library_dir))
        issues.extend(_strict_conversion_issues(library_dir))
    return issues


def doctor_diagnostics(library_dir: Path, *, strict: bool = False) -> dict:
    config_path = library_dir / "paper-cli.yaml"
    diagnostics = {
        "library": {
            "path": str(library_dir),
            "config_path": str(config_path),
            "config_exists": config_path.exists(),
            "inbox_exists": (library_dir / "inbox").is_dir(),
            "collections_exists": (library_dir / "collections").is_dir(),
            "indexes_exists": (library_dir / "indexes").is_dir(),
        },
        "mineru": {
            "api_key_env": "MINERU_API_KEY",
            "api_key_available": bool(os.environ.get("MINERU_API_KEY")),
        },
        "ai": _ai_diagnostics(library_dir),
    }
    try:
        config = load_config(library_dir)
    except Exception as exc:
        diagnostics["config_error"] = str(exc)
        return diagnostics

    mineru_config = dict(config.get("mineru") or {})
    diagnostics["mineru"].update(
        {
            "configured_executable": str(mineru_config.get("executable") or "mineru"),
            "configured_local_backend": mineru_config.get("local_backend"),
            "configured_local_jobs": mineru_config.get("local_jobs"),
            "configured_max_wait_seconds": mineru_config.get("max_wait_seconds"),
        }
    )
    if config_requests_local_mineru_check(config) or strict:
        environment = resolve_mineru_environment(config, probe=strict)
        diagnostics["mineru"].update(
            {
                "local_executable": environment.executable,
                "local_executable_exists": environment.exists,
                "local_version": environment.version,
                "local_error": environment.error,
            }
        )
    return diagnostics


def _ai_diagnostics(library_dir: Path) -> dict:
    try:
        config = load_config(library_dir).get("ai", {})
    except Exception:
        config = {}
    api_key_env = str(config.get("api_key_env") or "PAPER_AI_API_KEY")
    base_url = os.environ.get("PAPER_AI_BASE_URL") or config.get("base_url")
    model = os.environ.get("PAPER_AI_MODEL") or config.get("model")
    return {
        "provider": config.get("provider", "openai-compatible"),
        "api_key_env": api_key_env,
        "api_key_available": bool(os.environ.get(api_key_env) or os.environ.get("PAPER_AI_API_KEY")),
        "base_url_configured": bool(base_url),
        "model_configured": bool(model),
    }


def _strict_mineru_environment_issues(library_dir: Path) -> list[Issue]:
    try:
        config = load_config(library_dir)
    except Exception:
        return []
    if not config_requests_local_mineru_check(config):
        return []
    environment = resolve_mineru_environment(config, probe=True)
    if not environment.exists:
        return [
            Issue(
                "missing-mineru-local-executable",
                str(library_dir / "paper-cli.yaml"),
                environment.error or "MinerU executable was not found",
            )
        ]
    if environment.error:
        return [
            Issue(
                "invalid-mineru-local-executable",
                environment.executable or "",
                environment.error,
            )
        ]
    return []


def library_status(library_dir: Path) -> dict[str, int]:
    total = 0
    converted = 0
    failed = 0
    pending = 0
    incomplete_metadata = 0
    renamed = 0
    for bundle_dir in find_paper_dirs(library_dir):
        total += 1
        record = read_paper(bundle_dir)
        state = record.status.get("conversion")
        if state == "done":
            converted += 1
        elif state == "failed":
            failed += 1
        else:
            pending += 1
        if record.status.get("metadata") != "complete":
            incomplete_metadata += 1
        if record.previous_names:
            renamed += 1
    return {
        "total": total,
        "converted": converted,
        "failed": failed,
        "pending": pending,
        "incomplete_metadata": incomplete_metadata,
        "renamed": renamed,
    }
