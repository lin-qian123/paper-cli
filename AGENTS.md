# AGENTS.md

## Project Goal

Build `paper-cli` as a local-first, agent-native literature management CLI.

The project should make research papers directly manageable by AI agents by turning PDF-centric paper collections into structured paper bundles containing copied PDFs, MinerU Markdown, extracted images, metadata, conversion state, and durable indexes.

## Core Direction

- Prioritize CLI workflows that agents can call reliably.
- Treat the converted Markdown and image directory as the primary reading surface for agents.
- Keep each paper as a self-contained bundle.
- Preserve the original copied PDF beside the converted Markdown and images.
- Use metadata-first naming with a user-configurable naming template.
- Support local-folder PDF import in the MVP.
- Keep Zotero, Attanger, BibTeX, CSL JSON, and other source adapters as later phases.
- Keep generated extraction artifacts separate from later notes, summaries, classifications, and reviews.

## Technology Direction

- Use Python for the MVP because the first phase is dominated by filesystem operations, PDF metadata extraction, MinerU API integration, YAML/JSONL persistence, and fast test iteration.
- Keep the architecture language-neutral. The durable product contract is the paper bundle layout, `paper.yaml`, `conversion.json`, JSONL indexes, stable exit codes, and structured CLI output.
- Treat Rust as the preferred candidate for later large-scale engineering once the product contracts stabilize, especially for a robust distributable CLI, high-volume indexing, concurrent conversion orchestration, and cross-platform packaging.
- Do not let Python internals become the long-term API. Keep adapters, file formats, and CLI behavior explicit enough that a Rust implementation can replace or wrap the Python MVP later.
- Add `--json` output to user-facing commands early so agents can depend on structured output instead of parsing prose.

## MVP Scope

Implement the first usable skeleton around:

- `paper init`
- `paper import`
- `paper convert`
- `paper list`
- `paper status`
- `paper doctor`

The MVP imports local PDF files or folders, copies PDFs into the library, converts pending papers with MinerU, writes `paper.md` and `images/`, updates metadata, and automatically renames paper bundles after better metadata becomes available.

## Current Post-MVP AI Scope

`paper repair` is the first built-in AI layer. It should stay bounded and review-oriented:

- Use OpenAI-compatible chat completions providers only until another provider family is explicitly designed.
- Read provider settings from environment variables or `paper-cli.yaml`, and read secrets from environment variables only.
- Repair metadata and obvious Markdown extraction defects from local bundle evidence; do not translate, summarize, or stylistically rewrite papers.
- Create bundle-local backups before applying changes and record each applied run in `repair.json`.
- Keep full-paper AI passes, identifier lookup services, and automatic repair during import/convert out of this first AI layer unless a later design approves them.

`paper extract summary` is the second built-in AI layer. It should remain an extraction layer, not a repair layer:

- Read only converted bundles with `paper.md`; do not modify source PDFs, `paper.md`, `paper.yaml`, or `repair.json`.
- Generate article skeleton outputs under `extracts/summary/`: `summary.json`, `summary.md`, and `source-map.json`.
- Preserve source traceability through stable block IDs, line ranges, text hashes, section paths, section `block_ids`, and graph `source_block_ids`.
- Use CLI-internal provider concurrency for block-batch summaries, then aggregate section summaries and a conservative lightweight graph.
- Skip non-main content such as references, footnotes, funding, copyright/license text, page numbers, obvious OCR noise, pure formulas, pure tables, and pure images.

## Development Rules

- Before creating new features or changing behavior, use Superpowers brainstorming for design and obtain user approval.
- Maintain these three project files during project work:
  - `AGENTS.md` for project instructions and collaboration rules.
  - `README.md` for project overview, status, and usage.
  - `TODO.md` for pending work, development notes, blockers, and next steps.
- Keep implementation incremental and testable.
- Do not hard-code API keys or user-specific paths.
- Read secrets from environment variables or explicit config files that are not committed.
- For this project, API/AI-provider validation may load the project-root `.env` file directly, for example with `set -a; source .env; set +a`, but never print secret values or commit the `.env` file.
- Prefer clear filesystem contracts over hidden application state.
- Avoid destructive operations on user PDF libraries.
- Never modify a source PDF in place.
- If a rename or migration is needed, move the whole paper bundle and record the rename history.

## Data Principles

- Every paper must have a stable ID independent of its current folder name.
- Folder names may change after metadata extraction; IDs must not.
- Indexes should be rebuildable from paper bundles.
- Conversion status must be persisted, not only printed to the terminal.
- Failed conversions must leave enough state for diagnosis and retry.
- User-controlled name locks must be respected.

## Documentation Expectations

- Update `README.md` when project positioning, commands, install steps, or current status changes.
- If `README.zh-CN.md` exists, treat `README.md` as the source-of-truth README and keep `README.zh-CN.md` as a content-equivalent Simplified Chinese translation. The Chinese README may use natural Chinese phrasing, but it must preserve the same user-facing positioning, section structure, install steps, command examples, status, validation notes, limitations, and product claims unless a deliberate bilingual-doc update changes both files together.
- Update `TODO.md` after each meaningful development pass.
- Write larger approved designs under `docs/superpowers/specs/`.
