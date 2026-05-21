# TODO

## Current Phase

Local-folder MVP implemented and covered by tests. The first built-in AI repair pass is implemented for OpenAI-compatible providers; next work should validate real-provider behavior and harden edge cases before expanding source adapters.

## Engineering Phase

- [x] Commit the verified MVP hardening baseline.
- [x] Write engineering design for a lightweight, non-redundant project foundation.
- [x] Add minimal lint/format tooling.
- [x] Document `paper.yaml`, `conversion.json`, and CLI JSON output contracts.
- [x] Add a manual real-MinerU smoke-test checklist.
- [x] Add implementation plan for engineering milestones 1 and 2.
- [x] Expand `conversion.json` into a diagnostic record.
- [x] Append conversion job events to `indexes/jobs.jsonl`.
- [x] Preserve failed conversion diagnostics and retry failed bundles with incremented attempts.
- [x] Add metadata source and confidence fields to `paper.yaml`.
- [x] Merge conversion metadata by confidence to protect high-confidence fields.
- [x] Define source adapter interface and make local-folder import the reference adapter.
- [x] Write the approved AI repair design for `paper repair`.

## AI Repair Phase

- [x] Implement `paper repair` with default `--target all`.
- [x] Add `--target metadata`, `--target markdown`, and `--dry-run`.
- [x] Add an OpenAI-compatible provider configured by environment variables and optional `paper-cli.yaml` settings.
- [x] Build bounded metadata evidence packets from `paper.yaml`, bundle name, PDF filename, conversion state, and the Markdown head.
- [x] Apply safe metadata repairs with `metadata_sources=ai-repair` and confidence-aware merge rules.
- [x] Split `paper.md` into blocks and send only suspicious blocks to AI for repair.
- [x] Create per-bundle backups before writing `paper.yaml` or `paper.md`.
- [x] Write `repair.json` with applied changes, warnings, provider, model, and timestamps.
- [x] Add fake-provider tests for provider errors, invalid JSON, dry-run behavior, metadata repair, Markdown block patching, and backup creation.
- [x] Add a manual real-provider smoke-test checklist under `docs/smoke-tests/`.
- [ ] Run a real-provider AI repair smoke test on a converted non-sensitive PDF.
- [ ] Add an optional bundle selector for targeted repair after library-wide behavior is validated.
- [ ] Decide whether repair history should stay latest-only or become append-only JSONL.
- [x] Fix `paper repair --target all` so a later Markdown provider failure cannot leave metadata half-written for the same bundle.
- [x] Write a development record for suspicious-block weaknesses and implement conservative reason/policy classification.
- [ ] Aggregate verbose `review_only` Markdown warnings by reason/count while keeping detailed block IDs available.
- [ ] Add a future review/apply path for long prose OCR candidates that are currently `review_only`.

## Validation Log

- 2026-05-13: Tested the desktop PDF `Advanced Science - 2026 - Guo - Helical Electron Beam Micro-Bunching by High-Order Modes in a Micro-Plasma Waveguide.pdf` in a temporary library under `/tmp`.
  - Import succeeded and copied the PDF into an inbox bundle.
  - Real MinerU conversion succeeded with `MINERU_API_KEY`.
  - `paper.md`, `images/`, `paper.yaml`, `conversion.json`, and JSONL indexes were created.
  - `paper status --json` reported `total=1`, `converted=1`, `failed=0`, `pending=0`.
  - `paper doctor --json` reported no issues.
  - MinerU output contained 266 Markdown lines and 17 extracted images.
  - Known issue: fast filename metadata parsed `Advanced Science` as the creator, and post-conversion metadata did not reliably correct the author field from this real MinerU Markdown.
  - Known issue: MinerU raw sidecar files such as `layout.json`, `*_content_list.json`, and `*_origin.pdf` currently remain in the bundle root instead of a dedicated raw-output directory.
- 2026-05-13 follow-up fix:
  - Added title-prefix creator inference for cases like `Journal - Year - Author - Title.pdf` when MinerU provides the clean title.
  - Added dash normalization so Unicode dash variants in PDF filenames still match ASCII dashes in MinerU Markdown titles.
  - Added MinerU sidecar normalization into `raw/mineru/` for mocked ZIP outputs.
  - Replayed the desktop PDF through the existing MinerU output as a fixture; the bundle now renames to `Guo et al. - 2026 - Helical Electron Beam Micro-Bunching by High-Order Modes in a Micro-Plasma Waveguide`.
  - Re-ran real MinerU conversion inside `paper-libraries/desktop-live-test`; `paper status` and `paper doctor` passed, the bundle used `Guo et al.` naming, and MinerU sidecars were stored under `raw/mineru/`.
- 2026-05-13 provenance smoke test:
  - Re-ran real MinerU conversion inside `paper-libraries/provenance-live-test` after adding metadata provenance and conversion job diagnostics.
  - `paper status` reported `converted=1`, `failed=0`, `pending=0`; `paper doctor` reported no issues.
  - `paper.yaml` included `metadata_sources` and `metadata_confidence`: title from `mineru` with `high`, creators from `filename-title-prefix` with `medium`, year from `filename` with `medium`.
  - `conversion.json` used diagnostic schema version 1 with `converter=mineru`, `state=done`, `attempt=1`, `raw_output_dir=raw/mineru`, `markdown=paper.md`, and `images=images`.
  - `indexes/jobs.jsonl` recorded `conversion-started` and `conversion-finished` events.
- 2026-05-21 AI repair implementation:
  - Added `paper repair` with `--target metadata|markdown|all`, `--dry-run`, and `--json`.
  - Added OpenAI-compatible chat completions provider configuration from `PAPER_AI_*` or `paper-cli.yaml` with secrets read from environment variables only.
  - Metadata repair uses bounded evidence from `paper.yaml`, bundle name, source filename, conversion state, identifier candidates, and Markdown head; safe applied changes mark `metadata_sources` as `ai-repair`.
  - Markdown repair splits `paper.md` into blocks, sends only suspicious blocks, applies exact-match patches, and records skipped mismatches as warnings.
  - Applied runs create bundle-local backups, write latest-only `repair.json`, and rebuild `indexes/papers.jsonl`.
  - Added fake-provider tests for config, request payloads, invalid JSON, missing config, dry-run behavior, metadata protection, Markdown patching, mismatch rejection, backup creation, and index rebuild.
- 2026-05-21 dual-modality paper full smoke test:
  - Copied all 12 PDFs from `/Users/yuxiangzhang/Documents/research/paper/双模照相` into ignored test input `paper-libraries/full-smoke-input/双模照相`.
  - Imported the copied folder into `paper-libraries/full-smoke-library-clean` under collection `双模照相`; duplicate PDF hashes collapsed to 7 unique paper bundles.
  - Real MinerU conversion completed for all 7 bundles: `status` reported `converted=7`, `failed=0`, `pending=0`; `doctor` reported no issues.
  - Verified each converted bundle contains `original.pdf`, `paper.md`, `images/`, `raw/mineru/`, `conversion.json`, and `notes/README.md`; `jobs.jsonl` had 14 start/finish events and `papers.jsonl` had 7 rows.
  - `paper repair --target metadata --dry-run --json` with the configured OpenAI-compatible provider returned `ok=true` and wrote no `repair.json` files.
  - `paper repair --json` then completed for all 7 bundles with `failed=[]`; it wrote 7 `repair.json` files, created 12 backup files only for changed files, and `status` / `doctor` remained clean.
  - During the first full repair attempt, one provider response ended prematurely after metadata had already been written but before `repair.json`; added a regression test and changed repair orchestration to collect all selected target results before writing bundle files.
- 2026-05-21 suspicious-block optimization:
  - Added `docs/development/2026-05-21-ai-repair-suspicious-blocks.md` documenting current weaknesses, policy design, and validation results.
  - Added structured suspicious findings with `reasons` and `policy`: `auto_repair`, `review_only`, and `structural_warning`.
  - Markdown repair now sends only `auto_repair` blocks to AI; formula/table/reference/math-heavy blocks are recorded as `review_only` warnings instead of being auto-repaired.
  - Added detection for HTML tables, reference sections, common OCR words, repeated phrases, broken images, and long OCR paragraphs that should not be auto-sent.
  - `make verify` passed with 51 tests.
  - Real-provider retest on `paper-libraries/full-smoke-library-optimized-v2` completed with `failed=[]`; compared with the previous clean run, patch mismatch warnings fell from 3 to 1 and protected-block warnings fell from 4 to 0, while risky math/formula findings became explicit `review_only` records.

## Approved MVP

- [x] Define project as an agent-native local literature management CLI.
- [x] Choose local-folder import as the first source adapter.
- [x] Default to copying PDFs into each paper bundle.
- [x] Use metadata-first naming with user-configurable templates.
- [x] Import first, then automatically rename after MinerU conversion improves metadata.
- [x] Defer Zotero and Attanger support to phase 2.
- [x] Create Chinese documentation under `docs/zh/`.
- [x] Review and approve the written MVP spec.
- [x] Create an implementation plan after spec approval.
- [x] Clarify technology route: Python MVP, Rust as later large-scale candidate, language-neutral file/CLI contracts.
- [x] Confirm implementation defaults: current repository only, copy PDFs into bundles, MinerU API from environment, JSON output for main commands, hash-based duplicate skipping, no delete command in MVP.
- [x] Execute the MVP implementation plan.

## Implementation Backlog

- [x] Initialize Python project structure.
- [x] Choose packaging and CLI framework.
- [x] Implement `paper init`.
- [x] Implement library config loading from `paper-cli.yaml`.
- [x] Implement local PDF scanner.
- [x] Implement PDF copying into paper bundles.
- [x] Implement stable paper ID generation.
- [x] Implement fast metadata extraction.
- [x] Implement configurable naming renderer.
- [x] Implement filesystem-safe name sanitization and duplicate handling.
- [x] Implement MinerU conversion adapter.
- [x] Persist `conversion.json`.
- [x] Persist `paper.yaml`.
- [x] Implement post-conversion metadata refinement.
- [x] Implement automatic bundle rename with rename history.
- [x] Implement index rebuild.
- [x] Implement `paper list`.
- [x] Implement `paper status`.
- [x] Implement `paper doctor`.
- [x] Add focused tests for naming, bundle layout, import idempotency, and rename behavior.

## Phase 2 Ideas

- [ ] Evaluate a Rust CLI/core after the paper bundle and CLI contracts stabilize.
- [ ] Zotero read-only import adapter.
- [ ] Attachment resolver abstraction.
- [ ] Attanger-style attachment-root mapping.
- [ ] BibTeX / CSL JSON import.
- [ ] Agent classification based on converted Markdown.
- [ ] Review queue for ambiguous classification or naming.
- [ ] Search and retrieval over converted Markdown.

## Robustness Backlog

- [x] Improve post-conversion author inference for `Journal - Year - Author - Title.pdf` filenames when MinerU provides the clean title.
- [ ] Improve direct author extraction from MinerU Markdown title pages when no explicit `Authors:` line exists and filename inference is unavailable.
- [x] Mark low-confidence metadata from filename parsing so conversion-time metadata can override it more aggressively.
- [x] Normalize MinerU raw sidecar files into a dedicated raw-output directory for newly converted bundles.
- [x] Add a real-MinerU smoke-test checklist that can be run manually without committing user PDFs.

## Remaining Decisions

- MVP implementation language is Python; revisit Rust for larger post-MVP development after contracts stabilize.
- The current MinerU integration uses a clean in-project client. Validate it against real papers before deciding whether any workflow from older scripts should be reused.
- The current pre-conversion metadata pass is intentionally lightweight. Revisit only after real-paper validation shows concrete naming or classification gaps.
- MVP indexes remain JSONL. Revisit SQLite only when search, filtering, or larger-library performance needs justify it.

## Implementation Plan

- `.agents/superpowers/specs/2026-05-13-paper-cli-mvp-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-engineering-m1-m2-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-conversion-jobs-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-metadata-provenance-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-source-adapters-implementation.md`
- `docs/superpowers/specs/2026-05-21-paper-cli-ai-repair-design.md`
