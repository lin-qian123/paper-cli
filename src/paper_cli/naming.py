from __future__ import annotations

import re
import unicodedata

INVALID_FILENAME_CHARS = r'[\/:*?"<>|]+'
STRIP_UNICODE_CATEGORIES = {"Cc", "Cf", "Co", "Cs"}


def remove_problematic_unicode(value: str) -> str:
    return "".join(
        ch for ch in value if unicodedata.category(ch) not in STRIP_UNICODE_CATEGORIES
    )


def _first_creator(metadata: dict) -> str:
    creators = metadata.get("creators") or []
    if not creators:
        return ""
    first = creators[0]
    if isinstance(first, dict):
        return str(first.get("name") or "").strip()
    return str(first).strip()


def _title(metadata: dict, truncate: int | None = None) -> str:
    value = str(metadata.get("title") or "").strip()
    if truncate is not None and len(value) > truncate:
        return value[:truncate].rstrip()
    return value


def _year(metadata: dict) -> str:
    value = metadata.get("year")
    if value is None:
        return ""
    return str(value).strip()


def _append(value: str, suffix: str = "") -> str:
    return f"{value}{suffix}" if value else ""


def render_name(template: str, metadata: dict) -> str:
    """Render the controlled MVP subset of the naming template language."""
    language = str(metadata.get("language") or "").strip()
    first_creator = _first_creator(metadata)
    if language in {"zh", "zh-CN"}:
        creator_part = _append(first_creator, " - ")
    else:
        creator_part = _append(first_creator, " et al. - ")
    rendered = f"{creator_part}{_append(_year(metadata), ' - ')}{_title(metadata, truncate=100)}"
    return normalize_spaces(rendered).strip(" -")


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sanitize_name(value: str, max_length: int = 180) -> str:
    safe = remove_problematic_unicode(value)
    safe = re.sub(INVALID_FILENAME_CHARS, "-", safe)
    safe = re.sub(r"[\x00-\x1f]", "", safe)
    safe = normalize_spaces(safe)
    safe = safe.strip(" .-_")
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip(" .-_")
    return safe or "untitled"


def resolve_duplicate_name(base_name: str, existing_names: set[str]) -> str:
    if base_name not in existing_names:
        return base_name
    counter = 2
    while True:
        candidate = f"{base_name}-{counter}"
        if candidate not in existing_names:
            return candidate
        counter += 1
