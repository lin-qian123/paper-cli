# TODO

## Current Phase

Design and planning.

## Approved MVP

- [x] Define project as an agent-native local literature management CLI.
- [x] Choose local-folder import as the first source adapter.
- [x] Default to copying PDFs into each paper bundle.
- [x] Use metadata-first naming with user-configurable templates.
- [x] Import first, then automatically rename after MinerU conversion improves metadata.
- [x] Defer Zotero and Attanger support to phase 2.
- [x] Create Chinese documentation under `docs/zh/`.
- [ ] Review and approve the written MVP spec.
- [ ] Create an implementation plan after spec approval.

## Implementation Backlog

- [ ] Initialize Python project structure.
- [ ] Choose packaging and CLI framework.
- [ ] Implement `paper init`.
- [ ] Implement library config loading from `paper-cli.yaml`.
- [ ] Implement local PDF scanner.
- [ ] Implement PDF copying into paper bundles.
- [ ] Implement stable paper ID generation.
- [ ] Implement fast metadata extraction.
- [ ] Implement configurable naming renderer.
- [ ] Implement filesystem-safe name sanitization and duplicate handling.
- [ ] Implement MinerU conversion adapter.
- [ ] Persist `conversion.json`.
- [ ] Persist `paper.yaml`.
- [ ] Implement post-conversion metadata refinement.
- [ ] Implement automatic bundle rename with rename history.
- [ ] Implement index rebuild.
- [ ] Implement `paper list`.
- [ ] Implement `paper status`.
- [ ] Implement `paper doctor`.
- [ ] Add focused tests for naming, bundle layout, import idempotency, and rename behavior.

## Phase 2 Ideas

- [ ] Zotero read-only import adapter.
- [ ] Attachment resolver abstraction.
- [ ] Attanger-style attachment-root mapping.
- [ ] BibTeX / CSL JSON import.
- [ ] Agent classification based on converted Markdown.
- [ ] Review queue for ambiguous classification or naming.
- [ ] Search and retrieval over converted Markdown.

## Blockers / Open Questions

- Decide the implementation language and CLI framework.
- Decide whether the first MinerU integration should reuse existing scripts or wrap a new cleaner client.
- Decide how much metadata extraction to do before MinerU conversion.
- Decide whether indexes remain JSONL only in MVP or also include SQLite later.
