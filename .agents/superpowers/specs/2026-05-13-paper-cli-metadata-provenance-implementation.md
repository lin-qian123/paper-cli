# paper-cli Metadata Provenance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add metadata provenance and confidence to `paper.yaml` so filename, PDF metadata, MinerU, inferred authors, and future adapters can merge metadata without unsafe overwrites.

**Architecture:** Keep the existing `metadata` object stable for callers. Add sibling dictionaries `metadata_sources` and `metadata_confidence` on `PaperRecord`. Merge metadata by confidence rank during conversion; preserve higher-confidence existing values.

**Tech Stack:** Python 3.11, YAML, pytest, existing metadata/import/convert modules.

---

## File Structure

- Modify `src/paper_cli/models.py`: add `metadata_sources` and `metadata_confidence` to `PaperRecord`.
- Modify `src/paper_cli/metadata.py`: expose `fast_metadata_details()` returning metadata, sources, and confidence.
- Modify `src/paper_cli/importer.py`: persist import-time metadata provenance.
- Modify `src/paper_cli/convert.py`: merge conversion metadata with provenance and confidence rules.
- Modify `src/paper_cli/indexes.py`: include provenance summaries in `papers.jsonl`.
- Modify tests in `tests/test_importer.py`, `tests/test_metadata.py`, `tests/test_convert.py`, and `tests/test_indexes.py`.
- Update `docs/contracts/paper-yaml.md` and `docs/zh/contracts/paper-yaml.zh.md`.
- Update `TODO.md` and `docs/zh/TODO.zh.md`.

## Chunk 1: Model And Import Provenance

- [x] Add failing tests for `PaperRecord` round-trip with `metadata_sources` and `metadata_confidence`.
- [x] Add failing tests for filename/PDF fast metadata provenance.
- [x] Implement model fields and `fast_metadata_details()`.
- [x] Persist provenance during local import.

## Chunk 2: Conversion Merge Rules

- [x] Add failing conversion test asserting MinerU title gets high confidence and inferred creator gets medium confidence.
- [x] Add failing conversion test asserting existing high-confidence creator is not overwritten by lower-confidence inferred creator.
- [x] Implement confidence-ranked metadata merge.

## Chunk 3: Index And Docs

- [x] Include metadata provenance in `papers.jsonl`.
- [x] Update English and Chinese `paper.yaml` contract docs from planned to current.
- [x] Update TODO and run `make verify`.
- [x] Commit as `feat: add metadata provenance`.
