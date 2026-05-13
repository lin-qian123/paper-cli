from __future__ import annotations

import shutil
from pathlib import Path

from .base import ConversionResult


class LocalFixtureConverter:
    name = "local-fixture"

    def __init__(self, fixture_dir: Path):
        self.fixture_dir = fixture_dir

    def convert(self, source_pdf: Path, output_dir: Path) -> ConversionResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        fixture_markdown = self.fixture_dir / "paper.md"
        if not fixture_markdown.exists():
            return ConversionResult(ok=False, error=f"Missing fixture markdown: {fixture_markdown}")
        markdown_path = output_dir / "paper.md"
        shutil.copy2(fixture_markdown, markdown_path)

        fixture_images = self.fixture_dir / "images"
        images_dir = output_dir / "images"
        if images_dir.exists():
            shutil.rmtree(images_dir)
        if fixture_images.exists():
            shutil.copytree(fixture_images, images_dir)
        else:
            images_dir.mkdir(parents=True, exist_ok=True)

        return ConversionResult(ok=True, markdown_path=markdown_path, images_dir=images_dir)
