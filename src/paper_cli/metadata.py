from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

YEAR_PATTERN = re.compile(r"^(?P<creator>.+?)\s+-\s+(?P<year>\d{4})\s+-\s+(?P<title>.+)$")
logging.getLogger("pypdf").setLevel(logging.ERROR)


def detect_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh-CN"
    return "en"


def _creator_from_text(value: str) -> dict[str, str]:
    name = re.sub(r"\s+et\s+al\.?$", "", value.strip(), flags=re.IGNORECASE).strip()
    return {"name": name, "role": "author"} if name else {}


def _empty_metadata(title: str = "") -> dict[str, Any]:
    return {
        "title": title,
        "creators": [],
        "year": None,
        "language": detect_language(title),
        "doi": None,
    }


def metadata_from_filename(path: Path) -> dict[str, Any]:
    stem = path.stem.strip()
    match = YEAR_PATTERN.match(stem)
    if not match:
        return _empty_metadata(stem)

    creator = _creator_from_text(match.group("creator"))
    title = match.group("title").strip()
    return {
        "title": title,
        "creators": [creator] if creator else [],
        "year": int(match.group("year")),
        "language": detect_language(f"{creator.get('name', '')} {title}"),
        "doi": None,
    }


def metadata_from_pdf(path: Path) -> dict[str, Any]:
    try:
        reader = PdfReader(str(path))
        raw = reader.metadata or {}
    except Exception:
        return _empty_metadata()

    title = str(raw.get("/Title") or "").strip()
    author = str(raw.get("/Author") or "").strip()
    metadata = _empty_metadata(title)
    if author:
        metadata["creators"] = [{"name": author, "role": "author"}]
    return metadata


def fast_metadata(path: Path) -> dict[str, Any]:
    file_meta = metadata_from_filename(path)
    pdf_meta = metadata_from_pdf(path)
    merged = dict(file_meta)
    if pdf_meta.get("title") and not file_meta.get("title"):
        merged["title"] = pdf_meta["title"]
    if pdf_meta.get("creators") and not file_meta.get("creators"):
        merged["creators"] = pdf_meta["creators"]
    merged["language"] = detect_language(
        " ".join(
            [
                str(merged.get("title") or ""),
                " ".join(str(c.get("name", "")) for c in merged.get("creators", [])),
            ]
        )
    )
    return merged
