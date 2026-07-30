from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from paper_cli.indexes import find_paper_dirs
from paper_cli.models import PaperRecord, read_paper, utc_now_iso

from .memory_state import clear_memory_state
from .providers import AIProvider

SUMMARY_DIR = Path("extracts") / "summary"
LIBRARY_MEMORY_DIR = Path("_memory")
ROOT_COLLECTION_KEY = "__root__"
RuntimeEventSink = Callable[[str, dict[str, Any]], None]


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(data: Any) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(canonical)


def _relative_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _write_atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def _bundle_collection_key(library_dir: Path, bundle_dir: Path, record: PaperRecord) -> str:
    if record.collection:
        return str(record.collection)
    relative = bundle_dir.relative_to(library_dir)
    parts = relative.parts
    if parts and parts[0] == "collections" and len(parts) >= 3:
        return str(Path(*parts[1:-1]))
    return ROOT_COLLECTION_KEY


def _collection_output_dir(library_dir: Path, collection_key: str) -> Path:
    if collection_key == ROOT_COLLECTION_KEY:
        return library_dir / LIBRARY_MEMORY_DIR / "collections" / ROOT_COLLECTION_KEY
    return library_dir / "collections" / collection_key / LIBRARY_MEMORY_DIR


def _collection_memory_path(library_dir: Path, collection_key: str) -> Path:
    return _collection_output_dir(library_dir, collection_key) / "collection-memory.json"


def _library_memory_path(library_dir: Path) -> Path:
    return library_dir / LIBRARY_MEMORY_DIR / "library-memory.json"


def _matches_collection(collection_key: str, selected: str | set[str] | None) -> bool:
    if not selected:
        return True
    if isinstance(selected, set):
        return collection_key in selected
    return collection_key == selected


def _normalize_collection_reference(value: str) -> str:
    normalized = str(value or "").strip().strip("/")
    if not normalized:
        return normalized
    parts = list(Path(normalized).parts)
    if parts and parts[0] == "collections":
        parts = parts[1:]
    if "_memory" in parts:
        parts = parts[: parts.index("_memory")]
    if parts and parts[-1].endswith((".json", ".md")):
        parts = parts[:-1]
    if not parts:
        return ROOT_COLLECTION_KEY
    return str(Path(*parts))


def _candidate_bundles(
    library_dir: Path,
    *,
    collection: str | set[str] | None = None,
    limit: int | None = None,
) -> list[tuple[Path, PaperRecord, str]]:
    rows: list[tuple[Path, PaperRecord, str]] = []
    for bundle_dir in find_paper_dirs(library_dir):
        if not (bundle_dir / "paper.md").exists():
            continue
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            continue
        collection_key = _bundle_collection_key(library_dir, bundle_dir, record)
        if not _matches_collection(collection_key, collection):
            continue
        rows.append((bundle_dir, record, collection_key))
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _load_summary_inputs(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    collection_key: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    summary_path = bundle_dir / SUMMARY_DIR / "summary.json"
    source_map_path = bundle_dir / SUMMARY_DIR / "source-map.json"
    bundle_row = {
        "kind": "paper",
        "paper_id": record.id,
        "collection_path": collection_key,
        "path": str(bundle_dir),
        "relative_path": _relative_path(bundle_dir, library_dir),
    }
    if not summary_path.exists():
        bundle_row["reason"] = "missing-summary"
        return None, None, bundle_row
    try:
        summary = _load_json(summary_path)
    except Exception as exc:
        bundle_row["reason"] = "invalid-summary"
        bundle_row["error"] = str(exc)
        return None, None, bundle_row
    source_map = None
    if source_map_path.exists():
        try:
            source_map = _load_json(source_map_path)
        except Exception as exc:
            bundle_row["reason"] = "invalid-source-map"
            bundle_row["error"] = str(exc)
            return None, None, bundle_row
    block_ids = {
        str(block.get("block_id") or "")
        for block in summary.get("blocks") or []
        if isinstance(block, dict) and block.get("block_id")
    }
    if source_map is not None:
        block_ids.update(
            str(block.get("block_id") or "")
            for block in source_map.get("blocks") or []
            if isinstance(block, dict) and block.get("block_id")
        )
    block_ids.discard("")
    if not block_ids:
        bundle_row["reason"] = "missing-traceability"
        return None, None, bundle_row
    for section in summary.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_ids = {str(item) for item in section.get("block_ids") or []}
        if not section_ids <= block_ids:
            bundle_row["reason"] = "missing-traceability"
            return None, None, bundle_row
    graph = summary.get("graph") if isinstance(summary.get("graph"), dict) else {}
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        node_ids = {str(item) for item in node.get("source_block_ids") or []}
        if not node_ids <= block_ids:
            bundle_row["reason"] = "missing-traceability"
            return None, None, bundle_row
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        edge_ids = {str(item) for item in edge.get("source_block_ids") or []}
        if not edge_ids <= block_ids:
            bundle_row["reason"] = "missing-traceability"
            return None, None, bundle_row
    return summary, source_map, None


def _block_importance_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def _pick_first_summary(rows: list[dict[str, Any]], role: str) -> str:
    for row in rows:
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        if summary.get("role") == role and summary.get("summary_text"):
            return str(summary["summary_text"])
    return ""


def _section_summary_by_role(rows: list[dict[str, Any]], role: str) -> str:
    for row in rows:
        if row.get("role") == role and row.get("summary"):
            return str(row["summary"])
    return ""


def _dedupe_texts(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _build_paper_memory(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    collection_key: str,
    summary: dict[str, Any],
    source_map: dict[str, Any] | None,
) -> dict[str, Any]:
    summary_blocks = [
        block for block in summary.get("blocks") or [] if isinstance(block, dict) and block.get("block_id")
    ]
    summary_sections = [
        section for section in summary.get("sections") or [] if isinstance(section, dict) and section.get("section_id")
    ]
    graph = summary.get("graph") if isinstance(summary.get("graph"), dict) else {}
    graph_nodes = [node for node in graph.get("nodes") or [] if isinstance(node, dict)]
    graph_edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]

    sorted_blocks = sorted(
        summary_blocks,
        key=lambda block: (
            -_block_importance_rank(
                str((block.get("summary") or {}).get("importance") or "medium")
            ),
            int((block.get("display") or {}).get("order") or 0),
        ),
    )
    important_block_ids = [str(block["block_id"]) for block in sorted_blocks[:5]]
    important_section_ids = _dedupe_texts(
        [str((block.get("display") or {}).get("section_id") or "") for block in sorted_blocks[:5]]
    )
    research_problem = _section_summary_by_role(summary_sections, "background") or _pick_first_summary(
        summary_blocks, "background"
    )
    method = _section_summary_by_role(summary_sections, "method") or _pick_first_summary(
        summary_blocks, "method"
    )
    key_results = _dedupe_texts(
        [
            str((block.get("summary") or {}).get("summary_text") or "")
            for block in summary_blocks
            if str((block.get("summary") or {}).get("role") or "") == "result"
        ]
    )[:5]
    limitations = _dedupe_texts(
        [
            str((block.get("summary") or {}).get("summary_text") or "")
            for block in summary_blocks
            if str((block.get("summary") or {}).get("role") or "") == "limitation"
        ]
        + [
            str(node.get("label") or "")
            for node in graph_nodes
            if str(node.get("type") or "") == "limitation"
        ]
    )[:5]
    concepts = _dedupe_texts(
        [
            item
            for block in summary_blocks
            for item in ((block.get("summary") or {}).get("concepts") or [])
            if isinstance(item, str)
        ]
        + [
            str(node.get("label") or "")
            for node in graph_nodes
            if str(node.get("type") or "") == "concept"
        ]
    )[:12]
    methods = _dedupe_texts(
        [str(node.get("label") or "") for node in graph_nodes if str(node.get("type") or "") == "method"]
    )[:12]
    measurements = _dedupe_texts(
        [
            str(node.get("label") or "")
            for node in graph_nodes
            if str(node.get("type") or "") == "measurement"
        ]
    )[:12]
    system_or_material = ""
    for node in graph_nodes:
        if str(node.get("type") or "") in {"dataset_or_sample", "instrument"}:
            system_or_material = str(node.get("label") or "")
            if system_or_material:
                break
    paper_source_map_path = (
        _relative_path(bundle_dir / SUMMARY_DIR / "source-map.json", library_dir) if source_map is not None else None
    )
    return {
        "paper_id": record.id,
        "title": record.metadata.get("title"),
        "creators": [item.get("name") for item in record.metadata.get("creators") or [] if isinstance(item, dict)],
        "year": record.metadata.get("year"),
        "bundle_path": _relative_path(bundle_dir, library_dir),
        "summary_path": _relative_path(bundle_dir / SUMMARY_DIR / "summary.json", library_dir),
        "source_map_path": paper_source_map_path,
        "source_summary_hash": _sha256_json(summary),
        "overview": " ".join(
            _dedupe_texts(
                [str(section.get("summary") or "") for section in summary_sections[:2]]
                or [str((summary_blocks[0].get("summary") or {}).get("summary_text") or "")]
            )[:2]
        ).strip(),
        "memory": {
            "research_problem": research_problem,
            "method": method,
            "system_or_material": system_or_material,
            "key_results": key_results,
            "limitations": limitations,
            "important_section_ids": important_section_ids,
            "important_block_ids": important_block_ids,
        },
        "concepts": concepts,
        "methods": methods,
        "measurements": measurements,
        "section_summaries": [
            {
                "section_id": section.get("section_id"),
                "heading": section.get("heading"),
                "summary": section.get("summary"),
                "block_ids": section.get("block_ids") or [],
                "role": section.get("role"),
            }
            for section in summary_sections
        ],
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
    }


def _collection_source_hashes(papers: list[dict[str, Any]]) -> dict[str, str]:
    return {str(paper["paper_id"]): str(paper["source_summary_hash"]) for paper in papers}


def _load_existing_memory_hashes(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        payload = _load_json(path)
    except Exception:
        return None
    source = payload.get("source")
    if not isinstance(source, dict):
        return None
    hashes = source.get("summary_hashes") or source.get("collection_hashes")
    if not isinstance(hashes, dict):
        return None
    return {str(key): str(value) for key, value in hashes.items()}


def _load_existing_collection_memories(
    library_dir: Path,
    *,
    exclude: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set(exclude)
    collections_root = library_dir / "collections"
    if not collections_root.exists():
        return rows
    for path in sorted(collections_root.glob("**/_memory/collection-memory.json")):
        try:
            payload = _load_json(path)
        except Exception:
            continue
        collection_path = _normalize_collection_reference(str(payload.get("collection_path") or ""))
        if not collection_path or collection_path in seen:
            continue
        rows.append(payload)
        seen.add(collection_path)
    return rows


def _validate_collection_response(
    response: dict[str, Any],
    papers: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    valid_paper_ids = {str(paper["paper_id"]) for paper in papers}
    valid_block_ids = {
        str(block_id)
        for paper in papers
        for block_id in paper["memory"]["important_block_ids"]
    }
    themes = []
    for row in response.get("collection_themes") or []:
        if not isinstance(row, dict):
            continue
        paper_ids = [str(item) for item in row.get("paper_ids") or []]
        source_block_ids = [str(item) for item in row.get("source_block_ids") or []]
        if not set(paper_ids) <= valid_paper_ids:
            warnings.append(f"Skipped collection theme with unknown paper IDs: {row.get('name')}")
            continue
        if not set(source_block_ids) <= valid_block_ids:
            warnings.append(f"Skipped collection theme with unknown block IDs: {row.get('name')}")
            continue
        themes.append(
            {
                "name": str(row.get("name") or ""),
                "summary": str(row.get("summary") or ""),
                "paper_ids": paper_ids,
                "source_block_ids": source_block_ids,
            }
        )
    relations = []
    for row in response.get("relations") or []:
        if not isinstance(row, dict):
            continue
        source_paper_id = str(row.get("source_paper_id") or "")
        target_paper_id = str(row.get("target_paper_id") or "")
        source_block_ids = [str(item) for item in row.get("source_block_ids") or []]
        target_block_ids = [str(item) for item in row.get("target_block_ids") or []]
        if source_paper_id not in valid_paper_ids or target_paper_id not in valid_paper_ids:
            warnings.append("Skipped collection relation with unknown paper IDs")
            continue
        if not set(source_block_ids) <= valid_block_ids or not set(target_block_ids) <= valid_block_ids:
            warnings.append("Skipped collection relation with unknown block IDs")
            continue
        relations.append(
            {
                "type": str(row.get("type") or ""),
                "source_paper_id": source_paper_id,
                "target_paper_id": target_paper_id,
                "summary": str(row.get("summary") or ""),
                "source_block_ids": source_block_ids,
                "target_block_ids": target_block_ids,
            }
        )
    if isinstance(response.get("warnings"), list):
        warnings.extend(str(item) for item in response["warnings"])
    return {
        "overview_summary": str(response.get("overview_summary") or ""),
        "themes": themes,
        "relations": relations,
        "representative_paper_ids": [
            str(item) for item in response.get("representative_paper_ids") or [] if str(item) in valid_paper_ids
        ],
    }, warnings


def _collection_messages(collection_path: str, papers: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You synthesize collection-level paper memory from supplied paper summaries. "
                "Return JSON only. Use only supplied paper IDs and block IDs."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Build collection memory.",
                    "collection_path": collection_path,
                    "papers": [
                        {
                            "paper_id": paper["paper_id"],
                            "title": paper["title"],
                            "creators": paper["creators"],
                            "year": paper["year"],
                            "overview": paper["overview"],
                            "memory": paper["memory"],
                            "concepts": paper["concepts"],
                            "methods": paper["methods"],
                            "measurements": paper["measurements"],
                            "section_summaries": paper["section_summaries"][:6],
                        }
                        for paper in papers
                    ],
                    "required_schema": {
                        "overview_summary": "collection overview",
                        "collection_themes": [
                            {
                                "name": "theme",
                                "summary": "theme summary",
                                "paper_ids": ["paper-id"],
                                "source_block_ids": ["blk_000001"],
                            }
                        ],
                        "relations": [
                            {
                                "type": "supports",
                                "source_paper_id": "paper-a",
                                "target_paper_id": "paper-b",
                                "summary": "relation summary",
                                "source_block_ids": ["blk_000001"],
                                "target_block_ids": ["blk_000002"],
                            }
                        ],
                        "representative_paper_ids": ["paper-id"],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _render_collection_markdown(memory: dict[str, Any]) -> str:
    lines = [f"# Collection Memory: {memory['collection_path']}", ""]
    lines.append(f"Generated: {memory['generated_at']}")
    lines.append("")
    if memory.get("overview_summary"):
        lines.append("## Overview")
        lines.append("")
        lines.append(memory["overview_summary"])
        lines.append("")
    lines.append("## Paper Memories")
    lines.append("")
    for paper in memory["papers"]:
        lines.append(f"### {paper['title'] or paper['paper_id']}")
        lines.append("")
        lines.append(f"- Paper ID: `{paper['paper_id']}`")
        lines.append(f"- Bundle: `{paper['bundle_path']}`")
        lines.append(f"- Summary: `{paper['summary_path']}`")
        if paper["memory"].get("research_problem"):
            lines.append(f"- Main problem: {paper['memory']['research_problem']}")
        if paper["memory"].get("method"):
            lines.append(f"- Main method: {paper['memory']['method']}")
        if paper["memory"].get("key_results"):
            lines.append(f"- Key results: {'; '.join(paper['memory']['key_results'])}")
        if paper["memory"].get("important_block_ids"):
            lines.append(f"- Source blocks: {', '.join(paper['memory']['important_block_ids'])}")
        lines.append("")
    if memory["themes"]:
        lines.append("## Shared Themes")
        lines.append("")
        for theme in memory["themes"]:
            lines.append(f"- {theme['name']}: {theme['summary']}")
        lines.append("")
    if memory["skipped_papers"]:
        lines.append("## Skipped Papers")
        lines.append("")
        for paper in memory["skipped_papers"]:
            lines.append(f"- `{paper['paper_id']}`: {paper['reason']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _paper_index_payload(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": memory["generated_at"],
        "collection_path": memory["collection_path"],
        "papers": {
            paper["paper_id"]: {
                "bundle_path": paper["bundle_path"],
                "summary_path": paper["summary_path"],
                "source_map_path": paper["source_map_path"],
                "important_section_ids": paper["memory"]["important_section_ids"],
                "important_block_ids": paper["memory"]["important_block_ids"],
            }
            for paper in memory["papers"]
        },
    }


def _build_collection_memory(
    library_dir: Path,
    collection_path: str,
    papers: list[dict[str, Any]],
    skipped_papers: list[dict[str, Any]],
    provider: AIProvider,
) -> dict[str, Any]:
    response = provider.complete_json(
        _collection_messages(collection_path, papers),
        schema_name="memory-build-collection",
    )
    normalized, warnings = _validate_collection_response(response, papers)
    memory = {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "collection_path": collection_path,
        "overview_summary": normalized["overview_summary"],
        "source": {
            "paper_count": len(papers) + len(skipped_papers),
            "summarized_paper_count": len(papers),
            "skipped_paper_count": len(skipped_papers),
            "summary_hashes": _collection_source_hashes(papers),
        },
        "papers": papers,
        "themes": normalized["themes"],
        "relations": normalized["relations"],
        "representative_paper_ids": normalized["representative_paper_ids"],
        "skipped_papers": skipped_papers,
        "warnings": warnings,
    }
    return memory


def _validate_library_response(
    response: dict[str, Any],
    collections: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    valid_collection_paths = {str(item["collection_path"]) for item in collections}
    valid_paper_ids = {
        str(paper["paper_id"])
        for collection in collections
        for paper in collection.get("papers") or []
        if isinstance(paper, dict)
    }
    collection_rows = []
    for row in response.get("collections") or []:
        if not isinstance(row, dict):
            continue
        collection_path = _normalize_collection_reference(str(row.get("collection_path") or ""))
        if collection_path not in valid_collection_paths:
            warnings.append(f"Skipped unknown collection in library response: {collection_path}")
            continue
        representative_paper_ids = [
            str(item)
            for item in row.get("representative_paper_ids") or []
            if str(item) in valid_paper_ids
        ]
        collection_rows.append(
            {
                "collection_path": collection_path,
                "summary": str(row.get("summary") or ""),
                "main_themes": [str(item) for item in row.get("main_themes") or [] if str(item)],
                "representative_paper_ids": representative_paper_ids,
            }
        )
    global_themes = []
    for row in response.get("global_themes") or []:
        if not isinstance(row, dict):
            continue
        collection_paths = [
            _normalize_collection_reference(str(item)) for item in row.get("collection_paths") or []
        ]
        paper_ids = [str(item) for item in row.get("paper_ids") or []]
        if not set(collection_paths) <= valid_collection_paths or not set(paper_ids) <= valid_paper_ids:
            warnings.append(f"Skipped invalid global theme: {row.get('name')}")
            continue
        global_themes.append(
            {
                "name": str(row.get("name") or ""),
                "summary": str(row.get("summary") or ""),
                "collection_paths": collection_paths,
                "paper_ids": paper_ids,
            }
        )
    relations = []
    for row in response.get("cross_collection_relations") or []:
        if not isinstance(row, dict):
            continue
        source_collection = _normalize_collection_reference(str(row.get("source_collection_path") or ""))
        target_collection = _normalize_collection_reference(str(row.get("target_collection_path") or ""))
        if source_collection not in valid_collection_paths or target_collection not in valid_collection_paths:
            warnings.append("Skipped invalid cross-collection relation")
            continue
        relations.append(
            {
                "type": str(row.get("type") or ""),
                "source_collection_path": source_collection,
                "target_collection_path": target_collection,
                "summary": str(row.get("summary") or ""),
            }
        )
    if isinstance(response.get("warnings"), list):
        warnings.extend(str(item) for item in response["warnings"])
    return {
        "overview_summary": str(response.get("overview_summary") or ""),
        "collections": collection_rows,
        "global_themes": global_themes,
        "cross_collection_relations": relations,
    }, warnings


def _library_messages(collections: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You synthesize top-level library memory from supplied collection memories. "
                "Return JSON only. Do not repeat every paper detail."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Build library memory.",
                    "collections": [
                        {
                            "collection_path": collection["collection_path"],
                            "overview_summary": collection.get("overview_summary") or "",
                            "paper_count": len(collection.get("papers") or []),
                            "themes": collection.get("themes") or [],
                            "representative_paper_ids": collection.get("representative_paper_ids") or [],
                        }
                        for collection in collections
                    ],
                    "required_schema": {
                        "overview_summary": "library overview",
                        "collections": [
                            {
                                "collection_path": "collections/example",
                                "summary": "collection summary",
                                "main_themes": ["theme"],
                                "representative_paper_ids": ["paper-id"],
                            }
                        ],
                        "global_themes": [
                            {
                                "name": "theme",
                                "summary": "theme summary",
                                "collection_paths": ["collections/example"],
                                "paper_ids": ["paper-id"],
                            }
                        ],
                        "cross_collection_relations": [
                            {
                                "type": "shares-concept",
                                "source_collection_path": "collections/a",
                                "target_collection_path": "collections/b",
                                "summary": "relation summary",
                            }
                        ],
                        "warnings": [],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _render_library_markdown(memory: dict[str, Any]) -> str:
    lines = ["# Library Memory", ""]
    lines.append(f"Generated: {memory['generated_at']}")
    lines.append("")
    if memory.get("overview_summary"):
        lines.append("## Overview")
        lines.append("")
        lines.append(memory["overview_summary"])
        lines.append("")
    lines.append("## Collections")
    lines.append("")
    for collection in memory["collections"]:
        lines.append(f"### {collection['collection_path']}")
        lines.append("")
        lines.append(f"- Memory: `{collection['memory_path']}`")
        lines.append(f"- Papers summarized: {collection['paper_count']}")
        if collection.get("summary"):
            lines.append(f"- Summary: {collection['summary']}")
        if collection.get("main_themes"):
            lines.append(f"- Main themes: {', '.join(collection['main_themes'])}")
        lines.append("")
    if memory["global_themes"]:
        lines.append("## Global Themes")
        lines.append("")
        for theme in memory["global_themes"]:
            lines.append(f"- {theme['name']}: {theme['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _collection_index_payload(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": memory["generated_at"],
        "collections": {
            collection["collection_path"]: {
                "memory_path": collection["memory_path"],
                "paper_count": collection["paper_count"],
                "representative_paper_ids": collection["representative_paper_ids"],
            }
            for collection in memory["collections"]
        },
    }


def _build_library_memory(library_dir: Path, collection_memories: list[dict[str, Any]], provider: AIProvider) -> dict[str, Any]:
    response = provider.complete_json(
        _library_messages(collection_memories),
        schema_name="memory-build-library",
    )
    normalized, warnings = _validate_library_response(response, collection_memories)
    collection_rows_by_path = {row["collection_path"]: row for row in normalized["collections"]}
    collections = []
    for memory in collection_memories:
        collection_path = str(memory["collection_path"])
        row = collection_rows_by_path.get(collection_path, {})
        memory_path = _relative_path(_collection_memory_path(library_dir, collection_path), library_dir)
        collections.append(
            {
                "collection_path": collection_path,
                "memory_path": memory_path,
                "paper_count": len(memory.get("papers") or []),
                "summary": str(row.get("summary") or memory.get("overview_summary") or ""),
                "main_themes": row.get("main_themes") or [theme["name"] for theme in memory.get("themes") or []][:5],
                "representative_paper_ids": row.get("representative_paper_ids")
                or memory.get("representative_paper_ids")
                or [],
            }
        )
    return {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "overview_summary": normalized["overview_summary"],
        "source": {
            "collection_count": len(collection_memories),
            "paper_count": sum(len(collection.get("papers") or []) for collection in collection_memories),
            "summarized_paper_count": sum(len(collection.get("papers") or []) for collection in collection_memories),
            "skipped_paper_count": sum(len(collection.get("skipped_papers") or []) for collection in collection_memories),
            "collection_hashes": {
                str(collection["collection_path"]): _sha256_json(collection) for collection in collection_memories
            },
        },
        "collections": collections,
        "global_themes": normalized["global_themes"],
        "cross_collection_relations": normalized["cross_collection_relations"],
        "skipped_collections": [],
        "warnings": warnings,
    }


def _build_plan(
    library_dir: Path,
    *,
    collection: str | set[str] | None = None,
    limit: int | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    skipped_by_collection: dict[str, list[dict[str, Any]]] = {}
    for bundle_dir, record, collection_key in _candidate_bundles(library_dir, collection=collection, limit=limit):
        summary, source_map, skipped = _load_summary_inputs(
            library_dir,
            bundle_dir,
            record,
            collection_key,
        )
        if skipped is not None:
            skipped_by_collection.setdefault(collection_key, []).append(skipped)
            continue
        assert summary is not None
        grouped.setdefault(collection_key, []).append(
            _build_paper_memory(library_dir, bundle_dir, record, collection_key, summary, source_map)
        )
    return grouped, skipped_by_collection


def build_memory_library(
    library_dir: Path,
    provider: AIProvider | None,
    *,
    collection: str | set[str] | None = None,
    limit: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    event_sink: RuntimeEventSink | None = None,
) -> dict[str, Any]:
    planned: list[dict[str, Any]] = []
    written: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    warnings: list[str] = []
    collection_stale_detected = False

    grouped, skipped_by_collection = _build_plan(library_dir, collection=collection, limit=limit)
    collection_keys = sorted(set(grouped) | set(skipped_by_collection))
    collection_memories: list[dict[str, Any]] = []

    for collection_key in collection_keys:
        papers = grouped.get(collection_key, [])
        skipped_papers = skipped_by_collection.get(collection_key, [])
        output_path = _collection_memory_path(library_dir, collection_key)
        source_hashes = _collection_source_hashes(papers)
        existing_hashes = _load_existing_memory_hashes(output_path)
        is_stale = existing_hashes is not None and existing_hashes != source_hashes
        if dry_run:
            if not output_path.exists() and papers:
                collection_stale_detected = True
            if output_path.exists():
                try:
                    collection_memories.append(_load_json(output_path))
                except Exception:
                    collection_stale_detected = True
            if is_stale:
                collection_stale_detected = True
            planned.append(
                {
                    "kind": "collection-memory",
                    "collection_path": collection_key,
                    "path": str(output_path),
                    "paper_count": len(papers),
                    "skipped_paper_count": len(skipped_papers),
                    "stale": is_stale,
                }
            )
            skipped.extend(skipped_papers)
            continue
        if output_path.exists() and not force:
            if is_stale:
                collection_stale_detected = True
            skipped.append(
                {
                    "kind": "collection-memory",
                    "collection_path": collection_key,
                    "path": str(output_path),
                    "reason": "memory_exists",
                    "stale": is_stale,
                }
            )
            skipped.extend(skipped_papers)
            try:
                collection_memories.append(_load_json(output_path))
            except Exception as exc:
                failed.append(
                    {
                        "kind": "collection-memory",
                        "collection_path": collection_key,
                        "path": str(output_path),
                        "error": str(exc),
                    }
                )
            continue
        if provider is None:
            raise ValueError("AI provider is required unless --dry-run is used")
        try:
            if event_sink:
                event_sink(
                    "stage-started",
                    {"path": str(output_path), "stage": "collection-memory", "count": len(papers)},
                )
            memory = _build_collection_memory(library_dir, collection_key, papers, skipped_papers, provider)
            output_dir = _collection_output_dir(library_dir, collection_key)
            _write_atomic_json(output_dir / "collection-memory.json", memory)
            _write_atomic_text(output_dir / "collection-memory.md", _render_collection_markdown(memory))
            _write_atomic_json(output_dir / "paper-index.json", _paper_index_payload(memory))
            collection_memories.append(memory)
            written.append(
                {
                    "kind": "collection-memory",
                    "collection_path": collection_key,
                    "path": str(output_dir / "collection-memory.json"),
                    "paper_count": len(papers),
                    "skipped_paper_count": len(skipped_papers),
                }
            )
            skipped.extend(skipped_papers)
            if event_sink:
                event_sink(
                    "stage-finished",
                    {"path": str(output_path), "stage": "collection-memory", "ok": True},
                )
        except Exception as exc:
            failed.append(
                {
                    "kind": "collection-memory",
                    "collection_path": collection_key,
                    "path": str(output_path),
                    "error": str(exc),
                }
            )
            if event_sink:
                event_sink(
                    "stage-failed",
                    {"path": str(output_path), "stage": "collection-memory", "error": str(exc)},
                )

    collection_memories.extend(
        _load_existing_collection_memories(
            library_dir,
            exclude={str(memory["collection_path"]) for memory in collection_memories},
        )
    )
    library_output_path = _library_memory_path(library_dir)
    collection_hashes = {
        str(memory["collection_path"]): _sha256_json(memory) for memory in collection_memories
    }
    existing_library_hashes = _load_existing_memory_hashes(library_output_path)
    library_stale = collection_stale_detected or (
        existing_library_hashes is not None and existing_library_hashes != collection_hashes
    )

    if dry_run:
        planned.append(
            {
                "kind": "library-memory",
                "path": str(library_output_path),
                "collection_count": len(collection_keys),
                "summarized_collection_count": len(grouped),
                "stale": library_stale,
            }
        )
    elif failed:
        warnings.append("Skipped library memory because one or more collection memories failed")
    elif library_output_path.exists() and not force:
        skipped.append(
            {
                "kind": "library-memory",
                "path": str(library_output_path),
                "reason": "memory_exists",
                "stale": library_stale,
            }
        )
    else:
        if provider is None:
            raise ValueError("AI provider is required unless --dry-run is used")
        try:
            if event_sink:
                event_sink("stage-started", {"path": str(library_output_path), "stage": "library-memory"})
            library_memory = _build_library_memory(library_dir, collection_memories, provider)
            output_dir = library_dir / LIBRARY_MEMORY_DIR
            _write_atomic_json(output_dir / "library-memory.json", library_memory)
            _write_atomic_text(output_dir / "library-memory.md", _render_library_markdown(library_memory))
            _write_atomic_json(output_dir / "collection-index.json", _collection_index_payload(library_memory))
            written.append(
                {
                    "kind": "library-memory",
                    "path": str(output_dir / "library-memory.json"),
                    "collection_count": len(collection_memories),
                }
            )
            clear_memory_state(
                library_dir,
                collection_paths=[str(memory["collection_path"]) for memory in collection_memories],
                paper_ids=[
                    str(paper["paper_id"])
                    for memory in collection_memories
                    for paper in memory.get("papers") or []
                    if isinstance(paper, dict) and paper.get("paper_id")
                ],
                clear_library=True,
            )
            if event_sink:
                event_sink(
                    "stage-finished",
                    {"path": str(library_output_path), "stage": "library-memory", "ok": True},
                )
        except Exception as exc:
            failed.append(
                {
                    "kind": "library-memory",
                    "path": str(library_output_path),
                    "error": str(exc),
                }
            )
            if event_sink:
                event_sink(
                    "stage-failed",
                    {"path": str(library_output_path), "stage": "library-memory", "error": str(exc)},
                )

    return {
        "ok": not failed,
        "planned": planned,
        "written": written,
        "skipped": skipped,
        "failed": failed,
        "warnings": warnings,
    }


def refresh_memory_for_bundles(
    library_dir: Path,
    provider: AIProvider,
    bundle_dirs: list[Path],
) -> dict[str, Any]:
    affected_collections: set[str] = set()
    for bundle_dir in bundle_dirs:
        if not (bundle_dir / "paper.yaml").exists():
            continue
        record = read_paper(bundle_dir)
        affected_collections.add(_bundle_collection_key(library_dir, bundle_dir, record))
    if not affected_collections:
        return {
            "ok": True,
            "planned": [],
            "written": [],
            "skipped": [],
            "failed": [],
            "warnings": [],
        }
    return build_memory_library(
        library_dir,
        provider,
        collection=affected_collections,
        force=True,
        dry_run=False,
    )
