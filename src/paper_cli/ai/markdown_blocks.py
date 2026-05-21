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


def _block_type(text: str) -> str:
    stripped = text.strip()
    lines = stripped.splitlines()
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("!["):
        return "image"
    if stripped.startswith("$$") or stripped.endswith("$$"):
        return "formula"
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
    return blocks


def is_suspicious_block(block: MarkdownBlock, bundle_dir) -> bool:
    text = block.text.strip()
    if not text:
        return False
    if re.fullmatch(r"(\d+|page\s+\d+)", text, flags=re.I):
        return True
    if "�" in text or "\ufffd" in text:
        return True
    if re.search(r"\b(?:[A-Za-z]\s){3,}[A-Za-z]\b", text):
        return True
    if block.type == "image":
        match = re.search(r"\]\(([^)]+)\)", text)
        if match and not (bundle_dir / match.group(1)).exists():
            return True
    if block.type == "paragraph" and len(text) < 8 and re.search(r"[A-Za-z]", text):
        return True
    return False


def suspicious_blocks(blocks: list[MarkdownBlock], bundle_dir) -> list[MarkdownBlock]:
    return [block for block in blocks if is_suspicious_block(block, bundle_dir)]


def render_blocks(blocks: list[MarkdownBlock]) -> str:
    return "\n\n".join(block.text for block in blocks if block.text.strip()) + "\n"
