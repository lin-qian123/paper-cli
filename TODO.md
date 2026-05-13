# TODO

## Current Phase

Local-folder MVP implemented and covered by tests. Engineering work should first stabilize contracts and tooling without adding unnecessary platform complexity.

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
- [ ] Mark low-confidence metadata from filename parsing so conversion-time metadata can override it more aggressively.
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
