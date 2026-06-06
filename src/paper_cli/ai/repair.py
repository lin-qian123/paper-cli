from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paper_cli.convert import maybe_rename_bundle
from paper_cli.indexes import find_paper_dirs, rebuild_papers_index
from paper_cli.metadata import normalize_creators, valid_creators
from paper_cli.models import PaperRecord, read_paper, utc_now_iso, write_paper

from .markdown_blocks import (
    MarkdownBlock,
    render_blocks,
    repairable_suspicious_blocks,
    split_markdown_blocks,
    suspicious_findings,
)
from .providers import AIProvider

SUPPORTED_METADATA_FIELDS = {"title", "creators", "year", "doi", "language"}
HIGH_IMPACT_FIELDS = {"title", "creators", "year", "doi"}
ACCEPTED_CONFIDENCE = {"medium", "high"}


@dataclass
class MetadataRepairResult:
    changed: bool = False
    changes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MarkdownRepairResult:
    changed: bool = False
    blocks_checked: int = 0
    blocks_changed: int = 0
    warnings: list[str] = field(default_factory=list)
    warnings_by_reason: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    repaired_markdown: str | None = field(default=None, repr=False)

    def warning_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "reason": reason,
                "count": len(block_ids),
                "block_ids": sorted(set(block_ids)),
            }
            for reason, block_ids in sorted(self.warnings_by_reason.items())
        ]


@dataclass
class BundleRepairResult:
    path: Path
    targets: list[str]
    metadata: MetadataRepairResult = field(default_factory=MetadataRepairResult)
    markdown: MarkdownRepairResult = field(default_factory=MarkdownRepairResult)
    warnings: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "targets": self.targets,
            "metadata_changed": self.metadata.changed,
            "markdown_changed": self.markdown.changed,
            "warnings": self.warnings + self.metadata.warnings + self.markdown.warnings,
            "markdown_warning_summary": self.markdown.warning_summary(),
        }


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON in {path.name}"}
    return payload if isinstance(payload, dict) else {}


def _markdown_head(markdown: str, *, max_chars: int = 8000, max_blocks: int = 40) -> str:
    blocks = split_markdown_blocks(markdown)[:max_blocks]
    text = "\n\n".join(block.text for block in blocks)
    return text[:max_chars]


def _identifier_candidates(text: str) -> dict[str, list[str]]:
    return {
        "doi": sorted(set(re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text))),
        "arxiv": sorted(set(re.findall(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b", text, flags=re.I))),
        "pmid": sorted(set(re.findall(r"\bPMID[:\s]+(\d+)\b", text, flags=re.I))),
        "isbn": sorted(
            set(re.findall(r"\b(?:97[89][-\s]?)?\d[-\s]?\d{3}[-\s]?\d{5}[-\s]?\d\b", text))
        ),
    }


def build_metadata_evidence(bundle_dir: Path, record: PaperRecord) -> dict[str, Any]:
    markdown = (bundle_dir / "paper.md").read_text(encoding="utf-8")
    head = _markdown_head(markdown)
    return {
        "current_metadata": record.metadata,
        "metadata_sources": record.metadata_sources,
        "metadata_confidence": record.metadata_confidence,
        "bundle_name": bundle_dir.name,
        "source_pdf_filename": Path(str(record.source.get("imported_from") or "")).name,
        "markdown_head": head,
        "identifier_candidates": _identifier_candidates(head),
        "conversion": _read_json_file(bundle_dir / "conversion.json"),
    }


def _metadata_messages(evidence: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You repair paper.yaml metadata using only local evidence. Return JSON only. "
                "Do not invent scientific content or rewrite prose."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Propose safe metadata repairs.",
                    "supported_fields": sorted(SUPPORTED_METADATA_FIELDS),
                    "required_schema": {
                        "proposed_metadata": {},
                        "field_changes": [
                            {
                                "field": "title",
                                "old": "old value",
                                "new": "new value",
                                "confidence": "medium|high",
                                "source": "ai-md-head",
                                "evidence": "short local evidence",
                            }
                        ],
                        "warnings": [],
                    },
                    "evidence": evidence,
                },
                ensure_ascii=False,
            ),
        },
    ]


def _valid_metadata_value(field: str, value: Any) -> bool:
    if value in (None, "", []):
        return False
    if field in {"title", "doi", "language"}:
        return isinstance(value, str)
    if field == "year":
        return isinstance(value, int) and 1000 <= value <= 3000
    if field == "creators":
        return valid_creators(value)
    return False


def _normalize_metadata_value(field: str, value: Any) -> Any:
    if field != "creators":
        return value
    return normalize_creators(value)


def _is_user_high_confidence(record: PaperRecord, field: str) -> bool:
    return (
        record.metadata_sources.get(field) == "user"
        and record.metadata_confidence.get(field) == "high"
    )


def repair_metadata(
    bundle_dir: Path,
    record: PaperRecord,
    provider: AIProvider,
    *,
    dry_run: bool,
) -> MetadataRepairResult:
    result = MetadataRepairResult()
    response = provider.complete_json(
        _metadata_messages(build_metadata_evidence(bundle_dir, record)),
        schema_name="metadata-repair",
    )
    changes = response.get("field_changes") or []
    if not isinstance(changes, list):
        result.warnings.append("AI metadata response field_changes was not a list")
        return result
    for change in changes:
        if not isinstance(change, dict):
            continue
        field = str(change.get("field") or "")
        confidence = str(change.get("confidence") or "")
        new = _normalize_metadata_value(field, change.get("new"))
        evidence = str(change.get("evidence") or "")
        if field not in SUPPORTED_METADATA_FIELDS:
            result.warnings.append(f"Unsupported metadata field skipped: {field}")
            continue
        if confidence not in ACCEPTED_CONFIDENCE:
            result.warnings.append(f"Low-confidence metadata change skipped: {field}")
            continue
        if field in HIGH_IMPACT_FIELDS and not evidence:
            result.warnings.append(f"Metadata change without evidence skipped: {field}")
            continue
        if _is_user_high_confidence(record, field):
            result.warnings.append(f"User high-confidence field preserved: {field}")
            continue
        if not _valid_metadata_value(field, new):
            result.warnings.append(f"Invalid metadata value skipped: {field}")
            continue
        old = record.metadata.get(field)
        if old == new:
            continue
        result.changes.append(
            {
                "field": field,
                "old": old,
                "new": new,
                "confidence": confidence,
                "evidence": evidence,
            }
        )
    result.changed = bool(result.changes)
    return result


def apply_metadata_changes(record: PaperRecord, changes: list[dict[str, Any]]) -> None:
    for change in changes:
        field = str(change["field"])
        record.metadata[field] = change["new"]
        record.metadata_sources[field] = "ai-repair"
        record.metadata_confidence[field] = str(change["confidence"])


def _markdown_messages(blocks: list[MarkdownBlock]) -> list[dict[str, str]]:
    block_payload = [
        {
            "id": block.id,
            "type": block.type,
            "start_line": block.start_line,
            "end_line": block.end_line,
            "text": block.text,
        }
        for block in blocks
    ]
    return [
        {
            "role": "system",
            "content": (
                "You repair only explicit Markdown extraction defects. Return JSON only. "
                "Use exact old_text from the supplied block. Do not change scientific meaning."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Patch suspicious Markdown blocks.",
                    "blocks": block_payload,
                    "required_schema": {
                        "block_patches": [
                            {
                                "block_id": "b00000",
                                "action": "replace",
                                "old_text": "exact old text",
                                "new_text": "replacement",
                                "reason": "short reason",
                                "confidence": "medium|high",
                            }
                        ],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _allows_empty_replacement(old_text: str, reason: str) -> bool:
    reason_l = reason.lower()
    if any(word in reason_l for word in ("header", "footer", "page")):
        return True
    return bool(re.fullmatch(r"(\d+|page\s+\d+)", old_text.strip(), flags=re.I))


def _record_warning(
    result: MarkdownRepairResult,
    *,
    reason: str,
    block: MarkdownBlock,
    message: str,
) -> None:
    result.warnings.append(f"{reason} [{block.id}]: {message}")
    result.warnings_by_reason[reason].append(block.id)


def repair_markdown(
    bundle_dir: Path,
    provider: AIProvider,
    *,
    dry_run: bool,
) -> MarkdownRepairResult:
    result = MarkdownRepairResult()
    markdown_path = bundle_dir / "paper.md"
    if not markdown_path.exists():
        result.warnings.append("Missing paper.md; skipped Markdown repair")
        return result
    markdown = markdown_path.read_text(encoding="utf-8")
    blocks = split_markdown_blocks(markdown)
    findings = suspicious_findings(blocks, bundle_dir)
    candidates = repairable_suspicious_blocks(findings)
    result.blocks_checked = len(findings)
    for finding in findings:
        if finding.policy != "auto_repair":
            message = (
                f"{finding.policy} suspicious block skipped: ({', '.join(finding.reasons)}) "
                f"at {finding.block.id}"
            )
            for reason in finding.reasons:
                _record_warning(
                    result,
                    reason=f"{finding.policy}:{reason}",
                    block=finding.block,
                    message=message,
                )
            _record_warning(
                result,
                reason=f"{finding.policy}:all",
                block=finding.block,
                message=message,
            )
    if not candidates:
        return result
    response = provider.complete_json(_markdown_messages(candidates), schema_name="markdown-repair")
    patches = response.get("block_patches") or []
    if not isinstance(patches, list):
        fallback_block = (
            blocks[0]
            if blocks
            else MarkdownBlock(id="unknown", type="unknown", start_line=0, end_line=0, text="")
        )
        _record_warning(
            result,
            reason="provider:non_list_block_patches",
            block=fallback_block,
            message="AI Markdown response block_patches was not a list",
        )
        return result
    by_id = {block.id: block for block in blocks}
    changed_ids: set[str] = set()
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        block_id = str(patch.get("block_id") or "")
        block = by_id.get(block_id)
        if block is None:
            fallback_block = (
                blocks[0]
                if blocks
                else MarkdownBlock(id="unknown", type="unknown", start_line=0, end_line=0, text="")
            )
            _record_warning(
                result,
                reason="provider:unknown_block_id",
                block=fallback_block,
                message=f"Unknown block id skipped: {block_id}",
            )
            continue
        old_text = str(patch.get("old_text") or "")
        new_text = str(patch.get("new_text") or "")
        confidence = str(patch.get("confidence") or "")
        reason = str(patch.get("reason") or "")
        if confidence not in ACCEPTED_CONFIDENCE:
            _record_warning(
                result,
                reason="provider:low_confidence",
                block=block,
                message=f"Low-confidence Markdown patch skipped: {block_id}",
            )
            continue
        if old_text != block.text:
            _record_warning(
                result,
                reason="provider:old_text_mismatch",
                block=block,
                message=f"Patch old_text mismatch skipped: {block_id}",
            )
            continue
        if new_text == "" and not _allows_empty_replacement(old_text, reason):
            _record_warning(
                result,
                reason="provider:empty_patch",
                block=block,
                message=f"Empty Markdown patch skipped: {block_id}",
            )
            continue
        if block.type in {"formula", "table", "reference"} and new_text != old_text:
            _record_warning(
                result,
                reason="provider:protected_block",
                block=block,
                message=f"Protected Markdown block skipped: {block_id}",
            )
            continue
        changed_ids.add(block_id)
        index = blocks.index(block)
        blocks[index] = MarkdownBlock(
            id=block.id,
            type=block.type,
            start_line=block.start_line,
            end_line=block.end_line,
            text=new_text,
        )
    result.blocks_changed = len(changed_ids)
    result.changed = bool(changed_ids)
    if result.changed:
        result.repaired_markdown = render_blocks(blocks)
    return result


def _backup_file(bundle_dir: Path, filename: str, timestamp: str) -> None:
    source = bundle_dir / filename
    if not source.exists():
        return
    backup_dir = bundle_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    safe_timestamp = timestamp.replace(":", "").replace("+", "Z")
    shutil.copy2(source, backup_dir / f"{filename}.{safe_timestamp}.bak")


def _write_repair_json(
    bundle_dir: Path,
    *,
    provider: AIProvider,
    targets: list[str],
    dry_run: bool,
    metadata: MetadataRepairResult,
    markdown: MarkdownRepairResult,
) -> None:
    payload = {
        "schema_version": 1,
        "repaired_at": utc_now_iso(),
        "provider": provider.name,
        "model": provider.model,
        "targets": targets,
        "dry_run": dry_run,
        "metadata": {
            "changed": metadata.changed,
            "changes": metadata.changes,
            "warnings": metadata.warnings,
        },
        "markdown": {
            "changed": markdown.changed,
            "blocks_checked": markdown.blocks_checked,
            "blocks_changed": markdown.blocks_changed,
            "warnings": markdown.warnings,
            "warning_summary": markdown.warning_summary(),
        },
    }
    (bundle_dir / "repair.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _expanded_targets(target: str) -> list[str]:
    return ["metadata", "markdown"] if target == "all" else [target]


def _normalize_collection_reference(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    if normalized.startswith("collections/"):
        normalized = normalized[len("collections/") :]
    return normalized.strip("/")


def _matches_paper(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    paper: str | None,
) -> bool:
    if not paper:
        return True
    query = paper.casefold()
    if record.id.casefold().startswith(query):
        return True
    if query in record.id.casefold():
        return True
    if query in record.name.casefold():
        return True
    if query in bundle_dir.name.casefold():
        return True
    try:
        relative_path = str(bundle_dir.relative_to(library_dir)).casefold()
    except ValueError:
        relative_path = str(bundle_dir).casefold()
    return query in relative_path


def _matches_collection(record: PaperRecord, collection: str | None) -> bool:
    if not collection:
        return True
    query = _normalize_collection_reference(collection)
    if query == "inbox":
        return record.collection is None
    record_collection = _normalize_collection_reference(str(record.collection or ""))
    return record_collection == query


def _candidate_bundles(
    library_dir: Path,
    *,
    paper: str | None = None,
    collection: str | None = None,
    limit: int | None = None,
) -> list[tuple[Path, PaperRecord]]:
    candidates: list[tuple[Path, PaperRecord]] = []
    for bundle_dir in find_paper_dirs(library_dir):
        if not (bundle_dir / "paper.md").exists():
            continue
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            continue
        if not _matches_paper(library_dir, bundle_dir, record, paper):
            continue
        if not _matches_collection(record, collection):
            continue
        candidates.append((bundle_dir, record))
        if limit is not None and len(candidates) >= limit:
            break
    return candidates


def repair_library(
    library_dir: Path,
    provider: AIProvider,
    *,
    target: str = "all",
    dry_run: bool = False,
    paper: str | None = None,
    collection: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    targets = _expanded_targets(target)
    repaired: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for bundle_dir, record in _candidate_bundles(
        library_dir,
        paper=paper,
        collection=collection,
        limit=limit,
    ):
        current_dir = bundle_dir
        bundle_result = BundleRepairResult(path=current_dir, targets=targets)
        timestamp = utc_now_iso()
        try:
            if "metadata" in targets:
                bundle_result.metadata = repair_metadata(
                    current_dir,
                    record,
                    provider,
                    dry_run=dry_run,
                )
            if "markdown" in targets:
                bundle_result.markdown = repair_markdown(current_dir, provider, dry_run=dry_run)
            bundle_result.path = current_dir
            if dry_run:
                repaired.append(bundle_result.to_summary())
                continue
            if bundle_result.metadata.changed:
                _backup_file(current_dir, "paper.yaml", timestamp)
                apply_metadata_changes(record, bundle_result.metadata.changes)
                write_paper(current_dir, record)
                current_dir = maybe_rename_bundle(library_dir, current_dir, record)
            if bundle_result.markdown.changed:
                _backup_file(current_dir, "paper.md", timestamp)
                (current_dir / "paper.md").write_text(
                    bundle_result.markdown.repaired_markdown or "",
                    encoding="utf-8",
                )
            bundle_result.path = current_dir
            _write_repair_json(
                current_dir,
                provider=provider,
                targets=targets,
                dry_run=dry_run,
                metadata=bundle_result.metadata,
                markdown=bundle_result.markdown,
            )
            repaired.append(bundle_result.to_summary())
        except Exception as exc:
            failed.append({"path": str(current_dir), "error": str(exc)})
    if not dry_run:
        rebuild_papers_index(library_dir)
    return {
        "ok": not failed,
        "target": target,
        "paper": paper,
        "collection": collection,
        "limit": limit,
        "dry_run": dry_run,
        "repaired": repaired,
        "failed": failed,
    }
