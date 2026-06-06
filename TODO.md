# TODO

## Current Phase

Local-folder MVP implemented and covered by tests. The first built-in AI repair phase is closed for now: OpenAI-compatible metadata repair, conservative Markdown repair, backups, `repair.json`, real-provider smoke tests, and suspicious-block hardening are implemented and verified. The second built-in AI layer, `paper extract summary`, is now implemented for structured article-skeleton extraction: block summaries, section summaries, lightweight graph extraction, and source traceability outputs under `extracts/summary/`. The third built-in AI layer, `paper memory build`, is now implemented for collection-level and library-level agent memory from existing summary outputs, with stale tracking and automatic refresh after successful summary extraction.

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
- [x] Write the MinerU conversion backends plan for cloud batch conversion and local MinerU CLI conversion.
- [x] Implement `mineru-api-batch` with bounded batch size, upload/download concurrency, polling, and resume.
- [x] Implement `mineru-local` as a local CLI backend that normalizes output into the existing bundle contract.
- [x] Re-run QED random-30 or larger corpus validation after the new conversion backends land.
- [x] Write the run-manifest design for a future paper research plugin that keeps literature discovery in agent skills while using `paper-cli` for import, conversion, and summary extraction.
- [ ] Execute the MinerU productization plan for local environment management, deterministic metadata extraction, cloud batch validation, shared normalization, local concurrency auto-tuning, and scripted QED validation.

## AI Repair Phase

Status: phase-complete for now. Remaining unchecked items are follow-up enhancements, not blockers for the current AI repair milestone.

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
- [x] Run a real-provider AI repair smoke test on a converted non-sensitive PDF.
- [x] Add an optional bundle selector for targeted repair after library-wide behavior is validated.
- [x] Decide whether repair history should stay latest-only or become append-only JSONL.
- [x] Fix `paper repair --target all` so a later Markdown provider failure cannot leave metadata half-written for the same bundle.
- [x] Write a development record for suspicious-block weaknesses and implement conservative reason/policy classification.
- [x] Aggregate verbose `review_only` Markdown warnings by reason/count while keeping detailed block IDs available.
- [x] Add a future review/apply path for long prose OCR candidates that are currently `review_only`.

## AI Extract Summary Phase

Status: first implementation complete and smoke-tested on `paper-libraries/full-smoke-library-optimized-v2`.

- [x] Confirm command family as `paper extract`, with first capability `paper extract summary`.
- [x] Choose a layered extraction pipeline: block-level concurrent summaries, section-level aggregation, and graph-level extraction.
- [x] Confirm CLI-internal provider concurrency instead of Codex/external subagent dependency.
- [x] Confirm output location: `extracts/summary/summary.json`, `extracts/summary/summary.md`, and `extracts/summary/source-map.json`.
- [x] Confirm default skip behavior for existing summary output, with `--force` for regeneration.
- [x] Confirm UI-oriented traceability through stable `block_id`, source line ranges, text hashes, section paths, and `source-map.json`.
- [x] Confirm summary length should be content-dependent, not limited to one sentence.
- [x] Confirm first-pass block policy: summarize main prose/captions; skip references, footnotes, funding, copyright/license, headers/footers, page numbers, OCR noise, pure formulas, pure tables, and pure images.
- [x] Record design in `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`.
- [x] Implement target selection: `--paper`, `--collection`, `--limit`, `--workers`, `--paper-workers`, `--max-requests`, `--retries`, `--force`, `--dry-run`, and `--json`.
- [x] Implement summary-specific block classification and source-map generation.
- [x] Implement block-batch worker calls with CLI-internal concurrency.
- [x] Implement section aggregation and conservative graph extraction.
- [x] Implement missing-block-summary retry so provider omissions do not silently break frontend alignment.
- [x] Implement fake-provider tests for block workers, section aggregation, graph extraction, skip behavior, and traceability.
- [x] Run a real-provider smoke test on converted non-sensitive papers.
- [x] Add a dedicated contract document for `extracts/summary/summary.json` and `source-map.json`.
- [x] Consider a cheaper graph mode or `--no-graph` option if real-provider runs are too slow for large libraries.

## AI Memory Build Phase

Status: first implementation complete and unit-tested. The implementation plan is `docs/superpowers/specs/2026-06-05-paper-cli-memory-build-design.md`.

- [x] Confirm `paper memory build` should consume existing `paper extract summary` outputs only.
- [x] Confirm missing `extracts/summary/summary.json` should be skipped and reported, not auto-generated.
- [x] Confirm hierarchy: per-paper summaries remain the bottom layer, collection memories form the middle layer, and library memory forms the top layer.
- [x] Confirm progressive-disclosure traceability through paper IDs, bundle paths, summary paths, source-map paths, section IDs, and block IDs.
- [x] Write the implementation plan for `paper memory build`.
- [x] Implement `paper memory build --dry-run --json` without requiring provider config.
- [x] Implement summary/source-map discovery, validation, missing-summary skipping, and stale-source hash reporting.
- [x] Implement collection-level memory synthesis and `_memory/collection-memory.json` / `_memory/collection-memory.md` / `_memory/paper-index.json` outputs.
- [x] Implement library-level memory synthesis and `_memory/library-memory.json` / `_memory/library-memory.md` / `_memory/collection-index.json` outputs.
- [x] Add fake-provider tests for dry-run, skip behavior, force overwrite, stale detection, ID validation, provider failures, and atomic writes.
- [x] Run real-provider smoke test on `paper-libraries/full-smoke-library-optimized-v2` after implementation.
- [x] Track memory stale state in `indexes/memory-state.json`.
- [x] Mark memory stale after `import`, `convert`, and successful non-dry-run `repair` changes.
- [x] Auto-refresh affected collection and library memory after successful non-dry-run `extract summary`.

## MinerU Productization Phase

Status: implementation complete except for real large-scale cloud batch validation. The implementation plan is `docs/superpowers/specs/2026-05-26-paper-cli-mineru-productization-plan.md`.

- [x] Productize local MinerU environment management with config-driven executable resolution and strict doctor diagnostics.
- [x] Improve deterministic MinerU metadata extraction from converted Markdown and local evidence before falling back to AI repair.
- [ ] Run real large-scale `mineru-api-batch` validation when network conditions are stable.
- [x] Extract shared MinerU output normalization for serial API, batch API, and local CLI outputs.
- [x] Add conservative local MinerU concurrency auto-tuning with explicit CLI/config precedence.
- [x] Script the QED validation workflow so random sampling, import, conversion, doctor, artifact counts, and report generation are repeatable.
- [x] Harden the agent-facing CLI surface with clearer help, `resolve` / `get` / `inspect`, `convert --dry-run`, and richer `doctor --json` setup diagnostics.

## Validation Log

- 2026-06-06 repair targeting and extract-summary contract docs:
  - Added `paper repair --paper`, `--collection`, and `--limit` so targeted repair can reuse the same bundle-selection style as `extract summary`.
  - Added per-bundle `markdown_warning_summary` aggregation in CLI output and in `repair.json`, while keeping detailed warning strings and block IDs.
  - Added `docs/contracts/extract-summary-output.md` to document the `extracts/summary/summary.json` and `source-map.json` artifact contracts.
  - Added fake-provider tests for repair selector scoping and warning-summary emission in `tests/test_ai_repair.py`.
  - Verification not run in this pass.

- 2026-06-06 repair-history and graph-mode product decisions:
  - Decided that `repair.json` remains `latest-only`; append-only JSONL history is not part of the current product boundary.
  - Decided not to add `extract summary --no-graph` or a cheaper graph mode in the current release line; the default graph extraction remains the only built-in mode.
  - Verification not run in this pass.

- 2026-06-06 long-prose OCR handling decision:
  - Decided that long prose OCR candidates currently classified as `review_only` stay warning-only in the current product line.
  - No separate review/apply workflow will be added for this release line unless a later product decision reopens it.
  - Verification not run in this pass.

- 2026-06-06 AI memory auto-refresh and stale tracking:
  - Added `indexes/memory-state.json` to persist paper/collection/library stale state.
  - `import`, `convert`, and successful non-dry-run `repair` now mark affected memory stale instead of rebuilding memory immediately.
  - Successful non-dry-run `extract summary` now automatically refreshes the affected collection and library memory using the same provider, and clears stale state on success.
  - Added unit coverage for import stale marking, summary-triggered auto refresh, and repair-triggered stale marking.
  - Targeted verification passed: `uv run --extra dev pytest -v tests/test_ai_extract_summary.py tests/test_ai_memory_build.py tests/test_ai_repair.py`.
  - Real-provider incremental smoke test passed on `paper-libraries/full-smoke-library-optimized-v2`: `extract summary --paper sha256:f0a5909f --force --json` re-extracted 1 paper and returned `memory_refresh.ok=true` with fresh collection/library writes; `indexes/memory-state.json` ended with `library.stale=false`.

- 2026-06-05 AI memory build real-provider smoke test:
  - `memory build --dry-run --json` on `paper-libraries/full-smoke-library-optimized-v2` planned 1 collection memory and 1 library memory output, with `paper_count=5`, `skipped_paper_count=0`, and `stale=false`.
  - Real provider `memory build --json` passed on `paper-libraries/full-smoke-library-optimized-v2`; it wrote `collections/双模照相/_memory/collection-memory.json`, `collection-memory.md`, `paper-index.json`, and library-root `_memory/library-memory.json`, `library-memory.md`, `collection-index.json`.
  - After a compatibility fix for provider-returned collection paths, the final `library-memory.json` contained `warnings=[]`, one collection entry for `双模照相`, and a top-level `global_themes` list grounded in source paper IDs.

- 2026-06-05 AI memory build implementation:
  - Added `paper memory build` with `--collection`, `--limit`, `--force`, `--dry-run`, and `--json`.
  - Added `src/paper_cli/ai/memory_build.py` to discover existing `extracts/summary/summary.json` inputs, validate traceability, build deterministic paper-level memory, synthesize collection/library memory through the OpenAI-compatible provider, and write `_memory/` outputs atomically.
  - Implemented default skip behavior for existing collection/library memory outputs and stale detection based on summary hashes.
  - Added fake-provider tests covering dry-run without provider config, collection/library writes, stale detection, force rebuild, provider failure without partial output, and missing-provider CLI failure.
  - Targeted verification passed: `uv run --extra dev pytest -v tests/test_ai_extract_summary.py tests/test_ai_memory_build.py`.

- 2026-06-05 AI memory build planning:
  - Confirmed `paper memory build` should build hierarchical agent memory from existing `paper extract summary` outputs.
  - Confirmed missing `summary.json` is skipped and reported; the command must not auto-run summary extraction.
  - Planned output layers: per-paper summaries stay under `extracts/summary/`, collection memories live under collection `_memory/`, and library memory lives under library-root `_memory/`.
  - Planned traceability contract: memory items should preserve paper IDs, bundle paths, summary paths, source-map paths, section IDs, and source block IDs for later frontend paragraph-summary alignment.
  - Recorded the implementation plan in `docs/superpowers/specs/2026-06-05-paper-cli-memory-build-design.md`; implementation has not started.

- 2026-05-28 CLI surface hardening:
  - Changed argparse help to present the executable as `paper` and added descriptions for important agent-facing flags.
  - Added read-only `paper resolve`, `paper get`, and `paper inspect` commands for stable bundle lookup and artifact inspection by ID prefix, name/title fragment, relative path, absolute bundle path, or file path inside a bundle.
  - Added `paper convert --pending --dry-run --json` to report the effective converter, batch size, jobs, pending bundles, setup diagnostics, and planned write targets without contacting MinerU or writing bundle files.
  - Extended `paper doctor --json` with non-secret diagnostics for library/config presence, MinerU API key availability, local MinerU executable configuration, and AI provider configuration availability.
  - Added `missing-library-config` as a doctor issue when a target directory has not been initialized with `paper init`.
  - Updated `README.md`, `docs/contracts/cli-json.md`, and `docs/zh/contracts/cli-json.zh.md` for the new command surface and JSON shapes.
  - Targeted verification passed: `uv run --extra dev pytest -v tests/test_cli_papers.py tests/test_doctor.py tests/test_config.py`.

- 2026-05-26 MinerU productization implementation and validation:
  - Added config-driven local MinerU settings under `mineru` in `paper-cli.yaml`: `executable`, `local_backend`, `local_jobs`, and `max_wait_seconds`.
  - Added local MinerU environment resolution and strict doctor diagnostics for configured missing or invalid executables.
  - Added shared MinerU output normalization for serial API ZIP output, batch API ZIP output, and local CLI output.
  - Added deterministic MinerU metadata extraction for explicit `Authors:` / `Year:` lines, title-page author lines, DOI, arXiv ID, language, and journal-label title rejection.
  - Added conservative local jobs auto-tuning; `auto` resolves to one local MinerU process unless CLI/config explicitly overrides it.
  - Added `paper validate qed` to script deterministic QED sampling, symlink input creation, import, optional conversion, doctor checks, artifact counts, and Markdown report generation.
  - `make verify` passed with 114 tests and ruff clean.
  - Dry QED validation under `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-productization-dry-20260526` passed with `--no-convert`, 3 sampled/imported papers, and report `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-productization-dry-20260526-test-report.md`.
  - Full local MinerU validation under `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-productization-20260526` used MinerU 3.1.15 from `/Volumes/PHILIPS/programs/mineru/.venv/bin`, `--converter mineru-local --local-backend pipeline --batch-size 1 --jobs 1`.
  - Final validation result: `sampled=30`, `imported=30`, `converted=30`, `failed=0`, `pending=0`, `incomplete_metadata=0`, `renamed=20`, strict doctor issues `[]`.
  - Artifact counts were 30 bundles, 30 `paper.md`, 30 `images/`, 30 `raw/mineru`, and 30 `conversion.json`.
  - Naming anomaly scan for separators, replacement characters, private-use glyphs, `SCIENTIFIC REPORTS`, and repeated spaces returned no matches.
  - Full validation report: `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-productization-20260526-test-report.md`.

- 2026-05-25: Deleted the previous `/Volumes/PHILIPS/programs/paper-cache/paper-cli-*` test directories and reran a fresh QED random-30 validation under `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-retest-20260525`.
  - Sample source list: `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-retest-20260525-sample-list.txt`; symlink input folder: `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-retest-20260525-sample-input`.
  - `make verify` passed after adding private-use Unicode cleanup for imported/converted metadata and bundle names: 91 tests passed and ruff reported no issues.
  - `paper init`, `paper import`, duplicate import, `paper list --json`, pre-conversion `paper status --json`, and `paper doctor --json` passed.
  - Local MinerU conversion used `/Volumes/PHILIPS/programs/mineru/.venv/bin` on `PATH` with `--converter mineru-local --local-backend pipeline --batch-size 1 --jobs 1`.
  - Final 30-paper status: `total=30`, `converted=30`, `failed=0`, `pending=0`, `incomplete_metadata=0`, `renamed=9`.
  - `paper doctor --strict --json` returned `ok=true`; counts were 30 `paper.md`, 30 `images/`, 30 `raw/mineru`, and 30 `conversion.json`.
  - Naming anomaly scan for separators, replacement characters, private-use glyphs, `SCIENTIFIC REPORTS`, and repeated spaces returned no matches after the cleanup fix.
  - AI tests passed: `tests/test_ai_repair.py` and `tests/test_ai_extract_summary.py` reported 23 passed.
  - `extract summary --dry-run --limit 30 --json` planned all 30 converted papers successfully.
  - Real-provider smoke library: `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-retest-20260525-ai-smoke`.
  - Real-provider `repair --dry-run --json` passed on the smoke library; real-provider `repair --json` write path also passed and produced `repair.json` plus a backup.
  - Real-provider `extract summary --limit 1 --workers 4 --paper-workers 1 --max-requests 8 --json` passed on the smoke library with 25 summarized blocks, 3 sections, 12 graph nodes, and 11 graph edges.
  - Smoke-library `paper doctor --strict --json` returned `ok=true` after repair and summary output generation.

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
- 2026-05-21 AI repair metadata normalization fix:
  - Fixed a full-smoke regression where provider responses using `creators` as a string list were rejected as invalid, leaving repaired bundle names without the author prefix.
  - Added a fake-provider regression test covering `creators: ["W.L. Huang", "Q.F. Li", "Y.Z. Lin"]` normalization to `paper.yaml` creator objects and metadata-based bundle rename.
  - Re-ran real-provider repair on `paper-libraries/full-smoke-library-optimized-v2`: `failed=[]`; the Huang photoneutron bundle renamed to `W.L. Huang et al. - 2005 - ...`, `paper doctor --json` returned `ok=true`, and format audit found no invalid creator shapes or naming mismatches.
  - Markdown audit still flags review-only math/formula-heavy blocks as expected, plus remaining low-risk auto-repair candidates such as front-matter labels and OCR spelling residue in the Richi Kumar GIANT paper.
  - Unified creator normalization across filename/PDF metadata, MinerU `Authors:` parsing, AI repair, and doctor validation. `make verify` passed with 56 tests.
- 2026-05-21 AI repair phase closeout:
  - Treat the built-in AI repair feature as phase-complete for now.
  - Current shipped scope: OpenAI-compatible provider, metadata evidence packets, safe metadata application, bundle rename after repaired metadata, conservative Markdown repair, exact-match patching, bundle-local backups, latest-only `repair.json`, dry-run support, fake-provider tests, and real-provider validation.
  - Current safety boundary: math-heavy/formula/table/reference blocks are not auto-rewritten; they are recorded as `review_only` warnings.
  - Remaining AI repair ideas are follow-up enhancements: warning aggregation, review/apply workflow for long OCR prose candidates, optional bundle selector, and possible append-only repair history.
- 2026-05-21 AI extract summary planning:
  - Agreed that the next AI feature should be named `paper extract summary`, with `paper extract` reserved as a future command family for structured extraction tasks.
  - Selected a layered extraction route: main process builds a short article brief and source structure, internal concurrent workers summarize block batches, then aggregators produce section skeletons and a lightweight knowledge graph.
  - Confirmed output files under `extracts/summary/`: `summary.json` for structured agent/program use, `summary.md` for human reading, and `source-map.json` for future frontend paragraph-summary alignment.
  - Confirmed strict traceability as a core contract: stable block IDs, line ranges, text hashes, excerpts, section paths, `block_ids` on section summaries, and `source_block_ids` on graph nodes/edges.
  - Confirmed first-pass filtering: summarize main prose and captions; skip references, footnotes, funding, author contributions, conflicts, copyright/license text, headers/footers, page numbers, OCR noise, pure formulas, pure tables, and pure images.
  - Recorded the design in `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`; implementation has not started.
- 2026-05-21 AI extract summary implementation:
  - Added `paper extract summary` with `--paper`, `--collection`, `--limit`, `--workers`, `--force`, `--dry-run`, and `--json`.
  - Added summary extraction under `src/paper_cli/ai/extract_summary.py`: source-map generation, summary-specific block filtering, block-batch worker prompts, section aggregation, graph extraction, atomic output writes, and default skip behavior for existing summaries.
  - Output files are written to `extracts/summary/summary.json`, `extracts/summary/summary.md`, and `extracts/summary/source-map.json`; source traceability includes block IDs, line ranges, text hashes, section paths, section `block_ids`, and graph `source_block_ids`.
  - Added fake-provider tests covering source-map filtering, traceability, no source mutation, default skip and `--force`, CLI dry-run without provider config, and missing block-summary retry.
  - Final `make verify` passed with 61 tests and ruff clean.
  - Real-provider dry-run on `paper-libraries/full-smoke-library-optimized-v2` planned 5 converted bundles with 249 summarizable blocks and 35 block batches.
  - Real-provider extraction wrote summaries for all 5 converted bundles. Final output counts matched source-map summarizable counts exactly: Jae Yeon Park 44/44, Jorge Lerendegui-Marco 61/61, Richi Kumar 55/55, W.L. Huang 26/26, and Yu Yangyi 63/63.
  - During smoke testing, one provider run omitted some block summaries for the Jae Yeon Park paper; added a retry regression test and implementation so missing block summaries are retried before outputs are considered complete.
  - After extraction, `paper status --json` on the smoke library reported `total=5`, `converted=5`, `failed=0`, `pending=0`; `paper doctor --json` returned `ok=true`.
- 2026-05-23 AI extract summary concurrency update:
  - Changed default `paper extract summary --workers` from 2 to 16.
  - Added effective worker capping to the current paper's block-batch count, so oversized values such as `--workers 200` do not create more concurrent provider calls than available batches for that paper.
  - Added a regression test for the default worker constant and effective worker calculation.
- 2026-05-23 AI extract summary paper-level concurrency update:
  - Added `--paper-workers` for paper-level parallelism, default 16.
  - Added `--max-requests` as a global provider request concurrency cap, default 16, shared by block summaries, section aggregation, and graph extraction across all papers.
  - Added `--retries`, default 2, around every provider request; final failures report the schema name, attempt count, and underlying error in `failed[].error`.
  - Added fake-provider regression tests for multi-paper concurrency, global request limiting, temporary provider retry success, and clear final failure reporting without writing partial summary output.
- 2026-05-23 AI extract summary request-cap default update:
  - Raised the default global provider request cap `--max-requests` from 16 to 500 for the user's high-concurrency provider environment.
  - Kept `--max-requests` configurable so constrained providers can still lower the cap.
- 2026-05-23 AI extract summary retry wait update:
  - Added a fixed 10-second wait between provider request retry attempts.
  - Kept retry wait as an internal program constant rather than a public CLI parameter to avoid option clutter.
  - Tests pass `retry_wait=0` through the internal function for retry cases to keep the suite fast while preserving the production default.
- 2026-05-23 QED random-30 full-test pass:
  - Drew 30 deterministic-random PDFs from `/Volumes/PHILIPS/programs/paper-cache/QED` and created the test library at `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-fulltest-20260523`.
  - `make verify` passed with 66 tests and ruff clean; `paper init`, `import`, duplicate import skip, `list`, `status`, and `doctor` command paths passed.
  - Real MinerU conversion reached 4 converted bundles and 3 recorded failed bundles, then one remote task stayed running for more than 10 minutes and blocked the remaining serial batch; the run was stopped to continue the rest of the audit.
  - Verified AI command surfaces with a local OpenAI-compatible fake provider because the environment had `MINERU_API_KEY` but no `PAPER_AI_*` provider secrets: `repair` missing-config failure, `repair --dry-run`, `repair --target all`, `extract summary --dry-run`, default skip, `--paper`, and `--force` all behaved as expected on converted bundles.
  - Generated `/Volumes/PHILIPS/programs/paper-cache/paper-cli-qed-30-fulltest-20260523-test-report.md` with artifact counts, MinerU error text, dangling job evidence, naming/content flags, and summary-output counts.
  - Issues found: MinerU conversion needs a per-file maximum wait, upload/download retry/backoff, and better interruption/job-history cleanup; `doctor` should optionally detect dangling conversion jobs or enforce strict batch success; MinerU-derived renames need guards against all-caps OCR titles, trailing path characters, and malformed spacing.
- 2026-05-23 QED random-30 hardening follow-up:
  - Added MinerU network retry/backoff for submit, upload, polling, and ZIP download calls; upload retries rewind the PDF stream before each attempt.
  - Added `MINERU_MAX_WAIT_SECONDS`, defaulting to 30 minutes per paper, so one long-running MinerU task cannot block the whole serial batch indefinitely.
  - Conversion interruption now writes `conversion.json` with `state=interrupted`, appends a matching `conversion-finished` job event, marks the bundle failed for retry, rebuilds indexes, and then re-raises the interrupt.
  - Added `paper doctor --strict` to report pending conversions, failed conversions, invalid job JSON, and dangling `conversion-started` events without matching finish events.
  - Added title quality guards so OCR-damaged MinerU headings with trailing path characters, replacement characters, all-caps rewrites, or suspicious camel-case joins do not overwrite better existing titles or trigger bundle renames.
  - `make verify` passed with 72 tests and ruff clean.
- 2026-05-23 MinerU conversion backend implementation:
  - Added `paper convert --pending --converter` selection for `mineru-api`, `mineru-api-batch`, `mineru-local`, and `local-fixture`; `--batch-size`, `--jobs`, and `--local-backend` configure the new backends.
  - Added batch conversion orchestration that records per-bundle success and failure without blocking successful items in the same batch.
  - Added `mineru-api-batch` with 50-file upload-link request cap, stable `data_id`, bounded upload/download concurrency, polling, ZIP normalization, and resume from existing running `batch_id`.
  - Added `mineru-local` for installed `mineru` CLI conversion, including `-b` backend selection, local output normalization into `paper.md`, `images/`, and `raw/mineru/`, plus `--jobs` batch concurrency.
  - Extended strict doctor checks for stale running conversion files and missing `mineru-api-batch` `batch_id` / `data_id` mappings.
  - Real QED random-30 validation used `/Volumes/PHILIPS/programs/paper-cache/paper-cli-mineru-backends-qed-30-20260523-rerun` with `--converter mineru-api-batch --batch-size 2 --jobs 1`.
  - The conservative real run converted 6 papers successfully before MinerU OSS upload through the local proxy stalled again; interrupting the run wrote 2 `interrupted` conversion records and marked those bundles failed for retry.
  - The first real batch attempt exposed that started job events were being written for future chunks too early and that upload timeout was not bounded by `MINERU_MAX_WAIT_SECONDS`; both issues now have regression tests and fixes.
  - Local `mineru` CLI validation could not run on this machine because `mineru` is not installed on `PATH`; the backend is covered by subprocess-based tests.
  - Final local verification passed: `make verify` with 89 tests and ruff clean.
- 2026-05-24 local MinerU QED random-30 validation:
  - Installed the cloned MinerU repository at `/Volumes/PHILIPS/programs/mineru` into `/Volumes/PHILIPS/programs/mineru/.venv` with `uv pip install -e ".[all]"`.
  - Added missing `socksio` to the MinerU venv because the local environment uses a SOCKS proxy and MinerU/httpx failed without it.
  - Ran `paper convert --pending --converter mineru-local --local-backend pipeline --batch-size 1 --jobs 1` with `PATH=/Volumes/PHILIPS/programs/mineru/.venv/bin:$PATH` on 30 QED sample papers.
  - Final library: `/Volumes/PHILIPS/programs/paper-cache/paper-cli-mineru-local-qed-30-20260524`.
  - Final status: `total=30`, `converted=30`, `failed=0`, `pending=0`, `incomplete_metadata=0`, `renamed=13`.
  - `paper doctor --strict --json` returned `ok=true`.
  - Verified 30 `paper.md`, 30 `images/`, 30 `raw/mineru/`, and 30 `conversion.json` outputs.
  - Naming audit found four review candidates after local MinerU metadata extraction: one math-heavy title fragment, one private-use glyph at title end, one journal-label title (`SCIENTIFIC REPORTS`), and one title ending with `\`.
- 2026-05-24 AI provider smoke on local MinerU output:
  - Loaded provider configuration from the project `.env` without printing secret values.
  - `tests/test_ai_repair.py` and `tests/test_ai_extract_summary.py` passed with 23 tests.
  - `extract summary --dry-run --limit 30` on `/Volumes/PHILIPS/programs/paper-cache/paper-cli-mineru-local-qed-30-20260524` planned all 30 converted papers successfully.
  - A full-library `repair --dry-run` against the 30-paper library was stopped after the provider request chain hung through the local proxy for several minutes.
  - Created one-paper smoke library `/Volumes/PHILIPS/programs/paper-cache/paper-cli-ai-repair-smoke-20260524` from the local MinerU output.
  - Real provider `repair --dry-run` passed on the smoke library with `ok=true`, `repaired_count=1`, and `failed_count=0`.
  - Real provider `extract summary --limit 1` passed on the smoke library with 41 summarized blocks, 1 section, 13 graph nodes, and 11 graph edges.
  - Real provider `repair --json` write path passed on the smoke library; `paper doctor --strict --json` then returned `ok=true`.

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
- `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`
