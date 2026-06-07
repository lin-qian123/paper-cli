# MinerU Productization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current working MinerU backends into a more operationally reliable, easier-to-run conversion subsystem for large paper libraries.

**Architecture:** Keep the existing paper bundle contract unchanged, but make MinerU environment discovery, output normalization, metadata extraction, retry flows, concurrency selection, and validation workflows explicit modules. Prefer deterministic conversion-time logic for metadata that can be extracted from local evidence; keep `paper repair` as an optional AI review layer for uncertain or corrective changes.

**Tech Stack:** Python 3.11, `argparse`, YAML config, JSON/JSONL bundle contracts, `requests`, `subprocess`, `ThreadPoolExecutor`, existing `paper_cli` converters and doctor checks, local QED corpus smoke tests.

---

## Scope

This plan covers the requested MinerU follow-up areas:

1. Productize local MinerU environment management.
2. Improve deterministic metadata extraction from MinerU output.
3. Add real large-scale validation for `mineru-api-batch`.
4. Extract shared MinerU output normalization.
5. Add local MinerU concurrency auto-tuning.
6. Script the QED validation workflow.

This plan intentionally does not redesign `paper repair`, `paper extract summary`, Zotero import, or the durable bundle layout.

## Why Metadata Extraction Is Not Only `paper repair`

MinerU conversion already sees strong local evidence: the source PDF filename, PDF metadata, the first Markdown heading, early title-page text, `Authors:` lines when present, and MinerU sidecar files. When the project can extract metadata from those sources with deterministic rules and confidence labels, it should do so during conversion because:

- It is reproducible and does not require an AI provider.
- It improves bundle naming and indexes immediately after conversion.
- It keeps the library usable before any AI repair step runs.
- It is easier to test with fixtures and real MinerU output.

`paper repair` should remain the second-pass review layer for cases where deterministic evidence is weak or conflicting. It may use broader context and AI judgment, but it should not become required for normal conversion correctness. A good boundary is:

- Conversion-time metadata extraction: parse obvious title, creators, year, DOI, arXiv ID, and language from local deterministic evidence; assign source and confidence.
- Repair-time metadata correction: propose changes when local evidence conflicts, author extraction is ambiguous, title pages are messy, or the user wants a reviewable AI pass.

## File Structure

- Modify `src/paper_cli/config.py`
  - Add optional MinerU config defaults and merge logic.
- Modify `src/paper_cli/cli.py`
  - Add config-aware MinerU executable/backend/default jobs handling.
  - Add validation script entrypoint if implemented as a CLI subcommand.
- Modify `src/paper_cli/converters/mineru_local.py`
  - Use resolved local MinerU settings instead of assuming `mineru` on `PATH`.
  - Add auto jobs resolution hook.
- Modify `src/paper_cli/converters/mineru_api_batch.py`
  - Reuse shared normalization.
  - Improve diagnostics for real batch validation.
- Create `src/paper_cli/converters/mineru_normalize.py`
  - Own shared Markdown/image/raw sidecar normalization for ZIP and local directories.
- Create `src/paper_cli/converters/mineru_env.py`
  - Resolve local executable, inspect version, and produce doctor-friendly diagnostics.
- Create `src/paper_cli/converters/mineru_metadata.py`
  - Extract deterministic metadata candidates from MinerU Markdown and sidecars.
- Create `src/paper_cli/converters/mineru_jobs.py`
  - Resolve local jobs defaults from config and system resources.
- Modify `src/paper_cli/convert.py`
  - Use `mineru_metadata.py` for conversion-time metadata updates.
  - Use shared normalization result fields where needed.
- Modify `src/paper_cli/doctor.py`
  - Add local MinerU environment checks in strict mode.
  - Add optional conversion output quality warnings.
- Create `src/paper_cli/validation/qed.py`
  - Deterministic QED sample selection, library creation, command orchestration, artifact counts, and report generation.
- Modify `tests/test_config.py`
  - Cover MinerU config defaults and overrides.
- Create `tests/test_mineru_env.py`
  - Cover executable resolution, missing executable, and version parsing.
- Create `tests/test_mineru_normalize.py`
  - Cover shared normalization from ZIP and local output trees.
- Create `tests/test_mineru_metadata.py`
  - Cover title-page author, DOI, arXiv, and confidence behavior.
- Create `tests/test_mineru_jobs.py`
  - Cover auto jobs selection and config/CLI precedence.
- Create `tests/test_qed_validation.py`
  - Cover validation workflow with fixture commands and no real PDFs.
- Modify `README.md` and `docs/zh/README.zh.md`
  - Document MinerU local config, auto jobs, and validation workflow.
- Modify `TODO.md` and `docs/zh/TODO.zh.md`
  - Track implementation progress and validation results.

## Chunk 1: Local MinerU Environment Management

### Task 1: Add MinerU Config Defaults

**Files:**
- Modify: `src/paper_cli/config.py`
- Test: `tests/test_config.py`
- Docs: `README.md`, `docs/zh/README.zh.md`

- [ ] **Step 1: Write failing tests**
  - Test default config includes:
    ```yaml
    mineru:
      executable: mineru
      local_backend: null
      local_jobs: auto
      max_wait_seconds: null
    ```
  - Test a library `paper-cli.yaml` override can set:
    ```yaml
    mineru:
      executable: /path/to/mineru/.venv/bin/mineru
      local_backend: pipeline
      local_jobs: 1
    ```

- [ ] **Step 2: Run test to verify failure**
  ```bash
  uv run pytest tests/test_config.py -q
  ```
  Expected: fails because `mineru` config defaults are not present.

- [ ] **Step 3: Implement config defaults**
  - Extend `default_config()` with the `mineru` section.
  - Ensure existing library configs merge without overwriting user settings.

- [ ] **Step 4: Run tests**
  ```bash
  uv run pytest tests/test_config.py -q
  ```
  Expected: pass.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/config.py tests/test_config.py README.md docs/zh/README.zh.md
  git commit -m "feat: configure local MinerU executable"
  ```

### Task 2: Resolve And Diagnose Local MinerU Executable

**Files:**
- Create: `src/paper_cli/converters/mineru_env.py`
- Modify: `src/paper_cli/converters/mineru_local.py`
- Modify: `src/paper_cli/doctor.py`
- Test: `tests/test_mineru_env.py`, `tests/test_mineru_local.py`, `tests/test_doctor.py`

- [ ] **Step 1: Write failing tests**
  - `resolve_mineru_executable(config, cli_executable=None)` returns config path when configured.
  - It falls back to `shutil.which("mineru")`.
  - It returns a diagnostic object when missing.
  - `doctor --strict` emits `missing-mineru-local-executable` when `mineru-local` is configured but not executable.
  - Version parsing accepts output like `mineru, version 3.1.15`.

- [ ] **Step 2: Run tests**
  ```bash
  uv run pytest tests/test_mineru_env.py tests/test_mineru_local.py tests/test_doctor.py -q
  ```
  Expected: fails because module and doctor checks do not exist.

- [ ] **Step 3: Implement `mineru_env.py`**
  - Define a small dataclass:
    ```python
    @dataclass
    class MinerUEnvironment:
        executable: str | None
        exists: bool
        version: str | None = None
        error: str | None = None
    ```
  - Add:
    - `resolve_mineru_environment(config: dict, cli_executable: str | None = None)`.
    - `probe_mineru_version(executable: str, timeout: float = 10)`.
  - Keep probing read-only and bounded by timeout.

- [ ] **Step 4: Wire into local converter**
  - `MinerULocalConverter` should accept `executable=None`.
  - If not provided, resolve from config before running.
  - Preserve current constructor behavior for tests.

- [ ] **Step 5: Wire into doctor**
  - In strict mode, if library config points to `mineru-local` usage or has a `mineru` section, report clear environment diagnostics.

- [ ] **Step 6: Run tests**
  ```bash
  uv run pytest tests/test_mineru_env.py tests/test_mineru_local.py tests/test_doctor.py -q
  ```
  Expected: pass.

- [ ] **Step 7: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_env.py src/paper_cli/converters/mineru_local.py src/paper_cli/doctor.py tests/test_mineru_env.py tests/test_mineru_local.py tests/test_doctor.py
  git commit -m "feat: diagnose local MinerU environment"
  ```

## Chunk 2: Deterministic MinerU Metadata Extraction

### Task 3: Add MinerU Metadata Candidate Parser

**Files:**
- Create: `src/paper_cli/converters/mineru_metadata.py`
- Modify: `src/paper_cli/convert.py`
- Test: `tests/test_mineru_metadata.py`, `tests/test_convert.py`

- [ ] **Step 1: Write failing tests**
  - Markdown with explicit heading and `Authors:` keeps current behavior.
  - Title-page text without `Authors:` extracts creators from early lines:
    ```markdown
    # Correct Paper Title

    Alice Zhang, Bob Li, and Carol Wang
    Institute of Example
    ```
  - DOI extraction finds `10.xxxx/...`.
  - arXiv extraction finds `arXiv:2401.12345`.
  - Journal/publisher labels such as `SCIENTIFIC REPORTS` are rejected as titles when filename title is better.
  - Creator candidates from affiliations or emails are rejected.

- [ ] **Step 2: Run tests**
  ```bash
  uv run pytest tests/test_mineru_metadata.py tests/test_convert.py -q
  ```
  Expected: fails because parser does not exist.

- [ ] **Step 3: Implement parser**
  - Add `extract_mineru_metadata(markdown: str, *, existing: dict | None = None) -> tuple[dict, dict[str, str], dict[str, str]]`.
  - Keep confidence conservative:
    - `title`: `high` only for valid `# ` heading after quality gates.
    - `creators`: `medium` for title-page author-line heuristics, `high` only for explicit `Authors:`.
    - `doi`: `high` for DOI regex.
    - `arxiv`: `high` for arXiv regex if schema supports it later; otherwise keep under identifier candidates or skip until contract update.
  - Reuse `normalize_creators`.
  - Reject lines containing emails, affiliations, copyright, abstract labels, journal labels, or too many digits.

- [ ] **Step 4: Wire parser into conversion**
  - Replace direct `extract_metadata_details_from_markdown()` usage in `convert.py` with the new parser or make the old function delegate to it.
  - Preserve current metadata source/confidence merge rules.

- [ ] **Step 5: Run tests**
  ```bash
  uv run pytest tests/test_mineru_metadata.py tests/test_convert.py -q
  ```
  Expected: pass.

- [ ] **Step 6: Real fixture audit**
  - Pick 5 already converted QED bundles.
  - Run a dry fixture replay or metadata-only local script to compare old/new metadata without mutating source bundles.
  - Record false positives in TODO before broadening heuristics.

- [ ] **Step 7: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_metadata.py src/paper_cli/convert.py tests/test_mineru_metadata.py tests/test_convert.py TODO.md docs/zh/TODO.zh.md
  git commit -m "feat: improve MinerU metadata extraction"
  ```

## Chunk 3: Shared MinerU Output Normalization

### Task 4: Extract Normalization Module

**Files:**
- Create: `src/paper_cli/converters/mineru_normalize.py`
- Modify: `src/paper_cli/converters/mineru.py`
- Modify: `src/paper_cli/converters/mineru_api_batch.py`
- Modify: `src/paper_cli/converters/mineru_local.py`
- Test: `tests/test_mineru_normalize.py`, `tests/test_mineru_api_batch.py`, `tests/test_mineru_local.py`, `tests/test_convert.py`

- [ ] **Step 1: Write failing tests**
  - Normalize a ZIP containing nested `full.md` and `images/`.
  - Normalize a local directory containing nested Markdown, images, and sidecars.
  - Move sidecars to `raw/mineru/`.
  - Remove empty extracted directories.
  - Preserve `paper.md` and `images/` when source layout is already normalized.

- [ ] **Step 2: Run tests**
  ```bash
  uv run pytest tests/test_mineru_normalize.py tests/test_mineru_api_batch.py tests/test_mineru_local.py -q
  ```
  Expected: fails because shared module does not exist.

- [ ] **Step 3: Implement `mineru_normalize.py`**
  - Define:
    ```python
    @dataclass
    class NormalizedMinerUOutput:
        markdown_path: Path
        images_dir: Path
        raw_dir: Path
    ```
  - Add:
    - `normalize_mineru_directory(source_dir: Path, bundle_dir: Path)`.
    - `normalize_mineru_zip(content: bytes, bundle_dir: Path)`.
  - Keep behavior compatible with existing tests.

- [ ] **Step 4: Refactor converters**
  - `mineru.py` single-file cloud ZIP path uses `normalize_mineru_zip`.
  - `mineru_api_batch.py` uses `normalize_mineru_zip`.
  - `mineru_local.py` uses `normalize_mineru_directory`.

- [ ] **Step 5: Run tests**
  ```bash
  uv run pytest tests/test_mineru_normalize.py tests/test_mineru_api_batch.py tests/test_mineru_local.py tests/test_convert.py -q
  ```
  Expected: pass.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_normalize.py src/paper_cli/converters/mineru.py src/paper_cli/converters/mineru_api_batch.py src/paper_cli/converters/mineru_local.py tests/test_mineru_normalize.py tests/test_mineru_api_batch.py tests/test_mineru_local.py tests/test_convert.py
  git commit -m "refactor: share MinerU output normalization"
  ```

## Chunk 4: Local Concurrency Auto-Tuning

### Task 5: Add Local MinerU Jobs Resolver

**Files:**
- Create: `src/paper_cli/converters/mineru_jobs.py`
- Modify: `src/paper_cli/cli.py`
- Modify: `src/paper_cli/converters/mineru_local.py`
- Test: `tests/test_mineru_jobs.py`, `tests/test_convert.py`

- [ ] **Step 1: Write failing tests**
  - CLI `--jobs` overrides everything.
  - Config `mineru.local_jobs: 1` is honored.
  - Config `mineru.local_jobs: auto` chooses a conservative value.
  - Auto never exceeds pending item count.
  - Auto defaults to `1` when memory or platform information is unavailable.

- [ ] **Step 2: Run tests**
  ```bash
  uv run pytest tests/test_mineru_jobs.py tests/test_convert.py -q
  ```
  Expected: fails because resolver does not exist.

- [ ] **Step 3: Implement resolver**
  - Add:
    ```python
    def resolve_local_jobs(config: dict, cli_jobs: int | None, pending_count: int) -> int:
        ...
    ```
  - Start conservative:
    - CLI integer wins.
    - Config integer wins.
    - `auto` returns `1` on macOS unless an explicit later heuristic is approved.
    - Never return less than `1` or more than `pending_count`.
  - Record in docs that auto is conservative until more real local GPU/MPS data exists.

- [ ] **Step 4: Wire into CLI**
  - For `mineru-local`, pass resolved jobs to `convert_pending`.
  - Keep cloud default `--jobs=4` unless user overrides.

- [ ] **Step 5: Run tests**
  ```bash
  uv run pytest tests/test_mineru_jobs.py tests/test_convert.py -q
  ```
  Expected: pass.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_jobs.py src/paper_cli/cli.py src/paper_cli/converters/mineru_local.py tests/test_mineru_jobs.py tests/test_convert.py README.md docs/zh/README.zh.md
  git commit -m "feat: auto-tune local MinerU jobs"
  ```

## Chunk 5: Cloud Batch Large-Scale Validation

### Task 6: Add Batch Validation Runbook And Diagnostics

**Files:**
- Modify: `docs/smoke-tests/mineru.md`
- Modify: `docs/zh/smoke-tests/mineru.zh.md`
- Modify: `src/paper_cli/converters/mineru_api_batch.py`
- Test: `tests/test_mineru_api_batch.py`

- [ ] **Step 1: Write failing tests**
  - Batch converter includes enough error text to distinguish upload URL request, upload, polling, download, and ZIP normalization failures.
  - Timeout errors include `MINERU_MAX_WAIT_SECONDS`.
  - Running state remains resumable after upload failure.

- [ ] **Step 2: Run tests**
  ```bash
  uv run pytest tests/test_mineru_api_batch.py -q
  ```
  Expected: identify missing diagnostics if current messages are too generic.

- [ ] **Step 3: Improve diagnostics only where tests prove gaps**
  - Do not add complex retry policy changes unless real validation needs them.
  - Keep network retry count bounded.

- [ ] **Step 4: Update runbook**
  - Add exact commands for:
    ```bash
    paper convert --pending --converter mineru-api-batch --batch-size 20 --jobs 4 --json
    paper doctor --strict --json
    ```
  - Add suggested conservative validation ladder:
    - 10 papers
    - 30 papers
    - 100 papers
  - Add required report fields:
    - converted/failed/pending/interrupted
    - upload/poll/download error counts
    - resume result after interruption
    - artifact counts

- [ ] **Step 5: Execute real validation when network is stable**
  - Use a fresh library under an external validation root.
  - Do not commit PDFs or converted artifacts.
  - Record results in `TODO.md` and `docs/zh/TODO.zh.md`.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/converters/mineru_api_batch.py tests/test_mineru_api_batch.py docs/smoke-tests/mineru.md docs/zh/smoke-tests/mineru.zh.md TODO.md docs/zh/TODO.zh.md
  git commit -m "docs: add MinerU batch validation ladder"
  ```

## Chunk 6: Script QED Validation Workflow

### Task 7: Add QED Validation Helper

**Files:**
- Create: `src/paper_cli/validation/__init__.py`
- Create: `src/paper_cli/validation/qed.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_qed_validation.py`
- Docs: `README.md`, `docs/zh/README.zh.md`

- [ ] **Step 1: Decide command shape**
  - Preferred internal command:
    ```bash
    paper validate qed --source /path/to/QED --library-root /path/to/library-root --count 30 --seed 20260525 --converter mineru-local --json
    ```
  - If this feels too product-specific for public CLI, implement as a developer script under `scripts/qed_validation.py` instead.

- [ ] **Step 2: Write failing tests**
  - Sample selection is deterministic by seed.
  - It never deletes the source corpus.
  - It creates a symlink input folder and sample list.
  - It can run in `--dry-run` mode without invoking conversion.
  - It writes a Markdown report with command results and artifact counts.

- [ ] **Step 3: Run tests**
  ```bash
  uv run pytest tests/test_qed_validation.py -q
  ```
  Expected: fails because helper does not exist.

- [ ] **Step 4: Implement helper**
  - Keep destructive cleanup explicit:
    - Only delete test directories matching a generated prefix.
    - Never delete the source corpus path.
  - Use existing CLI functions or subprocess commands consistently.
  - Capture JSON outputs into the report.
  - Support `--no-convert` for import/list/status/doctor-only checks.

- [ ] **Step 5: Run tests**
  ```bash
  uv run pytest tests/test_qed_validation.py -q
  ```
  Expected: pass.

- [ ] **Step 6: Run local dry-run**
  ```bash
  uv run python -m paper_cli validate qed --source /path/to/QED --library-root /path/to/library-root --count 3 --seed 20260525 --no-convert --json
  ```
  Expected: creates sample list, imports 3 papers, doctor passes, no conversion is run.

- [ ] **Step 7: Commit**
  ```bash
  git add src/paper_cli/validation/__init__.py src/paper_cli/validation/qed.py src/paper_cli/cli.py tests/test_qed_validation.py README.md docs/zh/README.zh.md
  git commit -m "feat: script QED validation workflow"
  ```

## Final Verification

- [ ] Run unit and lint checks:
  ```bash
  make verify
  ```
  Expected: all tests pass and ruff reports no issues.

- [ ] Run local MinerU environment doctor:
  ```bash
  PATH="/path/to/mineru/.venv/bin:$PATH" \
  uv run python -m paper_cli --library /path/to/paper-cli-qed-30-retest-20260525 doctor --strict --json
  ```
  Expected: `ok=true`.

- [ ] Run QED scripted dry-run with 3 papers.

- [ ] Run QED scripted full local validation with 30 papers when time allows:
  ```bash
  PATH="/path/to/mineru/.venv/bin:$PATH" \
  uv run python -m paper_cli validate qed \
    --source /path/to/QED \
    --library-root /path/to/library-root \
    --count 30 \
    --seed 20260525 \
    --converter mineru-local \
    --local-backend pipeline \
    --jobs 1 \
    --json
  ```
  Expected: converted 30, failed 0, strict doctor ok, report written.

- [ ] Run cloud batch validation only when network conditions are stable.

- [ ] Update `TODO.md` and `docs/zh/TODO.zh.md` with measured validation results.

## Open Decisions

- Should `paper validate qed` be a public command or a developer-only script? Prefer a script if product-specific commands should stay out of the CLI.
- Should local `auto` jobs ever exceed 1 on macOS? Current evidence says `1` is safest; raise only after controlled validation.
- Should DOI/arXiv fields be added to `paper.yaml` contract now, or stored as identifier candidates until a broader metadata schema pass?
- Should cloud batch become the default converter after successful 100-paper validation, or should `mineru-api` remain default for backward compatibility?
