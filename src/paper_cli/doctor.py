from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

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


def run_doctor(library_dir: Path, *, strict: bool = False) -> list[Issue]:
    issues: list[Issue] = []
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
        issues.extend(_strict_conversion_issues(library_dir))
    return issues


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
