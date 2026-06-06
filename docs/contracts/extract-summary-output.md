# `extract summary` Output Contracts

This document defines the artifact contracts written by `paper extract summary`:

- `extracts/summary/summary.json`
- `extracts/summary/source-map.json`

## `summary.json`

Top-level shape:

```json
{
  "schema_version": 1,
  "paper_id": "sha256:...",
  "generated_at": "2026-06-06T00:00:00+00:00",
  "provider": "openai-compatible",
  "model": "gpt-5-mini",
  "source": {
    "markdown": "paper.md",
    "markdown_hash": "sha256:..."
  },
  "blocks": [],
  "sections": [],
  "graph": {
    "nodes": [],
    "edges": []
  },
  "indexes": {},
  "warnings": []
}
```

`blocks[]` entries:

```json
{
  "block_id": "blk_000000",
  "source_ref": {
    "start_line": 10,
    "end_line": 12,
    "text_hash": "sha256:...",
    "excerpt": "..."
  },
  "display": {
    "order": 3,
    "section_id": "sec_0001",
    "section_path": ["Introduction"]
  },
  "summary": {
    "summary_text": "...",
    "summary_level": "high",
    "key_points": ["..."],
    "role": "result",
    "importance": "medium",
    "concepts": ["..."]
  }
}
```

`sections[]` entries:

```json
{
  "section_id": "sec_0001",
  "heading": "Introduction",
  "section_path": ["Introduction"],
  "block_ids": ["blk_000000"],
  "summary": "...",
  "key_points": ["..."],
  "role": "other"
}
```

`graph.nodes[]` entries:

```json
{
  "id": "n1",
  "type": "concept",
  "label": "...",
  "source_block_ids": ["blk_000000"]
}
```

`graph.edges[]` entries:

```json
{
  "source": "n1",
  "target": "n2",
  "type": "supports",
  "label": "...",
  "confidence": "medium",
  "source_block_ids": ["blk_000001"]
}
```

Notes:

- `paper_id`, `block_id`, and `section_id` are the stable traceability anchors for later reading UIs and memory layers.
- `source.markdown_hash` must match the `markdown_hash` written to `source-map.json`.
- `warnings[]` records normalization, retry, or provider-side issues that did not block output generation.
- `indexes` is a derived convenience surface and must stay internally consistent with `blocks` and `sections`.

## `source-map.json`

Top-level shape:

```json
{
  "schema_version": 1,
  "markdown": "paper.md",
  "markdown_hash": "sha256:...",
  "blocks": []
}
```

`blocks[]` entries:

```json
{
  "block_id": "blk_000000",
  "type": "paragraph",
  "summary_policy": "summarize",
  "skip_reason": null,
  "start_line": 10,
  "end_line": 12,
  "section_id": "sec_0001",
  "section_path": ["Introduction"],
  "order": 3,
  "text_hash": "sha256:...",
  "text": "..."
}
```

Notes:

- `text_hash` is computed from the exact block text.
- `summary_policy` is one of `summarize`, `skip`, or `context_only`.
- `skip_reason` is populated when a block is not summarized.
- `section_path` preserves the heading stack active for the block at extraction time.
