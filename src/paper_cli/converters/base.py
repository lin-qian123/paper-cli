from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ConversionResult:
    ok: bool
    markdown_path: Path | None = None
    images_dir: Path | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict)


class Converter(Protocol):
    name: str

    def convert(self, source_pdf: Path, output_dir: Path) -> ConversionResult:
        raise NotImplementedError
