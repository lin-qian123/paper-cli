# MinerU Conversion Backends Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `paper-cli` conversion reliable for large paper libraries by adding a MinerU cloud batch backend first, then a local MinerU backend as a stable fallback.

**Architecture:** Keep the paper bundle contract unchanged and introduce explicit converter backends behind the existing `Converter` boundary. The cloud backend should submit batches, upload/download concurrently with limits, persist enough job state to resume safely, and reuse current conversion normalization. The local backend should call the installed `mineru` CLI and normalize its output into the same bundle shape.

**Tech Stack:** Python 3.11, existing `paper_cli.converters` protocol, `requests`, `ThreadPoolExecutor`, local filesystem JSON/YAML contracts, MinerU precise API, optional installed MinerU CLI.

---

## Background

The QED random-30 validation showed that the current per-paper MinerU API path is too fragile for large libraries:

- One remote task can block the serial batch.
- Upload/download proxy or timeout failures can leave many papers unfinished.
- The current converter does not exploit MinerU batch submission even though the official precise API supports batch parsing.

The official MinerU API documentation describes two relevant precise API batch paths:

- `/api/v4/file-urls/batch`: batch request signed upload URLs for local files. The mode comparison says precise API batch support is available, while the local upload section says a single upload-link request should not exceed 50 files.
- `/api/v4/extract/task/batch`: submit multiple URL files and poll by `batch_id`.

The same documentation also describes an Agent lightweight API, but that path is unsuitable for the main `paper-cli` converter because it is single-file, IP rate-limited, limited to smaller files/pages, and only returns Markdown. Treat it as a future experimental fallback, not the primary backend.

The `opendatalab/MinerU` repository documents local deployment, including CLI usage:

```bash
mineru -p <input_path> -o <output_path>
mineru -p <input_path> -o <output_path> -b pipeline
```

Local deployment is feasible, especially for stable large batch work, but it has hardware and environment tradeoffs. Docker is documented for Linux and Windows WSL2; macOS should use package/source installation instead.

## Product Direction

Implement in two stages:

1. `mineru-api-batch`: cloud API batch backend, because it is closest to the current implementation and immediately improves QED-scale throughput.
2. `mineru-local`: local CLI backend, because it avoids cloud queue, proxy, OSS download, and rate-limit instability for sustained large libraries.

Do not change the durable output contract:

```text
<paper-bundle>/
  paper.yaml
  original.pdf
  paper.md
  images/
  conversion.json
  raw/
    mineru/
  indexes/jobs.jsonl
```

## CLI Design

Recommended command surface:

```bash
paper convert --pending --converter mineru-api
paper convert --pending --converter mineru-api-batch --batch-size 20 --jobs 4
paper convert --pending --converter mineru-local --jobs 2
paper convert --pending --converter mineru-local --local-backend pipeline
paper doctor --strict --json
```

Defaults:

- Keep existing `paper convert --pending` behavior compatible for now.
- Add `--converter` with choices:
  - `mineru-api`: current per-paper cloud API backend.
  - `mineru-api-batch`: new precise API batch backend.
  - `mineru-local`: local installed CLI backend.
  - `local-fixture`: existing test backend, replacing or aliasing the current `--fixture-output` path internally.
- `--batch-size`: default 20, max 50 for `mineru-api-batch`.
- `--jobs`: default 4 for cloud upload/download concurrency, default 1 or 2 for local CLI depending on CPU/GPU safety.
- Keep `MINERU_MAX_WAIT_SECONDS` for per-task or per-batch waiting.

## State And Recovery Design

Extend `conversion.json` without breaking current readers:

```json
{
  "schema_version": 1,
  "converter": "mineru-api-batch",
  "ok": false,
  "state": "running",
  "attempt": 2,
  "submitted_at": "...",
  "converted_at": null,
  "batch_id": "mineru-batch-id",
  "data_id": "paper-cli-paper-id-or-short-hash",
  "remote_state": "running",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

Extend `indexes/jobs.jsonl` event payloads with optional batch fields:

```json
{
  "event": "conversion-started",
  "paper_id": "sha256:...",
  "bundle_path": "collections/QED/random-30/...",
  "converter": "mineru-api-batch",
  "attempt": 2,
  "state": "running",
  "batch_id": "..."
}
```

Recovery rules:

- If a bundle has `state=running` and `batch_id`, `paper convert --pending` should be able to resume polling before submitting a duplicate task.
- If polling says done, download and normalize output.
- If polling says failed, write failed state and keep diagnostics.
- If local process was interrupted, keep the currently implemented `interrupted` finished event behavior.
- `paper doctor --strict` should continue to flag dangling started jobs and incomplete conversions.

## File Structure

Expected files:

- Modify `src/paper_cli/cli.py`
  - Add `--converter`, `--batch-size`, `--jobs`, `--local-backend`.
  - Keep `--fixture-output` as a compatibility shortcut.
- Modify `src/paper_cli/convert.py`
  - Add a batch-aware conversion orchestration path while preserving the single-paper `Converter` protocol.
  - Consider a new `BatchConverter` protocol instead of overloading `Converter`.
- Create `src/paper_cli/converters/mineru_api_batch.py`
  - Own precise API batch upload, polling, download, retry, and resume behavior.
- Create `src/paper_cli/converters/mineru_local.py`
  - Own subprocess calls to local `mineru`.
  - Normalize CLI output to the same bundle contract.
- Modify `src/paper_cli/converters/mineru.py`
  - Keep current single-paper API backend as compatibility backend.
  - Reuse shared ZIP normalization if split out.
- Optionally create `src/paper_cli/converters/mineru_normalize.py`
  - Shared output normalization for API ZIP and local output.
- Modify `src/paper_cli/doctor.py`
  - Add stricter checks for stale running `conversion.json` if needed.
- Modify `tests/test_convert.py`
  - Add CLI option and conversion orchestration tests.
- Create `tests/test_mineru_api_batch.py`
  - Mock API batch submit, upload, poll, done/failed, resume, and download.
- Create `tests/test_mineru_local.py`
  - Mock subprocess and local output normalization.
- Update `README.md`, `docs/zh/README.zh.md`, `TODO.md`, and `docs/zh/TODO.zh.md` after implementation.

## Chunk 1: Converter Selection

### Task 1: Add Converter CLI Selection

**Files:**
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_convert.py`

- [ ] **Step 1: Write failing tests**
  - Test `paper convert --pending --converter local-fixture --fixture-output <dir>` still works.
  - Test unknown converter is rejected by argparse.
  - Test `--converter mineru-api` selects the existing `MinerUConverter`.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_convert.py
  ```
  Expected: new tests fail because `--converter` is not implemented.

- [ ] **Step 3: Implement converter selection**
  - Add `--converter`.
  - Map existing no-argument default to `mineru-api`.
  - Preserve `--fixture-output` compatibility.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_convert.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/cli.py tests/test_convert.py
  git commit -m "feat: add converter selection"
  ```

## Chunk 2: MinerU Cloud Batch Backend

### Task 2: Add Batch Converter Protocol

**Files:**
- Modify: `src/paper_cli/converters/base.py`
- Modify: `src/paper_cli/convert.py`
- Test: `tests/test_convert.py`

- [ ] **Step 1: Write failing tests**
  - Create a fake batch converter that receives multiple pending bundles.
  - Verify it writes done state for each returned bundle.
  - Verify a failed item in the same batch writes failed state without blocking successful items.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_convert.py
  ```

- [ ] **Step 3: Implement minimal batch protocol**
  - Add `BatchConversionItem` and `BatchConverter` or equivalent.
  - Keep existing single-paper converter path unchanged.
  - Add `convert_pending(..., batch_size=..., jobs=...)` parameters only if needed by CLI.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_convert.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/converters/base.py src/paper_cli/convert.py tests/test_convert.py
  git commit -m "feat: add batch conversion orchestration"
  ```

### Task 3: Implement MinerU API Batch Submit And Upload

**Files:**
- Create: `src/paper_cli/converters/mineru_api_batch.py`
- Test: `tests/test_mineru_api_batch.py`

- [ ] **Step 1: Write failing tests**
  - Mock `POST /api/v4/file-urls/batch`.
  - Verify no request contains more than 50 files.
  - Verify `data_id` is stable and maps back to bundle/paper ID.
  - Verify upload PUT calls are made with retry and concurrency limit.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_api_batch.py
  ```

- [ ] **Step 3: Implement submit/upload**
  - Use existing `MINERU_API_KEY`.
  - Default model version should stay configurable later; use current behavior first.
  - Use a bounded `ThreadPoolExecutor` for upload.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_api_batch.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_api_batch.py tests/test_mineru_api_batch.py
  git commit -m "feat: submit MinerU batch uploads"
  ```

### Task 4: Implement Batch Polling, Download, And Resume

**Files:**
- Modify: `src/paper_cli/converters/mineru_api_batch.py`
- Modify: `src/paper_cli/convert.py`
- Test: `tests/test_mineru_api_batch.py`

- [ ] **Step 1: Write failing tests**
  - Polling returns mixed `done`, `running`, and `failed` items.
  - Done item downloads ZIP and normalizes to `paper.md`, `images/`, `raw/mineru/`.
  - Failed item writes diagnostics.
  - Existing `conversion.json` with `state=running` and `batch_id` resumes polling instead of submitting duplicate upload.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_api_batch.py
  ```

- [ ] **Step 3: Implement polling/download/resume**
  - Poll by `batch_id`.
  - Reuse existing retry and `MINERU_MAX_WAIT_SECONDS`.
  - Do not write successful final state until output normalization succeeds.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_api_batch.py tests/test_convert.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_api_batch.py src/paper_cli/convert.py tests/test_mineru_api_batch.py
  git commit -m "feat: poll and resume MinerU batch conversions"
  ```

## Chunk 3: Local MinerU Backend

### Task 5: Implement Local CLI Converter

**Files:**
- Create: `src/paper_cli/converters/mineru_local.py`
- Test: `tests/test_mineru_local.py`
- Modify: `src/paper_cli/cli.py`

- [ ] **Step 1: Write failing tests**
  - Mock `subprocess.run`.
  - Verify command includes `mineru -p original.pdf -o <tmp-output>`.
  - Verify `--local-backend pipeline` adds `-b pipeline`.
  - Verify missing CLI returns a clear conversion failure.
  - Verify local output is normalized to bundle contract.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_local.py
  ```

- [ ] **Step 3: Implement local converter**
  - Use a temporary output directory per paper.
  - Call installed `mineru`.
  - Move/copy normalized output into bundle.
  - Capture stdout/stderr in conversion diagnostics on failure.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_mineru_local.py tests/test_convert.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_local.py src/paper_cli/cli.py tests/test_mineru_local.py
  git commit -m "feat: add local MinerU converter"
  ```

## Chunk 4: Strict Audit And Documentation

### Task 6: Strengthen Doctor For Batch Runs

**Files:**
- Modify: `src/paper_cli/doctor.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write failing tests**
  - `paper doctor --strict` reports stale `state=running` conversion files older than `MINERU_MAX_WAIT_SECONDS`.
  - `paper doctor --strict` reports missing batch mapping fields for `mineru-api-batch` running jobs.

- [ ] **Step 2: Run tests**
  ```bash
  uv run --extra dev pytest -q tests/test_doctor.py
  ```

- [ ] **Step 3: Implement strict checks**
  - Keep normal `doctor` non-strict behavior unchanged.
  - Add strict-only issue codes.

- [ ] **Step 4: Verify**
  ```bash
  uv run --extra dev pytest -q tests/test_doctor.py
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/doctor.py tests/test_doctor.py
  git commit -m "feat: audit batch conversion state"
  ```

### Task 7: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/zh/README.zh.md`
- Modify: `TODO.md`
- Modify: `docs/zh/TODO.zh.md`
- Optional: `docs/contracts/conversion-json.md`

- [ ] **Step 1: Update README command examples**
  - Document `--converter mineru-api-batch`.
  - Document `--batch-size`, `--jobs`, `--local-backend`.
  - Explain `mineru-local` prerequisites.

- [ ] **Step 2: Update TODO validation log**
  - Record tests and any real QED smoke rerun.

- [ ] **Step 3: Run docs and full checks**
  ```bash
  make verify
  ```
  Expected: all tests pass and ruff clean.

- [ ] **Step 4: Commit**
  ```bash
  git add README.md docs/zh/README.zh.md TODO.md docs/zh/TODO.zh.md docs/contracts/conversion-json.md
  git commit -m "docs: document MinerU conversion backends"
  ```

## Manual Validation Plan

After implementation, run these smoke tests with real PDFs under ignored local paths:

```bash
paper init /path/to/paper-cli-mineru-batch-smoke
paper --library /path/to/paper-cli-mineru-batch-smoke import /path/to/qed-sample-input --collection QED/random-30 --json
paper --library /path/to/paper-cli-mineru-batch-smoke convert --pending --converter mineru-api-batch --batch-size 10 --jobs 4 --json
paper --library /path/to/paper-cli-mineru-batch-smoke status --json
paper --library /path/to/paper-cli-mineru-batch-smoke doctor --strict --json
```

If local MinerU is installed:

```bash
paper init /path/to/paper-cli-mineru-local-smoke
paper --library /path/to/paper-cli-mineru-local-smoke import /path/to/qed-sample-input --collection QED/random-30 --json
paper --library /path/to/paper-cli-mineru-local-smoke convert --pending --converter mineru-local --local-backend pipeline --jobs 1 --json
paper --library /path/to/paper-cli-mineru-local-smoke doctor --strict --json
```

Record results in `TODO.md`; do not commit generated libraries, PDFs, MinerU ZIPs, images, or Markdown outputs.

## Open Decisions

- Whether `mineru-api-batch` should become the default cloud backend after validation.
- Whether to expose `model_version`, `language`, `enable_formula`, `enable_table`, and `is_ocr` as CLI flags now or keep them in `paper-cli.yaml`.
- Whether local `mineru` output layout is stable enough to normalize without a dedicated adapter version field.
- Whether to implement callback support later. For a local-first CLI, polling is simpler and sufficient for now.
