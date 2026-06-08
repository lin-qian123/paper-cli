# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog style, and this project uses semantic versioning for tagged releases.

## [0.1.0] - 2026-06-08

### Added

- Local-first paper library initialization, local PDF import, metadata-first bundle naming, and stable paper IDs.
- Self-contained paper bundles with `original.pdf`, `paper.yaml`, `paper.md`, `images/`, `conversion.json`, notes, backups, and indexes.
- MinerU conversion backends:
  - serial `mineru-api`;
  - batch `mineru-api-batch`;
  - local CLI `mineru-local`;
  - `local-fixture` for tests and dry runs.
- `mineru-api-batch` upload/download concurrency, batch polling, running-batch resume, retry/backoff, wait limits, and long-PDF splitting into 195-page parts.
- `paper doctor --strict` diagnostics for conversion state, batch mappings, stale running conversions, local MinerU setup, and AI provider setup.
- Agent-facing lookup commands: `resolve`, `get`, and `inspect`.
- `paper repair` for conservative AI metadata repair and low-risk Markdown extraction repair.
- `paper extract summary` for block summaries, section skeletons, lightweight graph extraction, and source-map traceability.
- `paper memory build` for collection-level and library-level memory from existing summary outputs.
- JSON output contracts for CLI commands and bundle artifacts.
- Repeatable QED corpus validation helper.

### Changed

- Split long PDF conversions keep existing metadata and leave uncertain title/author cleanup to AI metadata repair.
- Metadata extraction from MinerU title pages is intentionally conservative to avoid writing ambiguous author candidates into `paper.yaml`.

### Validation

- `uv run --extra dev pytest -q`: 140 tests passed.
- `uv run --extra dev ruff check src tests`: clean.
- QED `mineru-api-batch` validation on 519 PDFs converted 516 before long-PDF splitting; the remaining 3 were over MinerU API's 200-page limit.
- Targeted long-PDF split validation converted those 3 long PDFs successfully with strict doctor clean.

### Known Limitations

- Zotero, BibTeX, CSL JSON, attachment resolver, full-text search, and review queues are planned for later releases.
- Split long-PDF interruption resume/reporting can be improved.
- AI commands depend on the configured OpenAI-compatible provider and should not be used with sensitive documents unless the provider privacy boundary is acceptable.
