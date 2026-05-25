from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .naming import remove_problematic_unicode

YEAR_PATTERN = re.compile(r"^(?P<creator>.+?)\s+-\s+(?P<year>\d{4})\s+-\s+(?P<title>.+)$")
logging.getLogger("pypdf").setLevel(logging.ERROR)


def detect_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh-CN"
    return "en"


def normalize_creators(value: Any) -> list[dict[str, str]]:
    if value in (None, "", []):
        return []
    items = value
    if isinstance(value, str):
        normalized = re.sub(r"\s+and\s+", ",", value.strip())
        items = [part.strip() for part in re.split(r"[;,]", normalized) if part.strip()]
    if not isinstance(items, list):
        return []

    creators: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            name = remove_problematic_unicode(item).strip()
            role = "author"
        elif isinstance(item, dict):
            name = remove_problematic_unicode(str(item.get("name") or "")).strip()
            role = str(item.get("role") or "author").strip() or "author"
        else:
            return []
        name = re.sub(r"\s+et\s+al\.?$", "", name, flags=re.IGNORECASE).strip()
        if not name:
            return []
        creators.append({"name": name, "role": role})
    return creators


def valid_creators(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return all(
        isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip()
        for item in value
    )


def _creator_from_text(value: str) -> dict[str, str]:
    creators = normalize_creators(value)
    return creators[0] if creators else {}


def _empty_metadata(title: str = "") -> dict[str, Any]:
    return {
        "title": title,
        "creators": [],
        "year": None,
        "language": detect_language(title),
        "doi": None,
    }


def metadata_from_filename(path: Path) -> dict[str, Any]:
    stem = remove_problematic_unicode(path.stem).strip()
    match = YEAR_PATTERN.match(stem)
    if not match:
        return _empty_metadata(stem)

    creator = _creator_from_text(match.group("creator"))
    title = remove_problematic_unicode(match.group("title")).strip()
    return {
        "title": title,
        "creators": [creator] if creator else [],
        "year": int(match.group("year")),
        "language": detect_language(f"{creator.get('name', '')} {title}"),
        "doi": None,
    }


def filename_metadata_details(path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    metadata = metadata_from_filename(path)
    stem = remove_problematic_unicode(path.stem).strip()
    matched = YEAR_PATTERN.match(stem) is not None
    sources: dict[str, str] = {}
    confidence: dict[str, str] = {}
    if metadata.get("title"):
        sources["title"] = "filename" if matched else "filename-stem"
        confidence["title"] = "medium" if matched else "low"
    if metadata.get("creators"):
        sources["creators"] = "filename"
        confidence["creators"] = "medium"
    if metadata.get("year"):
        sources["year"] = "filename"
        confidence["year"] = "medium"
    if metadata.get("language"):
        sources["language"] = "detected"
        confidence["language"] = "medium"
    return metadata, sources, confidence


def metadata_from_pdf(path: Path) -> dict[str, Any]:
    try:
        reader = PdfReader(str(path))
        raw = reader.metadata or {}
    except Exception:
        return _empty_metadata()

    title = remove_problematic_unicode(str(raw.get("/Title") or "")).strip()
    author = remove_problematic_unicode(str(raw.get("/Author") or "")).strip()
    metadata = _empty_metadata(title)
    if author:
        metadata["creators"] = normalize_creators(author)
    return metadata


def pdf_metadata_details(path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    metadata = metadata_from_pdf(path)
    sources: dict[str, str] = {}
    confidence: dict[str, str] = {}
    if metadata.get("title"):
        sources["title"] = "pdf-metadata"
        confidence["title"] = "medium"
    if metadata.get("creators"):
        sources["creators"] = "pdf-metadata"
        confidence["creators"] = "medium"
    if metadata.get("language"):
        sources["language"] = "detected"
        confidence["language"] = "medium"
    return metadata, sources, confidence


def fast_metadata(path: Path) -> dict[str, Any]:
    return fast_metadata_details(path)[0]


def fast_metadata_details(path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    file_meta, sources, confidence = filename_metadata_details(path)
    pdf_meta, pdf_sources, pdf_confidence = pdf_metadata_details(path)
    merged = dict(file_meta)
    if pdf_meta.get("title") and not file_meta.get("title"):
        merged["title"] = pdf_meta["title"]
        sources["title"] = pdf_sources["title"]
        confidence["title"] = pdf_confidence["title"]
    if pdf_meta.get("creators") and not file_meta.get("creators"):
        merged["creators"] = pdf_meta["creators"]
        sources["creators"] = pdf_sources["creators"]
        confidence["creators"] = pdf_confidence["creators"]
    merged["language"] = detect_language(
        " ".join(
            [
                str(merged.get("title") or ""),
                " ".join(str(c.get("name", "")) for c in merged.get("creators", [])),
            ]
        )
    )
    sources["language"] = "detected"
    confidence["language"] = "medium"
    return merged, sources, confidence
