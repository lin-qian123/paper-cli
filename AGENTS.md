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

## MVP Scope

Implement the first usable skeleton around:

- `paper init`
- `paper import`
- `paper convert`
- `paper list`
- `paper status`
- `paper doctor`

The MVP imports local PDF files or folders, copies PDFs into the library, converts pending papers with MinerU, writes `paper.md` and `images/`, updates metadata, and automatically renames paper bundles after better metadata becomes available.

## Development Rules

- Before creating new features or changing behavior, use Superpowers brainstorming for design and obtain user approval.
- Maintain these three project files during project work:
  - `AGENTS.md` for project instructions and collaboration rules.
  - `README.md` for project overview, status, and usage.
  - `TODO.md` for pending work, development notes, blockers, and next steps.
- Keep implementation incremental and testable.
- Do not hard-code API keys or user-specific paths.
- Read secrets from environment variables or explicit config files that are not committed.
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
- Update `TODO.md` after each meaningful development pass.
- Write larger approved designs under `docs/superpowers/specs/`.
