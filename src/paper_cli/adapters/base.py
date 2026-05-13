from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ImportResult:
    imported: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


class SourceAdapter(Protocol):
    name: str

    def import_source(
        self,
        library_dir: Path,
        input_path: Path,
        *,
        collection: str | None,
        inbox: bool,
    ) -> ImportResult:
        raise NotImplementedError
