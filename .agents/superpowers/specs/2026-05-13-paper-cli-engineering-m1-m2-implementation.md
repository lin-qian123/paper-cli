# paper-cli Engineering M1-M2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first engineering foundation for `paper-cli`: lightweight quality tooling, a single verification command, contract documentation, and a real MinerU smoke-test checklist.

**Architecture:** Keep the current Python MVP implementation. Do not add new product features or change core command behavior unless required by linting. Treat `paper.yaml`, `conversion.json`, and CLI JSON output as the product contracts to document before further expansion.

**Tech Stack:** Python 3.11, setuptools, uv, pytest, ruff, Markdown documentation.

---

## File Structure

- Modify `pyproject.toml`: add `ruff` to the dev extra and add minimal Ruff settings.
- Create `Makefile`: provide `make test`, `make lint`, `make format`, and `make verify`.
- Create `docs/contracts/paper-yaml.md`: document the current and near-term `paper.yaml` contract.
- Create `docs/contracts/conversion-json.md`: document current conversion status and planned diagnostic fields.
- Create `docs/contracts/cli-json.md`: document JSON output for implemented commands.
- Create `docs/smoke-tests/mineru.md`: document manual real-MinerU validation using `paper-libraries/`.
- Create Chinese mirrors under `docs/zh/contracts/` and `docs/zh/smoke-tests/`.
- Modify `README.md` and `docs/zh/README.zh.md`: link engineering contract docs and verification command.
- Modify `TODO.md` and `docs/zh/TODO.zh.md`: mark completed engineering tasks and keep next tasks visible.

## Chunk 1: Tooling

### Task 1: Add Ruff And Verification Commands

**Files:**
- Modify: `pyproject.toml`
- Create: `Makefile`

- [x] **Step 1: Add Ruff to dev dependencies**
  Add `ruff>=0.8.0` to `[project.optional-dependencies].dev`.

- [x] **Step 2: Add minimal Ruff config**
  Configure `line-length = 100`, `target-version = "py311"`, and a conservative lint selection that catches import and obvious syntax/name issues.

- [x] **Step 3: Create Makefile**
  Add these commands:
  - `make test`
  - `make lint`
  - `make format`
  - `make verify`

- [x] **Step 4: Run lint**
  Run: `make lint`
  Expected: either PASS or focused style findings.

- [x] **Step 5: Fix style findings**
  Use `ruff check --fix` or targeted manual edits. Do not refactor unrelated code.

- [x] **Step 6: Run verification**
  Run: `make verify`
  Expected: tests and lint pass.

## Chunk 2: Contract Documentation

### Task 2: Document File And CLI Contracts

**Files:**
- Create: `docs/contracts/paper-yaml.md`
- Create: `docs/contracts/conversion-json.md`
- Create: `docs/contracts/cli-json.md`
- Create: `docs/zh/contracts/paper-yaml.zh.md`
- Create: `docs/zh/contracts/conversion-json.zh.md`
- Create: `docs/zh/contracts/cli-json.zh.md`

- [x] **Step 1: Document `paper.yaml`**
  Include required fields, current meanings, rename behavior, and planned metadata provenance fields.

- [x] **Step 2: Document `conversion.json`**
  Include current fields, success/failure examples, and planned diagnostic expansion.

- [x] **Step 3: Document CLI JSON output**
  Cover implemented commands: `init`, `import`, `convert`, `list`, `status`, and `doctor`.

- [x] **Step 4: Add Chinese mirrors**
  Keep Chinese docs faithful to the English contract docs, not a looser summary.

## Chunk 3: Real MinerU Smoke Test

### Task 3: Document Manual Validation

**Files:**
- Create: `docs/smoke-tests/mineru.md`
- Create: `docs/zh/smoke-tests/mineru.zh.md`

- [x] **Step 1: Write the smoke-test checklist**
  Include environment checks, local library path, import, convert, status, doctor, expected bundle shape, and what not to commit.

- [x] **Step 2: Include known validation library convention**
  Use `paper-libraries/<name>` and mention that `paper-libraries/` is git-ignored.

## Chunk 4: README And TODO Sync

### Task 4: Update Project Status Docs

**Files:**
- Modify: `README.md`
- Modify: `TODO.md`
- Modify: `docs/zh/README.zh.md`
- Modify: `docs/zh/TODO.zh.md`
- Modify: `docs/zh/README.md`

- [x] **Step 1: Add verification command to README**
  Mention `make verify` as the preferred local gate.

- [x] **Step 2: Link contract and smoke-test docs**
  Add concise references without turning README into a full spec.

- [x] **Step 3: Update TODO**
  Mark M1/M2 completed only after `make verify` passes.

## Chunk 5: Final Verification And Commit

### Task 5: Verify And Commit

**Files:**
- All modified files.

- [x] **Step 1: Run verification**
  Run: `make verify`
  Expected: PASS.

- [x] **Step 2: Check git status**
  Run: `git status --short`
  Expected: only intentional tracked changes; `paper-libraries/` remains ignored.

- [x] **Step 3: Commit implementation**
  Commit message: `chore: add engineering quality gates and contracts`.
