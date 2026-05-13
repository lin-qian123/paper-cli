# paper-cli Conversion Jobs Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden conversion bookkeeping by expanding `conversion.json`, appending conversion job events to `indexes/jobs.jsonl`, and making failed conversions explicitly retryable.

**Architecture:** Keep conversion synchronous and local. Do not introduce a daemon, queue service, SQLite, or background worker. Treat `conversion.json` as the latest per-bundle diagnostic record and `indexes/jobs.jsonl` as append-only job history.

**Tech Stack:** Python 3.11, pytest, JSON/JSONL files, existing converter interface.

---

## File Structure

- Modify `src/paper_cli/convert.py`: write expanded conversion diagnostics, append job events, track attempts.
- Modify `src/paper_cli/converters/base.py`: expose an optional converter name contract.
- Modify `src/paper_cli/converters/local_zip.py`: name fixture converter.
- Modify `src/paper_cli/converters/mineru.py`: name MinerU converter.
- Modify `tests/test_convert.py`: add conversion diagnostics, job history, and retry tests.
- Modify `docs/contracts/conversion-json.md`: update current contract from planned to implemented.
- Modify `docs/zh/contracts/conversion-json.zh.md`: Chinese mirror.
- Modify `TODO.md` and `docs/zh/TODO.zh.md`: record milestone completion.

## Chunk 1: Diagnostic `conversion.json`

### Task 1: Expand Latest Conversion Record

**Files:**
- Test: `tests/test_convert.py`
- Modify: `src/paper_cli/convert.py`
- Modify: `src/paper_cli/converters/base.py`
- Modify: `src/paper_cli/converters/local_zip.py`
- Modify: `src/paper_cli/converters/mineru.py`

- [x] **Step 1: Write failing success diagnostic test**
  Assert successful conversion writes `schema_version`, `converter`, `ok`, `state`, `attempt`, `submitted_at`, `converted_at`, `error`, `raw_output_dir`, `markdown`, and `images`.

- [x] **Step 2: Run focused test**
  Run: `uv run --extra dev pytest tests/test_convert.py::<test-name> -v`
  Expected: FAIL because current `conversion.json` is minimal.

- [x] **Step 3: Implement minimal diagnostic writer**
  Add converter names and expand the record while preserving current success behavior.

- [x] **Step 4: Run focused test**
  Expected: PASS.

## Chunk 2: Job History

### Task 2: Append Conversion Events

**Files:**
- Test: `tests/test_convert.py`
- Modify: `src/paper_cli/convert.py`

- [x] **Step 1: Write failing jobs test**
  Assert `indexes/jobs.jsonl` contains start and finish events with paper ID, bundle path, converter, state, and timestamps.

- [x] **Step 2: Run focused test**
  Expected: FAIL because events are not appended.

- [x] **Step 3: Append events via existing `append_job` helper**
  Add `conversion-started` and `conversion-finished` events.

- [x] **Step 4: Run focused test**
  Expected: PASS.

## Chunk 3: Failed Conversion Retry

### Task 3: Preserve Failure Diagnostics And Retry

**Files:**
- Test: `tests/test_convert.py`
- Modify: `src/paper_cli/convert.py`

- [x] **Step 1: Write failing retry test**
  Fail a fixture conversion, assert failed diagnostics and job event, then add fixture output and assert the same failed bundle is retried and succeeds with attempt `2`.

- [x] **Step 2: Run focused test**
  Expected: FAIL on missing attempt/job details.

- [x] **Step 3: Implement retry attempt counting**
  Read prior `conversion.json` if present and increment `attempt`. Continue skipping only `done` bundles.

- [x] **Step 4: Run focused test**
  Expected: PASS.

## Chunk 4: Documentation And Verification

### Task 4: Update Docs And Commit

**Files:**
- Modify: `docs/contracts/conversion-json.md`
- Modify: `docs/zh/contracts/conversion-json.zh.md`
- Modify: `TODO.md`
- Modify: `docs/zh/TODO.zh.md`

- [x] **Step 1: Update contract docs**
  Show the expanded `conversion.json` as current behavior.

- [x] **Step 2: Update TODO**
  Mark conversion job hardening complete and leave next metadata provenance work visible.

- [x] **Step 3: Run verification**
  Run: `make verify`
  Expected: PASS.

- [x] **Step 4: Commit**
  Commit message: `feat: add conversion job diagnostics`
