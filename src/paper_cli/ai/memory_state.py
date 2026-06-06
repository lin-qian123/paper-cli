from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paper_cli.models import read_paper, utc_now_iso

MEMORY_STATE_PATH = Path("indexes") / "memory-state.json"
ROOT_COLLECTION_KEY = "__root__"


def _default_state() -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "schema_version": 1,
        "updated_at": now,
        "papers": {},
        "collections": {},
        "library": {
            "stale": False,
            "reason": None,
            "updated_at": now,
        },
    }


def _load_state(library_dir: Path) -> dict[str, Any]:
    path = library_dir / MEMORY_STATE_PATH
    if not path.exists():
        return _default_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_state()
    if not isinstance(payload, dict):
        return _default_state()
    state = _default_state()
    state.update(payload)
    if not isinstance(state.get("papers"), dict):
        state["papers"] = {}
    if not isinstance(state.get("collections"), dict):
        state["collections"] = {}
    if not isinstance(state.get("library"), dict):
        state["library"] = _default_state()["library"]
    return state


def _save_state(library_dir: Path, state: dict[str, Any]) -> None:
    path = library_dir / MEMORY_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now_iso()
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _collection_key(library_dir: Path, bundle_dir: Path, collection: str | None) -> str:
    if collection:
        return collection
    relative = bundle_dir.relative_to(library_dir)
    parts = relative.parts
    if parts and parts[0] == "collections" and len(parts) >= 3:
        return str(Path(*parts[1:-1]))
    return ROOT_COLLECTION_KEY


def mark_bundles_stale(library_dir: Path, bundle_dirs: list[Path], *, reason: str) -> None:
    if not bundle_dirs:
        return
    state = _load_state(library_dir)
    now = utc_now_iso()
    affected_collections: set[str] = set()
    for bundle_dir in bundle_dirs:
        if not (bundle_dir / "paper.yaml").exists():
            continue
        record = read_paper(bundle_dir)
        collection_path = _collection_key(library_dir, bundle_dir, record.collection)
        affected_collections.add(collection_path)
        state["papers"][record.id] = {
            "paper_id": record.id,
            "bundle_path": str(bundle_dir.relative_to(library_dir)),
            "collection_path": collection_path,
            "stale": True,
            "reason": reason,
            "updated_at": now,
        }
    for collection_path in affected_collections:
        state["collections"][collection_path] = {
            "collection_path": collection_path,
            "stale": True,
            "reason": reason,
            "updated_at": now,
        }
    state["library"] = {
        "stale": True,
        "reason": reason,
        "updated_at": now,
    }
    _save_state(library_dir, state)


def clear_memory_state(
    library_dir: Path,
    *,
    collection_paths: list[str],
    paper_ids: list[str],
    clear_library: bool,
) -> None:
    state = _load_state(library_dir)
    now = utc_now_iso()
    for paper_id in paper_ids:
        entry = state["papers"].get(paper_id) or {"paper_id": paper_id}
        entry["stale"] = False
        entry["reason"] = None
        entry["updated_at"] = now
        state["papers"][paper_id] = entry
    for collection_path in collection_paths:
        entry = state["collections"].get(collection_path) or {"collection_path": collection_path}
        entry["stale"] = False
        entry["reason"] = None
        entry["updated_at"] = now
        state["collections"][collection_path] = entry
    if clear_library:
        remaining_stale = any(
            bool(entry.get("stale"))
            for key, entry in state["collections"].items()
            if key not in set(collection_paths)
        )
        state["library"] = {
            "stale": remaining_stale,
            "reason": "dependent-collections" if remaining_stale else None,
            "updated_at": now,
        }
    _save_state(library_dir, state)
