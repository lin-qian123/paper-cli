from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .config import load_config
from .converters.base import Converter
from .indexes import find_paper_dirs, rebuild_papers_index
from .metadata import detect_language
from .models import PaperRecord, read_paper, utc_now_iso, write_paper
from .naming import render_name, resolve_duplicate_name, sanitize_name


def extract_metadata_from_markdown(markdown: str) -> dict:
    title = None
    creator = None
    year = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if title is None and stripped.startswith("# "):
            title = stripped[2:].strip()
        elif stripped.lower().startswith("authors:"):
            creator = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("year:"):
            value = stripped.split(":", 1)[1].strip()
            match = re.search(r"\d{4}", value)
            if match:
                year = int(match.group(0))
    metadata: dict = {}
    if title:
        metadata["title"] = title
    if creator:
        metadata["creators"] = [{"name": creator, "role": "author"}]
    if year:
        metadata["year"] = year
    if title or creator:
        metadata["language"] = detect_language(f"{title or ''} {creator or ''}")
    return metadata


def _normalize_title_for_match(value: str) -> str:
    value = re.sub(r"[\u2010-\u2015\u2212]", "-", value)
    return " ".join(value.split())


def infer_creator_from_title_prefix(
    previous_title: str | None, converted_title: str | None
) -> str | None:
    if not previous_title or not converted_title:
        return None
    previous = _normalize_title_for_match(previous_title)
    converted = _normalize_title_for_match(converted_title)
    if previous == converted or not previous.endswith(converted):
        return None
    prefix = previous[: -len(converted)].strip()
    prefix = re.sub(r"[-:：|丨]+$", "", prefix).strip()
    if not prefix or len(prefix) > 80:
        return None
    if re.search(r"\d", prefix):
        return None
    return prefix


def _merge_metadata(existing: dict, update: dict) -> dict:
    merged = dict(existing)
    inferred_creator = infer_creator_from_title_prefix(
        str(existing.get("title") or ""),
        str(update.get("title") or ""),
    )
    for key, value in update.items():
        if value not in (None, "", []):
            merged[key] = value
    if inferred_creator and not update.get("creators"):
        merged["creators"] = [{"name": inferred_creator, "role": "author"}]
    return merged


def maybe_rename_bundle(library_dir: Path, bundle_dir: Path, record: PaperRecord) -> Path:
    if record.name_locked:
        record.status["naming"] = "review"
        write_paper(bundle_dir, record)
        return bundle_dir

    config = load_config(library_dir)
    template = config.get("naming", {}).get("template", "")
    rendered = sanitize_name(render_name(template, record.metadata) or record.name)
    if rendered == bundle_dir.name:
        record.name = rendered
        write_paper(bundle_dir, record)
        return bundle_dir

    target = bundle_dir.parent / resolve_duplicate_name(
        rendered,
        {p.name for p in bundle_dir.parent.iterdir() if p.is_dir() and p != bundle_dir},
    )
    previous = record.name
    record.name = target.name
    if previous and previous not in record.previous_names:
        record.previous_names.append(previous)
    record.naming["last_renamed_at"] = utc_now_iso()
    write_paper(bundle_dir, record)
    shutil.move(str(bundle_dir), str(target))
    return target


def _write_conversion_json(bundle_dir: Path, ok: bool, error: str | None = None) -> None:
    payload = {
        "ok": ok,
        "converted_at": utc_now_iso(),
        "error": error,
    }
    (bundle_dir / "conversion.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def convert_pending(library_dir: Path, converter: Converter) -> list[Path]:
    converted: list[Path] = []
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") == "done":
            continue
        result = converter.convert(bundle_dir / "original.pdf", bundle_dir)
        if not result.ok:
            record.status["conversion"] = "failed"
            write_paper(bundle_dir, record)
            _write_conversion_json(bundle_dir, ok=False, error=result.error)
            continue

        markdown_path = result.markdown_path or (bundle_dir / "paper.md")
        metadata_update = extract_metadata_from_markdown(markdown_path.read_text(encoding="utf-8"))
        record.metadata = _merge_metadata(record.metadata, metadata_update)
        record.status["conversion"] = "done"
        record.status["metadata"] = "complete" if record.metadata.get("title") else "partial"
        record.status["naming"] = "metadata"
        write_paper(bundle_dir, record)
        _write_conversion_json(bundle_dir, ok=True)
        converted.append(maybe_rename_bundle(library_dir, bundle_dir, record))
    rebuild_papers_index(library_dir)
    return converted
