from __future__ import annotations

import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Semaphore
from typing import Any

from paper_cli.indexes import find_paper_dirs
from paper_cli.models import PaperRecord, read_paper, utc_now_iso

from .markdown_blocks import MarkdownBlock, split_markdown_blocks
from .providers import AIProvider

SUMMARY_DIR = Path("extracts") / "summary"
DEFAULT_EXTRACT_SUMMARY_WORKERS = 16
DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS = 16
DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS = 500
DEFAULT_EXTRACT_SUMMARY_RETRIES = 2
DEFAULT_EXTRACT_SUMMARY_RETRY_WAIT_SECONDS = 10.0
NON_MAIN_SECTIONS = {
    "acknowledgements",
    "acknowledgments",
    "author contribution",
    "author contributions",
    "bibliography",
    "conflict of interest",
    "conflicts of interest",
    "copyright",
    "declaration of competing interest",
    "funding",
    "open access",
    "references",
}
NODE_TYPES = {
    "concept",
    "method",
    "dataset_or_sample",
    "instrument",
    "measurement",
    "result",
    "limitation",
    "claim",
}
EDGE_TYPES = {
    "uses",
    "measures",
    "produces",
    "supports",
    "compares_with",
    "limits",
    "depends_on",
    "explains",
}


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _heading_text(block: MarkdownBlock) -> str:
    return block.text.lstrip("#").strip()


def _heading_level(block: MarkdownBlock) -> int:
    return len(block.text) - len(block.text.lstrip("#"))


def _section_id(index: int) -> str:
    return f"sec_{index:04d}"


def _block_id(index: int) -> str:
    return f"blk_{index:06d}"


def _is_non_main_section(section_path: list[str]) -> bool:
    for heading in section_path:
        normalized = heading.strip().lower()
        if normalized in NON_MAIN_SECTIONS:
            return True
        if any(normalized.startswith(prefix) for prefix in NON_MAIN_SECTIONS):
            return True
    return False


def _is_noise_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if stripped.isdigit():
        return True
    if lowered.startswith(("page ", "copyright", "open access")):
        return True
    return len(stripped) < 8 and any(ch.isalpha() for ch in stripped)


def _summary_policy(block: MarkdownBlock, section_path: list[str]) -> tuple[str, str | None]:
    if block.type == "reference" or _is_non_main_section(section_path):
        reason = "reference_section" if block.type == "reference" else "non_main_section"
        return "skip", reason
    if block.type == "heading":
        return "skip", "heading"
    if block.type in {"formula", "table", "image"}:
        return "context_only", block.type
    if _is_noise_text(block.text):
        return "skip", "noise"
    return "summarize", None


def build_source_map(markdown: str) -> dict[str, Any]:
    blocks = split_markdown_blocks(markdown)
    mapped: list[dict[str, Any]] = []
    markdown_hash = _sha256_text(markdown)
    section_stack: list[tuple[int, str, str]] = []
    section_counter = 0

    for index, block in enumerate(blocks):
        if block.type == "heading":
            level = _heading_level(block)
            heading = _heading_text(block)
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            if heading and level > 1:
                section_counter += 1
                section_stack.append((level, _section_id(section_counter), heading))
        section_path = [item[2] for item in section_stack]
        section_id = section_stack[-1][1] if section_stack else None
        policy, skip_reason = _summary_policy(block, section_path)
        mapped.append(
            {
                "block_id": _block_id(index),
                "type": block.type,
                "summary_policy": policy,
                "skip_reason": skip_reason,
                "start_line": block.start_line,
                "end_line": block.end_line,
                "section_id": section_id,
                "section_path": section_path,
                "order": index,
                "text_hash": _sha256_text(block.text),
                "text": block.text,
            }
        )

    return {
        "schema_version": 1,
        "markdown": "paper.md",
        "markdown_hash": markdown_hash,
        "blocks": mapped,
    }


def _excerpt(text: str, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit]


def _paper_brief(record: PaperRecord, source_map: dict[str, Any]) -> dict[str, Any]:
    headings = []
    for block in source_map["blocks"]:
        if block["type"] == "heading":
            headings.append(block["text"].lstrip("#").strip())
        if len(headings) >= 30:
            break
    return {
        "title": record.metadata.get("title"),
        "creators": record.metadata.get("creators"),
        "year": record.metadata.get("year"),
        "doi": record.metadata.get("doi"),
        "language": record.metadata.get("language"),
        "headings": headings,
    }


def _summarizable_blocks(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    return [block for block in source_map["blocks"] if block["summary_policy"] == "summarize"]


def _batch_blocks(
    blocks: list[dict[str, Any]], *, max_chars: int = 7000, max_blocks: int = 8
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for block in blocks:
        size = len(block["text"])
        if current and (len(current) >= max_blocks or current_chars + size > max_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(block)
        current_chars += size
    if current:
        batches.append(current)
    return batches


def effective_worker_count(*, workers: int, batch_count: int) -> int:
    if batch_count <= 0:
        return 0
    return min(max(1, workers), batch_count)


def _complete_json_with_retries(
    provider: AIProvider,
    messages: list[dict[str, str]],
    *,
    schema_name: str,
    request_limiter: Semaphore | None,
    retries: int,
    retry_wait: float,
) -> dict[str, Any]:
    attempts = max(0, retries) + 1
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if request_limiter is None:
                return provider.complete_json(messages, schema_name=schema_name)
            with request_limiter:
                return provider.complete_json(messages, schema_name=schema_name)
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            if retry_wait > 0:
                time.sleep(retry_wait)
    raise RuntimeError(
        f"{schema_name} failed after {attempts} attempt(s): {last_error}"
    ) from last_error


def _block_worker_messages(
    *,
    brief: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You summarize only the supplied paper blocks. Return JSON only. "
                "Use the brief only as orientation; do not repeat it in every block summary."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Summarize each supplied block for an article skeleton.",
                    "brief": brief,
                    "blocks": [
                        {
                            "block_id": block["block_id"],
                            "type": block["type"],
                            "start_line": block["start_line"],
                            "end_line": block["end_line"],
                            "section_path": block["section_path"],
                            "text": block["text"],
                        }
                        for block in blocks
                    ],
                    "required_schema": {
                        "blocks": [
                            {
                                "block_id": "blk_000000",
                                "summary_text": "content-dependent summary",
                                "summary_level": "short|medium|detailed",
                                "key_points": [],
                                "role": "background|method|result|discussion|limitation|other",
                                "importance": "low|medium|high",
                                "concepts": [],
                                "graph_candidates": [],
                            }
                        ],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _section_messages(
    *,
    brief: dict[str, Any],
    sections: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You aggregate block summaries into section skeletons. Return JSON only. "
                "Every section summary must be grounded in the supplied block_ids."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Create section-level skeleton summaries.",
                    "brief": brief,
                    "sections": sections,
                    "required_schema": {
                        "sections": [
                            {
                                "section_id": "sec_0001",
                                "summary": "section summary",
                                "key_points": [],
                                "role": "background|method|result|discussion|other",
                            }
                        ],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _graph_messages(
    *,
    blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Extract a small knowledge graph from supplied summaries. Return JSON only. "
                "Use only allowed node and edge types. Every node and edge needs source_block_ids."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Extract a conservative knowledge graph.",
                    "allowed_node_types": sorted(NODE_TYPES),
                    "allowed_edge_types": sorted(EDGE_TYPES),
                    "blocks": blocks,
                    "sections": sections,
                    "required_schema": {
                        "nodes": [
                            {
                                "id": "node_0001",
                                "type": "concept",
                                "label": "label",
                                "source_block_ids": ["blk_000000"],
                            }
                        ],
                        "edges": [
                            {
                                "source": "node_0001",
                                "target": "node_0002",
                                "type": "supports",
                                "source_block_ids": ["blk_000000"],
                            }
                        ],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _normalize_block_summaries(
    response: dict[str, Any], allowed_ids: set[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows = response.get("blocks") or []
    if not isinstance(rows, list):
        return [], ["Block summary response blocks was not a list"]
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        block_id = str(row.get("block_id") or "")
        if block_id not in allowed_ids:
            warnings.append(f"Unknown block summary skipped: {block_id}")
            continue
        summary_text = str(row.get("summary_text") or "").strip()
        if not summary_text:
            warnings.append(f"Empty block summary skipped: {block_id}")
            continue
        normalized.append(
            {
                "block_id": block_id,
                "summary_text": summary_text,
                "summary_level": str(row.get("summary_level") or "medium"),
                "key_points": row.get("key_points") if isinstance(row.get("key_points"), list) else [],
                "role": str(row.get("role") or "other"),
                "importance": str(row.get("importance") or "medium"),
                "concepts": row.get("concepts") if isinstance(row.get("concepts"), list) else [],
                "graph_candidates": row.get("graph_candidates")
                if isinstance(row.get("graph_candidates"), list)
                else [],
            }
        )
    if isinstance(response.get("warnings"), list):
        warnings.extend(str(item) for item in response["warnings"])
    return normalized, warnings


def _build_summary_blocks(
    *,
    source_map: dict[str, Any],
    block_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {block["block_id"]: block for block in source_map["blocks"]}
    rows = []
    for summary in sorted(block_summaries, key=lambda item: by_id[item["block_id"]]["order"]):
        source = by_id[summary["block_id"]]
        rows.append(
            {
                "block_id": summary["block_id"],
                "source_ref": {
                    "start_line": source["start_line"],
                    "end_line": source["end_line"],
                    "text_hash": source["text_hash"],
                    "excerpt": _excerpt(source["text"]),
                },
                "display": {
                    "order": source["order"],
                    "section_id": source["section_id"],
                    "section_path": source["section_path"],
                },
                "summary": {
                    "summary_text": summary["summary_text"],
                    "summary_level": summary["summary_level"],
                    "key_points": summary["key_points"],
                    "role": summary["role"],
                    "importance": summary["importance"],
                    "concepts": summary["concepts"],
                },
            }
        )
    return rows


def _section_inputs(
    *,
    source_map: dict[str, Any],
    summary_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_block_id = {block["block_id"]: block for block in source_map["blocks"]}
    sections: dict[str, dict[str, Any]] = {}
    for summary in summary_blocks:
        source = by_block_id[summary["block_id"]]
        section_id = source["section_id"] or "sec_0000"
        section = sections.setdefault(
            section_id,
            {
                "section_id": section_id,
                "heading": (source["section_path"][-1] if source["section_path"] else "Document"),
                "section_path": source["section_path"],
                "block_ids": [],
                "block_summaries": [],
            },
        )
        section["block_ids"].append(summary["block_id"])
        section["block_summaries"].append(
            {
                "block_id": summary["block_id"],
                "summary_text": summary["summary"]["summary_text"],
                "key_points": summary["summary"]["key_points"],
            }
        )
    return list(sections.values())


def _normalize_sections(
    response: dict[str, Any],
    section_inputs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    by_id = {section["section_id"]: section for section in section_inputs}
    rows = response.get("sections") or []
    if not isinstance(rows, list):
        rows = []
        warnings.append("Section response sections was not a list")
    normalized = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        section_id = str(row.get("section_id") or "")
        source = by_id.get(section_id)
        if source is None:
            warnings.append(f"Unknown section skipped: {section_id}")
            continue
        seen.add(section_id)
        normalized.append(
            {
                "section_id": section_id,
                "heading": source["heading"],
                "section_path": source["section_path"],
                "block_ids": source["block_ids"],
                "summary": str(row.get("summary") or ""),
                "key_points": row.get("key_points") if isinstance(row.get("key_points"), list) else [],
                "role": str(row.get("role") or "other"),
            }
        )
    for section in section_inputs:
        if section["section_id"] not in seen:
            normalized.append(
                {
                    "section_id": section["section_id"],
                    "heading": section["heading"],
                    "section_path": section["section_path"],
                    "block_ids": section["block_ids"],
                    "summary": " ".join(
                        item["summary_text"] for item in section["block_summaries"][:3]
                    ),
                    "key_points": [],
                    "role": "other",
                }
            )
    if isinstance(response.get("warnings"), list):
        warnings.extend(str(item) for item in response["warnings"])
    return normalized, warnings


def _normalize_graph(
    response: dict[str, Any],
    block_ids: set[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    warnings: list[str] = []
    nodes = []
    seen_nodes = set()
    for row in response.get("nodes") or []:
        if not isinstance(row, dict):
            continue
        node_id = str(row.get("id") or "")
        node_type = str(row.get("type") or "")
        source_ids = [str(item) for item in row.get("source_block_ids") or []]
        if not node_id or node_type not in NODE_TYPES or not set(source_ids) <= block_ids:
            warnings.append(f"Graph node skipped: {node_id}")
            continue
        seen_nodes.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": str(row.get("label") or ""),
                "source_block_ids": source_ids,
            }
        )
    edges = []
    for row in response.get("edges") or []:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        edge_type = str(row.get("type") or "")
        source_ids = [str(item) for item in row.get("source_block_ids") or []]
        if (
            source not in seen_nodes
            or target not in seen_nodes
            or edge_type not in EDGE_TYPES
            or not set(source_ids) <= block_ids
        ):
            warnings.append(f"Graph edge skipped: {source}->{target}")
            continue
        edges.append(
            {
                "source": source,
                "target": target,
                "type": edge_type,
                "source_block_ids": source_ids,
            }
        )
    if isinstance(response.get("warnings"), list):
        warnings.extend(str(item) for item in response["warnings"])
    return {"nodes": nodes, "edges": edges}, warnings


def _extract_block_summaries(
    *,
    provider: AIProvider,
    brief: dict[str, Any],
    batches: list[list[dict[str, Any]]],
    workers: int,
    request_limiter: Semaphore | None,
    retries: int,
    retry_wait: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not batches:
        return [], warnings
    block_by_id = {block["block_id"]: block for batch in batches for block in batch}

    def run_batch(index: int, batch: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], list[str]]:
        response = _complete_json_with_retries(
            provider,
            _block_worker_messages(brief=brief, blocks=batch),
            schema_name="extract-summary-blocks",
            request_limiter=request_limiter,
            retries=retries,
            retry_wait=retry_wait,
        )
        summaries, batch_warnings = _normalize_block_summaries(
            response,
            {block["block_id"] for block in batch},
        )
        return index, summaries, batch_warnings

    results: list[tuple[int, list[dict[str, Any]]]] = []
    effective_workers = effective_worker_count(workers=workers, batch_count=len(batches))
    if effective_workers <= 1:
        for index, batch in enumerate(batches):
            batch_index, summaries, batch_warnings = run_batch(index, batch)
            results.append((batch_index, summaries))
            warnings.extend(batch_warnings)
    else:
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            futures = {
                executor.submit(run_batch, index, batch): index for index, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                batch_index, summaries, batch_warnings = future.result()
                results.append((batch_index, summaries))
                warnings.extend(batch_warnings)
    summaries = []
    for _, batch_summaries in sorted(results, key=lambda item: item[0]):
        summaries.extend(batch_summaries)
    seen = {summary["block_id"] for summary in summaries}
    missing_ids = [block_id for block_id in block_by_id if block_id not in seen]
    if missing_ids:
        warnings.append(f"Retrying missing block summaries: {', '.join(missing_ids)}")
        retry_batches = [[block_by_id[block_id]] for block_id in missing_ids]
        for index, batch in enumerate(retry_batches):
            _, retry_summaries, retry_warnings = run_batch(index, batch)
            summaries.extend(retry_summaries)
            warnings.extend(retry_warnings)
    seen = {summary["block_id"] for summary in summaries}
    still_missing = [block_id for block_id in block_by_id if block_id not in seen]
    if still_missing:
        raise ValueError(f"Missing block summaries after retry: {', '.join(still_missing)}")
    return summaries, warnings


def _indexes(summary_blocks: list[dict[str, Any]], sections: list[dict[str, Any]]) -> dict[str, Any]:
    by_section = {section["section_id"]: {"block_ids": section["block_ids"]} for section in sections}
    by_block = {}
    for index, block in enumerate(summary_blocks):
        by_block[block["block_id"]] = {
            "summary_path": f"/blocks/{index}",
            "section_id": block["display"]["section_id"],
        }
    return {"by_block_id": by_block, "by_section_id": by_section}


def _render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = ["# AI Summary", ""]
    for section in summary["sections"]:
        lines.append(f"## {section['heading']}")
        lines.append("")
        if section["summary"]:
            lines.append(f"- Section summary: {section['summary']}")
        if section["key_points"]:
            lines.append("- Key points:")
            for point in section["key_points"]:
                lines.append(f"  - {point}")
        lines.append(f"- Source blocks: {', '.join(section['block_ids'])}")
        lines.append("")
    if summary["graph"]["nodes"] or summary["graph"]["edges"]:
        lines.append("## Knowledge Graph")
        lines.append("")
        for node in summary["graph"]["nodes"]:
            lines.append(
                f"- {node['id']} ({node['type']}): {node['label']} "
                f"[{', '.join(node['source_block_ids'])}]"
            )
        for edge in summary["graph"]["edges"]:
            lines.append(
                f"- {edge['source']} --{edge['type']}--> {edge['target']} "
                f"[{', '.join(edge['source_block_ids'])}]"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_outputs(bundle_dir: Path, summary: dict[str, Any], source_map: dict[str, Any]) -> None:
    output_dir = bundle_dir / SUMMARY_DIR
    tmp_dir = bundle_dir / "extracts" / ".summary.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (tmp_dir / "source-map.json").write_text(
        json.dumps(source_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (tmp_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    tmp_dir.rename(output_dir)


def extract_summary_bundle(
    bundle_dir: Path,
    record: PaperRecord,
    provider: AIProvider,
    *,
    workers: int = DEFAULT_EXTRACT_SUMMARY_WORKERS,
    force: bool = False,
    dry_run: bool = False,
    request_limiter: Semaphore | None = None,
    retries: int = DEFAULT_EXTRACT_SUMMARY_RETRIES,
    retry_wait: float = DEFAULT_EXTRACT_SUMMARY_RETRY_WAIT_SECONDS,
) -> dict[str, Any]:
    output_dir = bundle_dir / SUMMARY_DIR
    if output_dir.joinpath("summary.json").exists() and not force:
        return {"path": str(bundle_dir), "status": "skipped", "reason": "summary_exists"}
    markdown = (bundle_dir / "paper.md").read_text(encoding="utf-8")
    source_map = build_source_map(markdown)
    candidates = _summarizable_blocks(source_map)
    batches = _batch_blocks(candidates)
    if dry_run:
        return {
            "path": str(bundle_dir),
            "status": "planned",
            "summarizable_blocks": len(candidates),
            "batches": len(batches),
        }
    brief = _paper_brief(record, source_map)
    block_summaries, warnings = _extract_block_summaries(
        provider=provider,
        brief=brief,
        batches=batches,
        workers=max(1, workers),
        request_limiter=request_limiter,
        retries=retries,
        retry_wait=retry_wait,
    )
    summary_blocks = _build_summary_blocks(source_map=source_map, block_summaries=block_summaries)
    section_inputs = _section_inputs(source_map=source_map, summary_blocks=summary_blocks)
    section_response = _complete_json_with_retries(
        provider,
        _section_messages(brief=brief, sections=section_inputs),
        schema_name="extract-summary-sections",
        request_limiter=request_limiter,
        retries=retries,
        retry_wait=retry_wait,
    )
    sections, section_warnings = _normalize_sections(section_response, section_inputs)
    warnings.extend(section_warnings)
    graph_response = _complete_json_with_retries(
        provider,
        _graph_messages(blocks=summary_blocks, sections=sections),
        schema_name="extract-summary-graph",
        request_limiter=request_limiter,
        retries=retries,
        retry_wait=retry_wait,
    )
    graph, graph_warnings = _normalize_graph(
        graph_response,
        {block["block_id"] for block in summary_blocks},
    )
    warnings.extend(graph_warnings)
    summary = {
        "schema_version": 1,
        "paper_id": record.id,
        "generated_at": utc_now_iso(),
        "provider": provider.name,
        "model": provider.model,
        "source": {
            "markdown": "paper.md",
            "markdown_hash": source_map["markdown_hash"],
        },
        "blocks": summary_blocks,
        "sections": sections,
        "graph": graph,
        "indexes": _indexes(summary_blocks, sections),
        "warnings": warnings,
    }
    _write_outputs(bundle_dir, summary, source_map)
    return {
        "path": str(bundle_dir),
        "status": "extracted",
        "blocks_summarized": len(summary_blocks),
        "sections": len(sections),
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
        "warnings": warnings,
    }


def _matches_paper(record: PaperRecord, bundle_dir: Path, paper: str | None) -> bool:
    if not paper:
        return True
    return record.id.startswith(paper) or bundle_dir.name.startswith(paper) or record.name.startswith(paper)


def _matches_collection(record: PaperRecord, collection: str | None) -> bool:
    if not collection:
        return True
    return record.collection == collection


def _candidate_bundles(
    library_dir: Path,
    *,
    paper: str | None = None,
    collection: str | None = None,
    limit: int | None = None,
) -> list[tuple[Path, PaperRecord]]:
    candidates = []
    for bundle_dir in find_paper_dirs(library_dir):
        if not (bundle_dir / "paper.md").exists():
            continue
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            continue
        if not _matches_paper(record, bundle_dir, paper):
            continue
        if not _matches_collection(record, collection):
            continue
        candidates.append((bundle_dir, record))
        if limit is not None and len(candidates) >= limit:
            break
    return candidates


def extract_summary_library(
    library_dir: Path,
    provider: AIProvider | None,
    *,
    paper: str | None = None,
    collection: str | None = None,
    limit: int | None = None,
    workers: int = DEFAULT_EXTRACT_SUMMARY_WORKERS,
    paper_workers: int = DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
    max_requests: int = DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
    retries: int = DEFAULT_EXTRACT_SUMMARY_RETRIES,
    retry_wait: float = DEFAULT_EXTRACT_SUMMARY_RETRY_WAIT_SECONDS,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    extracted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    candidates = _candidate_bundles(
        library_dir,
        paper=paper,
        collection=collection,
        limit=limit,
    )
    request_limiter = Semaphore(max(1, max_requests))

    def run_candidate(index: int, bundle_dir: Path, record: PaperRecord) -> tuple[int, dict[str, Any]]:
        try:
            if dry_run:
                row = extract_summary_bundle(
                    bundle_dir,
                    record,
                    provider,  # type: ignore[arg-type]
                    workers=workers,
                    force=force,
                    dry_run=True,
                )
                return index, row
            if provider is None:
                raise ValueError("AI provider is required unless --dry-run is used")
            row = extract_summary_bundle(
                bundle_dir,
                record,
                provider,
                workers=workers,
                force=force,
                dry_run=False,
                request_limiter=request_limiter,
                retries=retries,
                retry_wait=retry_wait,
            )
            return index, row
        except Exception as exc:
            return index, {"path": str(bundle_dir), "status": "failed", "error": str(exc)}

    results: list[tuple[int, dict[str, Any]]] = []
    effective_paper_workers = effective_worker_count(
        workers=paper_workers,
        batch_count=len(candidates),
    )
    if effective_paper_workers <= 1 or dry_run:
        for index, (bundle_dir, record) in enumerate(candidates):
            results.append(run_candidate(index, bundle_dir, record))
    else:
        with ThreadPoolExecutor(max_workers=effective_paper_workers) as executor:
            futures = {
                executor.submit(run_candidate, index, bundle_dir, record): index
                for index, (bundle_dir, record) in enumerate(candidates)
            }
            for future in as_completed(futures):
                results.append(future.result())

    for _, row in sorted(results, key=lambda item: item[0]):
        if row["status"] == "planned":
            planned.append(row)
        elif row["status"] == "skipped":
            skipped.append(row)
        elif row["status"] == "failed":
            failed.append({"path": row["path"], "error": row["error"]})
        else:
            extracted.append(row)
    return {
        "ok": not failed,
        "extracted": extracted,
        "skipped": skipped,
        "planned": planned,
        "failed": failed,
    }
