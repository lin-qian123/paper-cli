from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PaperRecord:
    id: str
    name: str
    collection: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    metadata_sources: dict[str, str] = field(default_factory=dict)
    metadata_confidence: dict[str, str] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    status: dict[str, str] = field(default_factory=dict)
    naming: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1
    name_locked: bool = False
    previous_names: list[str] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        paper_id: str,
        name: str,
        collection: str | None,
        imported_from: str,
        metadata: dict[str, Any] | None = None,
        metadata_sources: dict[str, str] | None = None,
        metadata_confidence: dict[str, str] | None = None,
    ) -> "PaperRecord":
        return cls(
            id=paper_id,
            name=name,
            collection=collection,
            metadata=metadata
            or {
                "title": None,
                "creators": [],
                "year": None,
                "language": "en",
                "doi": None,
            },
            metadata_sources=metadata_sources or {},
            metadata_confidence=metadata_confidence or {},
            source={
                "type": "local-folder",
                "imported_from": imported_from,
                "copied_pdf": "original.pdf",
                "imported_at": utc_now_iso(),
            },
            status={
                "import": "done",
                "conversion": "pending",
                "metadata": "partial",
                "naming": "fast",
            },
            naming={
                "template": "default",
                "rendered_from": ["creators", "year", "title"],
                "last_renamed_at": None,
            },
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperRecord":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            id=str(data["id"]),
            name=str(data.get("name") or ""),
            name_locked=bool(data.get("name_locked", False)),
            previous_names=list(data.get("previous_names") or []),
            collection=data.get("collection"),
            metadata=dict(data.get("metadata") or {}),
            metadata_sources=dict(data.get("metadata_sources") or {}),
            metadata_confidence=dict(data.get("metadata_confidence") or {}),
            source=dict(data.get("source") or {}),
            status=dict(data.get("status") or {}),
            naming=dict(data.get("naming") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "name_locked": self.name_locked,
            "previous_names": self.previous_names,
            "collection": self.collection,
            "metadata": self.metadata,
            "metadata_sources": self.metadata_sources,
            "metadata_confidence": self.metadata_confidence,
            "source": self.source,
            "status": self.status,
            "naming": self.naming,
        }


def write_paper(bundle_dir: Path, record: PaperRecord) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    path = bundle_dir / "paper.yaml"
    path.write_text(
        yaml.safe_dump(record.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def read_paper(bundle_dir: Path) -> PaperRecord:
    path = bundle_dir / "paper.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid paper metadata: {path}")
    return PaperRecord.from_dict(data)
