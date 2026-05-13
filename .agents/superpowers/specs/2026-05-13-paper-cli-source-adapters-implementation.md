# paper-cli Source Adapters Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a small source adapter boundary and make the current local-folder import the reference adapter without changing CLI behavior.

**Architecture:** Keep `paper_cli.importer.import_path()` as the public facade used by the CLI. Move local-folder import orchestration behind `LocalFolderAdapter`, with a `SourceAdapter` protocol for future Zotero, Attanger, BibTeX, and CSL adapters.

**Tech Stack:** Python 3.11, Protocol/dataclass-style lightweight interfaces, existing local filesystem import logic.

---

## File Structure

- Create `src/paper_cli/adapters/__init__.py`.
- Create `src/paper_cli/adapters/base.py`: source adapter protocol and import result type.
- Create `src/paper_cli/adapters/local_folder.py`: local-folder reference adapter wrapping existing import logic.
- Modify `src/paper_cli/importer.py`: keep low-level PDF import helpers and use `LocalFolderAdapter` in `import_path`.
- Add `tests/test_adapters.py`: verify local-folder adapter behavior and source type.
- Update `docs/superpowers/specs/2026-05-13-paper-cli-engineering-design.md` and Chinese mirror if needed.
- Update `TODO.md` and `docs/zh/TODO.zh.md`.

## Chunk 1: Adapter Interface

- [x] Add failing test for `LocalFolderAdapter.import_source()` importing a PDF.
- [x] Create adapter protocol and local-folder adapter.
- [x] Keep existing CLI import tests green.

## Chunk 2: Importer Facade

- [x] Refactor `import_path()` to delegate to `LocalFolderAdapter`.
- [x] Verify duplicate handling and index rebuild still pass.
- [x] Run focused import and adapter tests.

## Chunk 3: Docs And Commit

- [x] Update TODO and engineering docs to mark adapter boundary complete.
- [x] Run `make verify`.
- [x] Commit as `refactor: add source adapter boundary`.
