from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def discover_pdfs(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() == ".pdf" else []
    if not path.exists():
        raise FileNotFoundError(path)
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def collection_root(library_dir: Path, collection: str | None, inbox: bool) -> Path:
    if inbox or not collection:
        return library_dir / "inbox"
    clean_parts = [part for part in collection.split("/") if part and part not in {".", ".."}]
    return library_dir / "collections" / Path(*clean_parts)
