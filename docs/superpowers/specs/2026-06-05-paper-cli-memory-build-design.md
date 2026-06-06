# paper-cli Paper Memory Build Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `paper memory build`, a library-level and collection-level memory builder that consumes existing `paper extract summary` outputs and creates a progressive-disclosure memory system for agents.

**Architecture:** The command is a third built-in AI layer after `paper repair` and `paper extract summary`. It does not read full papers again and does not auto-run summary extraction; instead it synthesizes memory from existing `extracts/summary/summary.json`, `source-map.json`, and bundle metadata. Outputs live under library and collection `_memory/` directories and preserve pointers back to paper bundles, sections, and source block IDs.

**Tech Stack:** Python CLI, existing `paper_cli` library discovery/config/provider utilities, JSON/Markdown filesystem contracts, fake-provider tests with `pytest`, `ruff`, and `make verify`.

---

## Status

This is a planning document only. It records the approved direction for `paper memory build`; implementation has not started in this document.

Confirmed product decisions:

- `paper memory build` is based on existing `paper extract summary` results.
- Missing `extracts/summary/summary.json` is skipped and reported; the command must not auto-run `paper extract summary`.
- The first useful scope is hierarchical memory for agents:
  - paper layer: existing `extracts/summary/` outputs.
  - collection layer: synthesized memory for one collection/category.
  - library layer: top-level memory across collections.
- The design should support later frontend reading views by keeping durable links from memory items back to paper summaries, source maps, sections, and block IDs.

## Goals

- Build an agent memory surface that can answer "what is in this library?" without loading every paper.
- Preserve progressive disclosure: library memory points to collection memory; collection memory points to per-paper summaries; per-paper summaries point to source blocks.
- Reuse the current article skeleton from `paper extract summary` instead of repeating paper-level extraction.
- Keep outputs local, deterministic in layout, and inspectable by humans and agents.
- Make skipped and stale inputs visible instead of silently hiding gaps.

## Non-Goals

First version does not:

- Run MinerU conversion.
- Run `paper repair`.
- Run `paper extract summary` automatically.
- Modify `paper.md`, `paper.yaml`, `repair.json`, `summary.json`, or `source-map.json`.
- Read full `paper.md` as the primary source for memory synthesis.
- Implement open-ended literature search or web research; that remains outside core `paper-cli` and belongs to companion agent workflows such as `paper-research-plugin`.
- Build a global vector database.
- Build a full citation graph from external services.
- Require every collection to have complete summaries before memory can be built.

## Command Contract

Recommended CLI surface:

```bash
paper memory build
paper memory build --collection <collection-path>
paper memory build --limit 5
paper memory build --force
paper memory build --dry-run
paper memory build --json
```

Default behavior:

- Run from a `paper-cli` library root.
- Discover converted bundles with existing `extracts/summary/summary.json`.
- Build collection memory for collections that have at least one summarized paper.
- Build library memory from available collection memories.
- Skip papers missing `summary.json`; report them in JSON and Markdown outputs.
- Skip existing `_memory/*.json` outputs unless `--force` is supplied.
- Use `--dry-run` to report planned collections, summarized papers, missing summaries, existing memory outputs, and stale candidates without invoking the AI provider or writing files.

Open question for implementation: whether `--limit` should cap papers globally or per collection. Recommended first behavior is global cap, matching existing command patterns.

## Input Contract

Primary input files:

```text
<paper-bundle>/
  paper.yaml
  extracts/
    summary/
      summary.json
      source-map.json
```

`summary.json` should provide:

- paper metadata snapshot where available.
- block summaries with stable `block_id`.
- section summaries with `block_ids`.
- graph nodes and edges with `source_block_ids`.
- source hash or enough source metadata to detect staleness.

`source-map.json` should provide:

- `block_id`.
- `start_line` / `end_line`.
- `text_hash`.
- `section_path`.
- summary policy and skip reason.

`paper.yaml` should provide:

- stable paper ID.
- title.
- creators/authors.
- year.
- DOI/arXiv ID where available.
- bundle metadata and current folder name.

If `source-map.json` is missing but `summary.json` exists, first version should warn and proceed with weaker traceability only if `summary.json` still contains block IDs and source pointers. If block IDs cannot be recovered, skip that paper with reason `missing-traceability`.

## Output Contract

Recommended library-level layout:

```text
<library-root>/
  _memory/
    library-memory.json
    library-memory.md
    collection-index.json
```

Recommended collection-level layout:

```text
<library-root>/
  collections/
    <collection-path>/
      _memory/
        collection-memory.json
        collection-memory.md
        paper-index.json
```

If a library uses a flat layout or bundles outside `collections/`, implementation should map them into a synthetic collection key such as `__root__` and write the corresponding memory under `<library-root>/_memory/collections/__root__/` to avoid ambiguous paths.

All writes should be atomic: write to a temporary file in the same directory, then replace the target.

## JSON Shape

### `collection-memory.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-05T00:00:00Z",
  "collection_path": "collections/example",
  "source": {
    "paper_count": 12,
    "summarized_paper_count": 10,
    "skipped_paper_count": 2,
    "summary_hashes": {
      "paper-id": "sha256:..."
    }
  },
  "papers": [
    {
      "paper_id": "paper-id",
      "title": "Paper title",
      "creators": ["Author A", "Author B"],
      "year": 2026,
      "bundle_path": "collections/example/Author - 2026 - Title",
      "summary_path": "collections/example/Author - 2026 - Title/extracts/summary/summary.json",
      "source_map_path": "collections/example/Author - 2026 - Title/extracts/summary/source-map.json",
      "memory": {
        "research_problem": "...",
        "method": "...",
        "system_or_material": "...",
        "key_results": ["..."],
        "limitations": ["..."],
        "important_section_ids": ["sec_0001"],
        "important_block_ids": ["blk_0001", "blk_0002"]
      },
      "concepts": ["..."],
      "methods": ["..."],
      "measurements": ["..."]
    }
  ],
  "themes": [
    {
      "name": "Shared theme",
      "summary": "...",
      "paper_ids": ["paper-id"],
      "source_block_ids": ["blk_0001"]
    }
  ],
  "relations": [
    {
      "type": "supports|contrasts|extends|uses-method|shares-concept",
      "source_paper_id": "paper-a",
      "target_paper_id": "paper-b",
      "summary": "...",
      "source_block_ids": ["blk_0001"],
      "target_block_ids": ["blk_0009"]
    }
  ],
  "skipped_papers": [
    {
      "paper_id": "paper-id",
      "bundle_path": "collections/example/Missing",
      "reason": "missing-summary"
    }
  ],
  "warnings": []
}
```

### `library-memory.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-05T00:00:00Z",
  "source": {
    "collection_count": 3,
    "paper_count": 100,
    "summarized_paper_count": 80,
    "skipped_paper_count": 20
  },
  "collections": [
    {
      "collection_path": "collections/example",
      "memory_path": "collections/example/_memory/collection-memory.json",
      "paper_count": 12,
      "summary": "...",
      "main_themes": ["..."],
      "representative_paper_ids": ["paper-id"]
    }
  ],
  "global_themes": [
    {
      "name": "...",
      "summary": "...",
      "collection_paths": ["collections/example"],
      "paper_ids": ["paper-id"]
    }
  ],
  "cross_collection_relations": [],
  "skipped_collections": [],
  "warnings": []
}
```

## Markdown Outputs

`collection-memory.md` should be human-readable and stable enough for an agent to skim:

```markdown
# Collection Memory: collections/example

Generated: 2026-06-05T00:00:00Z

## Overview

...

## Paper Memories

### Paper title

- Paper ID: `...`
- Bundle: `...`
- Summary: `.../extracts/summary/summary.json`
- Main contribution: ...
- Key methods: ...
- Key results: ...
- Source blocks: `blk_0001`, `blk_0002`

## Shared Themes

...

## Skipped Papers

...
```

`library-memory.md` should be a top-level index and should avoid copying every paper detail:

```markdown
# Library Memory

## Collections

### collections/example

- Memory: `collections/example/_memory/collection-memory.json`
- Papers summarized: 10/12
- Main themes: ...

## Global Themes

...
```

## AI Synthesis Strategy

Recommended first implementation is a hybrid pipeline:

1. Deterministically collect and compact existing paper summaries.
2. Use AI provider calls only for collection-level and library-level synthesis.
3. Keep prompts bounded: include metadata, section summaries, top important block summaries, graph nodes/edges, and source pointers, but not full block text.
4. Require structured JSON responses with paper IDs, section IDs, and block IDs copied from input.
5. Validate that every returned paper ID and block ID exists in the collected input.

Rejected first-version alternatives:

- Deterministic-only memory: cheap and reliable, but too weak for cross-paper theme synthesis.
- Full-paper reread: too expensive and violates the decision to build from existing summary outputs.
- External subagent fan-out: useful conceptually, but less reproducible inside a local CLI than bounded internal provider calls.

Concurrency can be added conservatively after the serial path works. The first implementation may process collections serially if it keeps provider calls bounded and error reporting clear.

## Prompt Boundary

Collection synthesis prompt should tell the model:

- Use only the supplied summaries and source IDs.
- Do not invent missing facts, citations, experiments, authors, or results.
- Prefer concise but information-dense memory.
- Preserve paper IDs and block IDs exactly.
- Separate themes, methods, measurements, results, and limitations.
- Mark uncertainty in `warnings` instead of filling gaps.

Library synthesis prompt should be even more compact:

- Use only collection-level memory summaries.
- Do not repeat all paper-level details.
- Produce a map of collections, global themes, and cross-collection links.

## Staleness and Idempotency

First version should compute a hash for every consumed `summary.json`, for example `sha256` of canonical JSON bytes. Store these hashes in collection memory.

Default skip behavior:

- If target memory exists and `--force` is not provided, skip it.
- If target memory exists but source hashes differ, report `stale=true` in `--dry-run` and regular JSON output.
- Do not overwrite stale memory unless `--force` is supplied.

Future enhancement:

- Add a `paper memory status` command to report stale/missing memory without building it.

## Error Handling

- Missing provider config:
  - `--dry-run`: allowed, because no AI calls are made.
  - normal build: fail clearly before writing outputs that need AI synthesis.
- Missing `summary.json`: skip paper with `reason=missing-summary`.
- Missing `source-map.json`: warn; skip only if traceability cannot be recovered.
- Malformed `summary.json`: skip paper with `reason=invalid-summary`.
- Provider failure for one collection: report the collection in `failed[]`, do not write partial collection memory, and continue other collections when safe.
- Library synthesis failure after collection memories are written: keep valid collection memories and report library memory as failed.
- Existing output without `--force`: report as skipped, not failed.

CLI JSON should include:

```json
{
  "ok": true,
  "planned": [],
  "written": [],
  "skipped": [],
  "failed": [],
  "warnings": []
}
```

## File Structure

Expected implementation files:

- Modify `src/paper_cli/cli.py`
  - Add `paper memory build` subcommand.
  - Wire target options, provider config loading, `--dry-run`, `--force`, and `--json`.
- Create `src/paper_cli/ai/memory_build.py`
  - Discover summary outputs.
  - Load and validate `summary.json` / `source-map.json`.
  - Build compact paper memory inputs.
  - Call provider for collection and library synthesis.
  - Validate returned IDs.
  - Write JSON/Markdown outputs atomically.
- Create or extend tests in `tests/test_ai_memory_build.py`
  - Cover dry-run, skip behavior, missing summaries, fake-provider synthesis, stale detection, and atomic failure behavior.
- Update `README.md`
  - Only after implementation: document `paper memory build` under command list and AI features.
- Update `TODO.md` and `docs/zh/TODO.zh.md`
  - Track implementation progress and validation results.
- Optional later contract docs:
  - `docs/contracts/memory.md`
  - `docs/zh/contracts/memory.zh.md`

## Chunk 1: Command Skeleton and Dry Run

### Task 1: Add Memory Command Surface

**Files:**

- Modify: `src/paper_cli/cli.py`
- Create: `tests/test_ai_memory_build.py`

- [ ] **Step 1: Write failing CLI test**

  Test that `paper memory build --dry-run --json` works without provider config and reports planned/skipped papers from fixture summaries.

- [ ] **Step 2: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_dry_run_without_provider
  ```

  Expected: FAIL because `paper memory` does not exist.

- [ ] **Step 3: Add argparse subcommands**

  Add `memory` and `build` parsers, with `--collection`, `--limit`, `--force`, `--dry-run`, and `--json`.

- [ ] **Step 4: Implement placeholder dry-run path**

  Return structured JSON with discovered candidates, skipped missing summaries, and no writes.

- [ ] **Step 5: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_dry_run_without_provider
  ```

  Expected: PASS.

## Chunk 2: Input Discovery and Traceability

### Task 2: Load Summary Inputs

**Files:**

- Create: `src/paper_cli/ai/memory_build.py`
- Modify: `tests/test_ai_memory_build.py`

- [ ] **Step 1: Write failing tests**

  Cover:

  - paper with valid `summary.json` and `source-map.json` is included.
  - missing `summary.json` is skipped with `missing-summary`.
  - malformed `summary.json` is skipped with `invalid-summary`.
  - missing traceability is skipped with `missing-traceability`.

- [ ] **Step 2: Run tests**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py
  ```

  Expected: FAIL on missing loader implementation.

- [ ] **Step 3: Implement loader**

  Add focused dataclasses or typed dictionaries for:

  - paper memory source.
  - collection memory source.
  - skipped paper.
  - build plan.

- [ ] **Step 4: Validate IDs**

  Ensure every block ID referenced by section and graph summaries exists in `source-map.json` or in `summary.json.blocks`.

- [ ] **Step 5: Run tests**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py
  ```

  Expected: PASS for discovery tests.

## Chunk 3: Collection Memory Build

### Task 3: Synthesize Collection Memory

**Files:**

- Modify: `src/paper_cli/ai/memory_build.py`
- Modify: `tests/test_ai_memory_build.py`

- [ ] **Step 1: Write fake-provider test**

  Fake provider returns collection JSON with paper IDs, themes, relations, and block IDs. Test that outputs preserve those IDs and write both `collection-memory.json` and `collection-memory.md`.

- [ ] **Step 2: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_writes_collection_memory
  ```

  Expected: FAIL because synthesis and writers do not exist.

- [ ] **Step 3: Implement compact prompt input builder**

  Include only:

  - metadata.
  - section summaries.
  - important block summaries.
  - graph nodes/edges.
  - source pointers.

- [ ] **Step 4: Implement provider call and validation**

  Validate returned paper IDs and block IDs against loaded sources before writing.

- [ ] **Step 5: Implement atomic JSON and Markdown writers**

  Write temp files in the target `_memory/` directory and replace targets atomically.

- [ ] **Step 6: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_writes_collection_memory
  ```

  Expected: PASS.

## Chunk 4: Library Memory Build

### Task 4: Synthesize Library Memory

**Files:**

- Modify: `src/paper_cli/ai/memory_build.py`
- Modify: `tests/test_ai_memory_build.py`

- [ ] **Step 1: Write fake-provider test**

  Build two collection memories, then synthesize `library-memory.json`, `library-memory.md`, and `collection-index.json`.

- [ ] **Step 2: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_writes_library_memory
  ```

  Expected: FAIL because library synthesis does not exist.

- [ ] **Step 3: Implement library prompt input**

  Use only collection summaries and collection-level themes; do not send all paper details.

- [ ] **Step 4: Implement library output writer**

  Write `_memory/library-memory.json`, `_memory/library-memory.md`, and `_memory/collection-index.json`.

- [ ] **Step 5: Run targeted test**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py::test_memory_build_writes_library_memory
  ```

  Expected: PASS.

## Chunk 5: Skip, Force, Stale, and Failure Semantics

### Task 5: Harden Operational Behavior

**Files:**

- Modify: `src/paper_cli/ai/memory_build.py`
- Modify: `tests/test_ai_memory_build.py`

- [ ] **Step 1: Write regression tests**

  Cover:

  - existing memory skipped by default.
  - `--force` overwrites memory.
  - changed summary hash reports stale.
  - provider failure does not leave partial output.
  - collection failure appears in `failed[]` with clear message.

- [ ] **Step 2: Run tests**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py
  ```

  Expected: FAIL on missing hardening behavior.

- [ ] **Step 3: Implement hash and staleness checks**

  Store canonical `summary.json` hashes in collection memory source metadata.

- [ ] **Step 4: Implement no-partial-output behavior**

  Validate provider JSON before any target file replace.

- [ ] **Step 5: Run tests**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py
  ```

  Expected: PASS.

## Chunk 6: Documentation and Full Verification

### Task 6: Update Docs and Validate

**Files:**

- Modify: `README.md`
- Modify: `TODO.md`
- Modify: `docs/zh/TODO.zh.md`
- Optional create: `docs/contracts/memory.md`
- Optional create: `docs/zh/contracts/memory.zh.md`

- [ ] **Step 1: Update README after implementation**

  Add `paper memory build` to command list and AI feature overview only after tests pass.

- [ ] **Step 2: Update TODO logs**

  Record implementation result, test commands, and any validation caveats.

- [ ] **Step 3: Run targeted tests**

  ```bash
  uv run --extra dev pytest -v tests/test_ai_memory_build.py tests/test_ai_extract_summary.py
  ```

  Expected: PASS.

- [ ] **Step 4: Run full verification**

  ```bash
  make verify
  ```

  Expected: PASS with ruff clean.

- [ ] **Step 5: Run smoke dry-run on existing library**

  ```bash
  uv run paper --root paper-libraries/full-smoke-library-optimized-v2 memory build --dry-run --json
  ```

  Expected: reports summarized papers, skipped missing summaries if any, and planned memory outputs without provider config.

- [ ] **Step 6: Run real-provider smoke build**

  ```bash
  set -a; source .env; set +a
  uv run paper --root paper-libraries/full-smoke-library-optimized-v2 memory build --json
  ```

  Expected: writes `_memory/library-memory.json`, `_memory/library-memory.md`, and collection-level memory files for summarized collections. Do not print secret values.

## Acceptance Criteria

- `paper memory build --dry-run --json` runs without provider config.
- Normal build fails early and clearly when provider config is missing.
- Missing paper summaries are skipped and reported; the command does not auto-run `paper extract summary`.
- Outputs preserve pointers to paper IDs, bundle paths, summary paths, source-map paths, section IDs, and block IDs.
- Existing memory outputs are skipped by default and overwritten only with `--force`.
- Stale source summary hashes are reported.
- Provider failures do not leave partial memory files.
- Fake-provider tests cover collection synthesis, library synthesis, skip behavior, stale behavior, and failure behavior.
- `make verify` passes after implementation.
- Real-provider smoke test succeeds on `paper-libraries/full-smoke-library-optimized-v2`.

## Follow-Up Ideas

- Add `paper memory status`.
- Add deterministic-only mode for cheap memory indexes.
- Add `--collection-workers` and `--max-requests` only if real libraries need collection-level concurrency.
- Add optional contract docs for `library-memory.json` and `collection-memory.json`.
- Add frontend reader integration where a memory item opens the corresponding paper, section, and source block.
