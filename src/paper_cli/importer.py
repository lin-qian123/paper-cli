from __future__ import annotations

from pathlib import Path

from .adapters.local_folder import LocalFolderAdapter
from .config import load_config
from .fs import collection_root, copy_file, sha256_file
from .indexes import rebuild_papers_index
from .metadata import fast_metadata_details
from .models import PaperRecord, read_paper, write_paper
from .naming import render_name, resolve_duplicate_name, sanitize_name_from_config


def paper_id_for_file(path: Path) -> str:
    return f"sha256:{sha256_file(path)}"


def existing_paper_ids(library_dir: Path) -> set[str]:
    ids: set[str] = set()
    for metadata_path in library_dir.glob("**/paper.yaml"):
        try:
            ids.add(read_paper(metadata_path.parent).id)
        except Exception:
            continue
    return ids


def _existing_names(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {p.name for p in root.iterdir() if p.is_dir()}


def import_pdf(
    library_dir: Path, pdf_path: Path, collection: str | None, inbox: bool = False
) -> Path | None:
    pdf_path = pdf_path.resolve()
    paper_id = paper_id_for_file(pdf_path)
    if paper_id in existing_paper_ids(library_dir):
        return None

    config = load_config(library_dir)
    metadata, metadata_sources, metadata_confidence = fast_metadata_details(pdf_path)
    template = config.get("naming", {}).get("template", "")
    name = sanitize_name_from_config(
        render_name(template, metadata) or pdf_path.stem,
        config,
    )

    root = collection_root(library_dir, collection, inbox)
    root.mkdir(parents=True, exist_ok=True)
    final_name = resolve_duplicate_name(name, _existing_names(root))
    bundle_dir = root / final_name
    bundle_dir.mkdir(parents=True, exist_ok=False)

    copy_file(pdf_path, bundle_dir / "original.pdf")
    notes_dir = bundle_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "README.md").write_text("# Notes\n\n", encoding="utf-8")

    record = PaperRecord.new(
        paper_id=paper_id,
        name=final_name,
        collection=None if inbox else collection,
        imported_from=str(pdf_path),
        metadata=metadata,
        metadata_sources=metadata_sources,
        metadata_confidence=metadata_confidence,
    )
    write_paper(bundle_dir, record)
    return bundle_dir


def import_path(
    library_dir: Path, input_path: Path, collection: str | None, inbox: bool = False
) -> list[Path]:
    result = LocalFolderAdapter().import_source(
        library_dir,
        input_path,
        collection=collection,
        inbox=inbox,
    )
    rebuild_papers_index(library_dir)
    return result.imported
