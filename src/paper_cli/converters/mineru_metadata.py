from __future__ import annotations

import re
from typing import Any

from paper_cli.metadata import detect_language, normalize_creators
from paper_cli.naming import remove_problematic_unicode

DOI_PATTERN = re.compile(r"\b(10\.\d{4,9}/[^\s<>'\"{}|\\^`\]]+)", re.IGNORECASE)
ARXIV_PATTERN = re.compile(r"\barXiv\s*:\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", re.IGNORECASE)
JOURNAL_LABELS = {
    "SCIENTIFIC REPORTS",
    "NATURE",
    "SCIENCE",
    "PHYSICAL REVIEW LETTERS",
    "PHYSICAL REVIEW A",
    "PHYSICAL REVIEW E",
    "NEW JOURNAL OF PHYSICS",
}


def extract_mineru_metadata(
    markdown: str,
    *,
    existing: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    lines = [remove_problematic_unicode(line).strip() for line in markdown.splitlines()]
    metadata: dict[str, Any] = {}
    sources: dict[str, str] = {}
    confidence: dict[str, str] = {}

    title = _first_heading(lines)
    if title and not _bad_title(title, existing):
        metadata["title"] = title
        sources["title"] = "mineru"
        confidence["title"] = "high"

    authors_line = _explicit_authors_line(lines)
    creators_confidence = "high"
    if authors_line is None:
        authors_line = _title_page_authors_line(lines, title)
        creators_confidence = "medium"
    creators = normalize_creators(authors_line) if authors_line else []
    if creators:
        metadata["creators"] = creators
        sources["creators"] = "mineru" if creators_confidence == "high" else "mineru-title-page"
        confidence["creators"] = creators_confidence

    year = _explicit_year(lines)
    if year:
        metadata["year"] = year
        sources["year"] = "mineru"
        confidence["year"] = "high"

    doi = _first_doi(markdown)
    if doi:
        metadata["doi"] = doi
        sources["doi"] = "mineru"
        confidence["doi"] = "high"

    arxiv = _first_arxiv(markdown)
    if arxiv:
        metadata["arxiv"] = arxiv
        sources["arxiv"] = "mineru"
        confidence["arxiv"] = "high"

    if title or creators:
        metadata["language"] = detect_language(f"{title or ''} {authors_line or ''}")
        sources["language"] = "detected"
        confidence["language"] = "medium"

    return metadata, sources, confidence


def _first_heading(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            return title or None
    return None


def _explicit_authors_line(lines: list[str]) -> str | None:
    for line in lines[:80]:
        if line.lower().startswith("authors:"):
            return line.split(":", 1)[1].strip()
    return None


def _explicit_year(lines: list[str]) -> int | None:
    for line in lines[:80]:
        if line.lower().startswith("year:"):
            match = re.search(r"\d{4}", line)
            if match:
                return int(match.group(0))
    return None


def _title_page_authors_line(lines: list[str], title: str | None) -> str | None:
    passed_title = title is None
    for line in lines[:30]:
        if line.startswith("# "):
            passed_title = True
            continue
        if not passed_title or not line:
            continue
        candidate = line.strip()
        if _looks_like_author_line(candidate):
            return candidate
    return None


def _looks_like_author_line(value: str) -> bool:
    lowered = value.lower()
    if any(
        marker in lowered
        for marker in [
            "@",
            "abstract",
            "institute",
            "university",
            "laboratory",
            "department",
            "copyright",
            "doi",
            "arxiv",
            "received",
            "accepted",
        ]
    ):
        return False
    if len(value) > 240 or len(value) < 5:
        return False
    if sum(ch.isdigit() for ch in value) > 2:
        return False
    if "," not in value and " and " not in lowered and ";" not in value:
        return False
    creators = normalize_creators(value)
    return bool(creators) and len(creators) <= 20


def _first_doi(markdown: str) -> str | None:
    match = DOI_PATTERN.search(markdown)
    if not match:
        return None
    return match.group(1).rstrip(".,;)")


def _first_arxiv(markdown: str) -> str | None:
    match = ARXIV_PATTERN.search(markdown)
    return match.group(1) if match else None


def _bad_title(title: str, existing: dict[str, Any] | None = None) -> bool:
    stripped = title.strip()
    if not stripped:
        return True
    normalized = re.sub(r"\s+", " ", stripped).upper()
    if normalized in JOURNAL_LABELS:
        return True
    return False
