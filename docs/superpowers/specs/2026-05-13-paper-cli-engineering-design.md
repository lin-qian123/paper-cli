# paper-cli Engineering Design

Date: 2026-05-13

## Purpose

`paper-cli` has moved past the first MVP proof. It can import a local PDF, copy it into a bundle, convert it through MinerU, normalize Markdown and images, update metadata, rename the bundle, rebuild indexes, and pass `doctor`.

The next phase should make the project reliable enough for sustained development without turning it into a heavy platform. The goal is a small, explicit engineering foundation: stable file contracts, predictable CLI behavior, focused quality gates, and real-paper validation.

## Non-Goals

Do not build these in the engineering pass:

- A GUI.
- A database server.
- A plugin marketplace.
- A background daemon.
- A full search engine.
- A Rust rewrite.
- Zotero sync or bidirectional integration.
- A large framework around simple local file operations.

These may become useful later, but adding them now would obscure the core contract.

## Engineering Principles

1. Keep the product contract filesystem-first and language-neutral.
2. Keep Python as the implementation language for this phase.
3. Keep every feature reachable through the CLI.
4. Prefer plain files over hidden state.
5. Make agent-facing output structured and stable.
6. Add tooling only when it catches real mistakes.
7. Validate with real PDFs, but never commit user PDFs or MinerU outputs.
8. Treat future Rust work as a replacement or wrapper around stable contracts, not as an urgent rewrite.

## Stable Contracts

### Library Layout

The managed library keeps this shape:

```text
paper-library/
  paper-cli.yaml
  collections/
  inbox/
  indexes/
    papers.jsonl
    jobs.jsonl
```

Local development and manual validation libraries may live under:

```text
paper-libraries/
```

`paper-libraries/` is ignored by git because it can contain copied PDFs, extracted images, and MinerU raw output.

### Paper Bundle Layout

The bundle contract for newly converted papers should be:

```text
<paper-name>/
  paper.yaml
  original.pdf
  paper.md
  images/
  conversion.json
  raw/
    mineru/
      layout.json
      *_content_list.json
      *_origin.pdf
  notes/
    README.md
```

The root stays optimized for the common agent path: read `paper.yaml`, `paper.md`, and `images/`. Extractor-specific sidecars go under `raw/<converter>/`.

### Metadata Contract

`paper.yaml` remains the canonical paper record. The next schema refinement should add provenance without breaking the current fields:

```yaml
metadata:
  title: "..."
  creators:
    - name: "..."
      role: "author"
  year: 2026
  language: "en"
  doi: null
metadata_sources:
  title: "mineru"
  creators: "filename-title-prefix"
  year: "filename"
metadata_confidence:
  title: "high"
  creators: "medium"
  year: "medium"
```

This keeps the current simple metadata shape for callers while giving future importers and review queues enough information to avoid unsafe overwrites.

### CLI Contract

All user-facing commands should support `--json`. JSON output should be valid, stable, and suitable for agents. A command should return:

- `0` for success.
- `1` for validation failures found by `doctor`.
- `2` or argparse default behavior for invalid CLI usage.
- Non-zero for unexpected runtime errors.

The next engineering pass should document the JSON schema for each command before adding more commands.

## Minimal Quality Tooling

Add only lightweight local gates:

- `pytest` for tests.
- `ruff` for linting and formatting.
- Optional `mypy` later, only after types stop slowing iteration.
- A `Makefile` or small `justfile` only if repeated commands become annoying.

Recommended first commands:

```bash
uv run --with pytest pytest -v
uv run --with ruff ruff check src tests
uv run --with ruff ruff format src tests
```

Avoid a complex CI matrix until there is a remote repository and real release target.

## Conversion Workflow

The current conversion path is enough for MVP, but the engineering version should separate it into explicit stages:

1. Discover pending bundles.
2. Create or update a conversion job record.
3. Submit PDF to converter.
4. Poll and download output.
5. Normalize output into bundle contract.
6. Extract metadata.
7. Rename bundle if allowed.
8. Rebuild indexes.
9. Persist success or failure details.

`conversion.json` should grow from a small status file into a useful diagnostic record:

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "submitted_at": "...",
  "converted_at": "...",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

This is still local and simple. It does not require a daemon or database.

## Indexes

Keep JSONL indexes for now:

- `indexes/papers.jsonl`: rebuildable paper summary rows.
- `indexes/jobs.jsonl`: append-only job history when conversion jobs become explicit.

Do not add SQLite until one of these is true:

- JSONL search is too slow for a real library.
- Query requirements become richer than simple scans.
- Multiple commands need transactional updates.

## Testing Strategy

Keep tests layered:

- Unit tests: naming, metadata parsing, schema helpers.
- Workflow tests: import, convert with fixture output, index rebuild, doctor.
- Mocked network tests: MinerU API shape, zip normalization, sidecar handling.
- Manual smoke tests: real MinerU conversion using local PDFs under `paper-libraries/`.

Do not commit real user PDFs or extracted outputs. Record smoke-test results in `TODO.md`.

## Next Engineering Milestones

### Milestone 1: Baseline And Tooling

- Commit the current verified MVP baseline.
- Add `ruff` configuration.
- Add a single documented verification command.
- Keep all tests green.

### Milestone 2: Contract Documentation

- Document `paper.yaml`.
- Document `conversion.json`.
- Document CLI JSON output for implemented commands.
- Add a short manual MinerU smoke-test checklist.

### Milestone 3: Conversion Job Hardening

- Expand `conversion.json`.
- Append conversion events to `indexes/jobs.jsonl`.
- Preserve failure diagnostics.
- Add retry behavior for failed conversions.

### Milestone 4: Metadata Provenance

- Add metadata source and confidence fields.
- Make post-conversion overwrites depend on confidence.
- Keep user or locked metadata protected.

### Milestone 5: Adapter Boundary

- Define a source adapter interface.
- Keep local-folder import as the reference adapter.
- Add Zotero read-only import only after the interface is clear.

## Decision

Proceed incrementally. The next implementation plan should cover only Milestones 1 and 2 first. Milestones 3-5 should remain designed but not started until the contracts and tooling are in place.
