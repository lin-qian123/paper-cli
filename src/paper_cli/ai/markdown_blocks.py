from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MarkdownBlock:
    id: str
    type: str
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class SuspiciousFinding:
    block: MarkdownBlock
    reasons: list[str]
    policy: str


AUTO_REPAIR = "auto_repair"
REVIEW_ONLY = "review_only"
STRUCTURAL_WARNING = "structural_warning"
PROTECTED_TYPES = {"formula", "table", "reference"}

BOILERPLATE_NOISE = {
    "article",
    "open",
    "open access",
    "check for updates",
    "research article",
    "original article",
}

COMMON_OCR_WORDS = {
    "Te",
    "Tere",
    "fssion",
    "diferent",
    "scientifc",
    "efciency",
    "frst",
    "simplifed",
}


def _block_type(text: str) -> str:
    stripped = text.strip()
    lines = stripped.splitlines()
    lowered = stripped.lower()
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("!["):
        return "image"
    if stripped.startswith("$$") or stripped.endswith("$$"):
        return "formula"
    if "<table" in lowered or "</table>" in lowered:
        return "table"
    if lines and all(line.lstrip().startswith("|") for line in lines):
        return "table"
    if re.match(r"^\s*(references|bibliography)\s*$", stripped, flags=re.I):
        return "reference"
    return "paragraph"


def split_markdown_blocks(markdown: str) -> list[MarkdownBlock]:
    blocks: list[MarkdownBlock] = []
    current: list[str] = []
    start_line = 1
    block_index = 0

    def flush(end_line: int) -> None:
        nonlocal block_index, current, start_line
        if not current:
            return
        text = "\n".join(current).strip("\n")
        blocks.append(
            MarkdownBlock(
                id=f"b{block_index:05d}",
                type=_block_type(text),
                start_line=start_line,
                end_line=end_line,
                text=text,
            )
        )
        block_index += 1
        current = []

    for line_no, line in enumerate(markdown.splitlines(), start=1):
        if line.strip() == "":
            flush(line_no - 1)
            start_line = line_no + 1
            continue
        if line.startswith("#") and current:
            flush(line_no - 1)
            start_line = line_no
        if not current:
            start_line = line_no
        current.append(line)
    flush(len(markdown.splitlines()))
    return _mark_reference_section(blocks)


def _is_reference_heading(block: MarkdownBlock) -> bool:
    return bool(re.match(r"^#+\s*(references|bibliography)\b", block.text.strip(), flags=re.I))


def _mark_reference_section(blocks: list[MarkdownBlock]) -> list[MarkdownBlock]:
    marked: list[MarkdownBlock] = []
    in_references = False
    for block in blocks:
        if block.type == "heading":
            if _is_reference_heading(block):
                in_references = True
                marked.append(_replace_block_type(block, "reference"))
                continue
            in_references = False
        if in_references:
            marked.append(_replace_block_type(block, "reference"))
        else:
            marked.append(block)
    return marked


def _replace_block_type(block: MarkdownBlock, block_type: str) -> MarkdownBlock:
    return MarkdownBlock(
        id=block.id,
        type=block_type,
        start_line=block.start_line,
        end_line=block.end_line,
        text=block.text,
    )


def _has_spaced_letters(text: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z])(?:[A-Za-z]\s+){3,}[A-Za-z](?![A-Za-z])", text))


def _has_spaced_digits(text: str) -> bool:
    return bool(re.search(r"(?<!\d)(?:\d\s+){2,}\d(?!\d)", text))


def _has_math(text: str) -> bool:
    return "$" in text or "\\" in text or any(token in text for token in ("_", "^", "\\mathrm"))


def _is_math_heavy(block: MarkdownBlock) -> bool:
    text = block.text
    if block.type in PROTECTED_TYPES:
        return True
    if not _has_math(text):
        return False
    math_chars = sum(text.count(token) for token in ("$", "\\", "_", "^", "{", "}"))
    return math_chars >= 8 or bool(re.search(r"\$[^$]*(?:[A-Za-z0-9]\s+){2,}[A-Za-z0-9][^$]*\$", text))


def _has_common_ocr_word(text: str) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in COMMON_OCR_WORDS)


def _has_repeated_phrase(text: str) -> bool:
    tokens = re.findall(r"[A-Za-z][A-Za-z-]*", text.lower())
    for size in range(4, 9):
        for index in range(0, len(tokens) - (size * 2) + 1):
            if tokens[index : index + size] == tokens[index + size : index + (size * 2)]:
                return True
    return False


def _policy_for(block: MarkdownBlock, reasons: list[str]) -> str:
    if "broken_image" in reasons:
        return STRUCTURAL_WARNING
    if block.type in PROTECTED_TYPES or "math_heavy" in reasons:
        return REVIEW_ONLY
    if "common_ocr_word" in reasons and len(block.text) > 320:
        return REVIEW_ONLY
    return AUTO_REPAIR


def is_suspicious_block(block: MarkdownBlock, bundle_dir) -> bool:
    return classify_suspicious_block(block, bundle_dir) is not None


def classify_suspicious_block(block: MarkdownBlock, bundle_dir) -> SuspiciousFinding | None:
    text = block.text.strip()
    if not text:
        return None
    reasons: list[str] = []
    if re.fullmatch(r"(\d+|page\s+\d+)", text, flags=re.I):
        reasons.append("page_number")
    if "�" in text or "\ufffd" in text:
        reasons.append("replacement_character")
    if _has_spaced_letters(text):
        reasons.append("spaced_letters")
    if _has_spaced_digits(text):
        reasons.append("spaced_digits")
    if _is_math_heavy(block) and {"spaced_letters", "spaced_digits"} & set(reasons):
        reasons.append("math_heavy")
    if block.type == "paragraph" and _has_common_ocr_word(text):
        reasons.append("common_ocr_word")
    if block.type == "paragraph" and _has_repeated_phrase(text):
        reasons.append("repeated_phrase")
    if text.lower() in BOILERPLATE_NOISE:
        reasons.append("front_matter_noise")
    if block.type == "image":
        match = re.search(r"\]\(([^)]+)\)", text)
        if match and not (bundle_dir / match.group(1)).exists():
            reasons.append("broken_image")
    if block.type == "paragraph" and len(text) < 8 and re.search(r"[A-Za-z]", text):
        reasons.append("short_text_noise")
    if not reasons:
        return None
    return SuspiciousFinding(block=block, reasons=reasons, policy=_policy_for(block, reasons))


def suspicious_findings(blocks: list[MarkdownBlock], bundle_dir) -> list[SuspiciousFinding]:
    findings = []
    for block in blocks:
        finding = classify_suspicious_block(block, bundle_dir)
        if finding is not None:
            findings.append(finding)
    return findings


def suspicious_blocks(blocks: list[MarkdownBlock], bundle_dir) -> list[MarkdownBlock]:
    return [finding.block for finding in suspicious_findings(blocks, bundle_dir)]


def repairable_suspicious_blocks(findings: list[SuspiciousFinding]) -> list[MarkdownBlock]:
    return [finding.block for finding in findings if finding.policy == AUTO_REPAIR]


def render_blocks(blocks: list[MarkdownBlock]) -> str:
    return "\n\n".join(block.text for block in blocks if block.text.strip()) + "\n"
