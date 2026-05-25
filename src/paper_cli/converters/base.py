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


@dataclass
class BatchConversionItem:
    bundle_dir: Path
    source_pdf: Path
    output_dir: Path
    paper_id: str
    attempt: int
    submitted_at: str


@dataclass
class BatchConversionResult:
    bundle_dir: Path
    ok: bool
    markdown_path: Path | None = None
    images_dir: Path | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict)
    batch_id: str | None = None
    data_id: str | None = None
    remote_state: str | None = None


class Converter(Protocol):
    name: str

    def convert(self, source_pdf: Path, output_dir: Path) -> ConversionResult:
        raise NotImplementedError


class BatchConverter(Protocol):
    name: str

    def convert_batch(
        self,
        items: list[BatchConversionItem],
        output_dir: Path,
        *,
        jobs: int = 1,
    ) -> list[BatchConversionResult]:
        raise NotImplementedError
