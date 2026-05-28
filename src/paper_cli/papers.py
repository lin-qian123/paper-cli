from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .indexes import find_paper_dirs
from .models import PaperRecord, read_paper


@dataclass(frozen=True)
class PaperMatch:
    bundle_dir: Path
    record: PaperRecord
    reasons: tuple[str, ...]


def paper_row(library_dir: Path, bundle_dir: Path, record: PaperRecord | None = None) -> dict:
    record = record or read_paper(bundle_dir)
    return {
        "id": record.id,
        "name": record.name,
        "collection": record.collection,
        "status": record.status,
        "path": str(bundle_dir),
        "relative_path": str(bundle_dir.relative_to(library_dir)),
    }


def resolve_papers(library_dir: Path, query: str) -> list[PaperMatch]:
    query = query.strip()
    if not query:
        return []

    bundle_dirs = find_paper_dirs(library_dir)
    path_match = _resolve_path_query(library_dir, query)
    matches: list[PaperMatch] = []
    for bundle_dir in bundle_dirs:
        record = read_paper(bundle_dir)
        reasons = _match_reasons(library_dir, bundle_dir, record, query, path_match)
        if reasons:
            matches.append(PaperMatch(bundle_dir=bundle_dir, record=record, reasons=tuple(reasons)))
    return matches


def resolve_one_paper(library_dir: Path, query: str) -> tuple[PaperMatch | None, list[PaperMatch]]:
    matches = resolve_papers(library_dir, query)
    if len(matches) == 1:
        return matches[0], matches
    return None, matches


def inspect_paper(library_dir: Path, bundle_dir: Path, record: PaperRecord | None = None) -> dict:
    record = record or read_paper(bundle_dir)
    summary_dir = bundle_dir / "extracts" / "summary"
    return {
        "paper": {
            **paper_row(library_dir, bundle_dir, record),
            "name_locked": record.name_locked,
            "previous_names": record.previous_names,
            "metadata": record.metadata,
            "metadata_sources": record.metadata_sources,
            "metadata_confidence": record.metadata_confidence,
            "source": record.source,
            "naming": record.naming,
            "schema_version": record.schema_version,
        },
        "artifacts": {
            "paper_yaml": _artifact(bundle_dir / "paper.yaml"),
            "original_pdf": _artifact(bundle_dir / "original.pdf"),
            "paper_md": _artifact(bundle_dir / "paper.md"),
            "images_dir": _artifact(bundle_dir / "images"),
            "raw_mineru_dir": _artifact(bundle_dir / "raw" / "mineru"),
            "conversion_json": _artifact(bundle_dir / "conversion.json"),
            "repair_json": _artifact(bundle_dir / "repair.json"),
            "summary_json": _artifact(summary_dir / "summary.json"),
            "summary_md": _artifact(summary_dir / "summary.md"),
            "source_map_json": _artifact(summary_dir / "source-map.json"),
        },
        "conversion": _read_json(bundle_dir / "conversion.json"),
        "repair": _read_json(bundle_dir / "repair.json"),
        "extract_summary": {
            "summary": _read_json(summary_dir / "summary.json"),
            "source_map": _read_json(summary_dir / "source-map.json"),
        },
    }


def _resolve_path_query(library_dir: Path, query: str) -> Path | None:
    candidates = [Path(query)]
    if not Path(query).is_absolute():
        candidates.append(library_dir / query)
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        bundle = _nearest_bundle_dir(resolved)
        if bundle is not None:
            return bundle
    return None


def _nearest_bundle_dir(path: Path) -> Path | None:
    current = path if path.is_dir() else path.parent
    for candidate in (current, *current.parents):
        if (candidate / "paper.yaml").exists():
            return candidate
    return None


def _match_reasons(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    query: str,
    path_match: Path | None,
) -> list[str]:
    reasons: list[str] = []
    query_casefold = query.casefold()
    if path_match is not None and path_match == bundle_dir.resolve():
        reasons.append("path")
    if record.id == query:
        reasons.append("id")
    elif record.id.startswith(query):
        reasons.append("id-prefix")
    if record.name == query:
        reasons.append("name")
    elif query_casefold in record.name.casefold():
        reasons.append("name-substring")
    relative_path = str(bundle_dir.relative_to(library_dir))
    if relative_path == query:
        reasons.append("relative-path")
    elif query_casefold in relative_path.casefold():
        reasons.append("relative-path-substring")
    title = record.metadata.get("title")
    if isinstance(title, str) and query_casefold in title.casefold():
        reasons.append("title-substring")
    return reasons


def _artifact(path: Path) -> dict[str, Any]:
    exists = path.exists()
    payload: dict[str, Any] = {
        "path": str(path),
        "exists": exists,
    }
    if exists:
        payload["type"] = "dir" if path.is_dir() else "file"
        if path.is_file():
            payload["bytes"] = path.stat().st_size
    return payload


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"error": f"invalid-json: {exc}"}
    return data if isinstance(data, dict) else {"value": data}
