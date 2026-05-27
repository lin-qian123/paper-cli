from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NormalizedMinerUOutput:
    markdown_path: Path
    images_dir: Path
    raw_dir: Path


def normalize_mineru_zip(content: bytes, bundle_dir: Path) -> NormalizedMinerUOutput:
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            archive.extractall(tmp_dir)
        return normalize_mineru_directory(tmp_dir, bundle_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def normalize_mineru_directory(source_dir: Path, bundle_dir: Path) -> NormalizedMinerUOutput:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    markdown_files = sorted(source_dir.glob("**/*.md"))
    if not markdown_files:
        raise ValueError("MinerU output did not contain Markdown")

    markdown_path = bundle_dir / "paper.md"
    shutil.copy2(markdown_files[0], markdown_path)

    images_dir = bundle_dir / "images"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    source_images = [
        path for path in source_dir.glob("**/images") if path.is_dir() and any(path.iterdir())
    ]
    if source_images:
        shutil.copytree(source_images[0], images_dir)
    else:
        images_dir.mkdir(parents=True, exist_ok=True)

    raw_dir = bundle_dir / "raw" / "mineru"
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_dir.glob("**/*")):
        if path.is_dir() or path == markdown_files[0]:
            continue
        relative = path.relative_to(source_dir)
        if "images" in relative.parts:
            continue
        target = raw_dir / path.name
        if target.exists():
            target = raw_dir / "_".join(relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    return NormalizedMinerUOutput(
        markdown_path=markdown_path,
        images_dir=images_dir,
        raw_dir=raw_dir,
    )
