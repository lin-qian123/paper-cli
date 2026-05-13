from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import read_paper


def find_paper_dirs(library_dir: Path) -> list[Path]:
    roots = [library_dir / "inbox", library_dir / "collections"]
    paper_dirs: list[Path] = []
    for root in roots:
        if root.exists():
            paper_dirs.extend(path.parent for path in root.glob("**/paper.yaml"))
    return sorted(set(paper_dirs))


def _paper_row(library_dir: Path, bundle_dir: Path) -> dict[str, Any]:
    record = read_paper(bundle_dir)
    return {
        "id": record.id,
        "name": record.name,
        "collection": record.collection,
        "path": str(bundle_dir.relative_to(library_dir)),
        "title": record.metadata.get("title"),
        "creators": record.metadata.get("creators", []),
        "year": record.metadata.get("year"),
        "language": record.metadata.get("language"),
        "metadata_sources": record.metadata_sources,
        "metadata_confidence": record.metadata_confidence,
        "status": record.status,
    }


def rebuild_papers_index(library_dir: Path) -> None:
    index_dir = library_dir / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    rows = [_paper_row(library_dir, bundle_dir) for bundle_dir in find_paper_dirs(library_dir)]
    content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    (index_dir / "papers.jsonl").write_text(content, encoding="utf-8")


def append_job(library_dir: Path, event: dict[str, Any]) -> None:
    index_dir = library_dir / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    with (index_dir / "jobs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
