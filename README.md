# paper-cli

`paper-cli` is a planned local-first, agent-native literature management CLI.

Its purpose is to make research papers easier for AI agents to manage and read. Instead of treating PDF files as the main working surface, `paper-cli` builds structured paper bundles that contain the copied PDF, MinerU-converted Markdown, extracted images, metadata, conversion state, and indexes.

## Current Status

Design phase. No implementation code exists yet.

The approved MVP direction is:

- Import local PDF files or folders.
- Copy each PDF into a self-contained paper bundle.
- Convert PDFs with MinerU.
- Store `original.pdf`, `paper.md`, `images/`, `paper.yaml`, and conversion state together.
- Use metadata-first naming with a configurable naming template.
- Import quickly first, then automatically rename bundles after conversion provides better metadata.
- Defer Zotero and other source adapters to a later phase.

## Planned MVP Commands

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper list
paper status
paper doctor
```

## Planned Library Shape

```text
paper-library/
  paper-cli.yaml
  collections/
    <collection-path>/
      <paper-name>/
        paper.yaml
        original.pdf
        paper.md
        images/
        conversion.json
        notes/
          README.md
  inbox/
    <paper-name>/
      paper.yaml
      original.pdf
      paper.md
      images/
      conversion.json
      notes/
        README.md
  indexes/
    papers.jsonl
    jobs.jsonl
```

## Naming

The default naming format is metadata-first and user-configurable:

```text
{{if language == "zh"}}
{{ firstCreator suffix=" - " }}
{{elseif language == "zh-CN"}}
{{ firstCreator suffix=" - " }}
{{else}}
{{creators  max="1" suffix=" et al. - "}}
{{ endif }}
{{ year suffix=" - " }}
{{ title truncate="100" }}
```

The importer first creates a usable destination from fast metadata or file-name parsing. After MinerU conversion, `paper-cli` extracts better metadata and automatically renames the whole paper bundle unless the name is locked.

## Source Adapters

MVP:

- Local folder import.

Later phases:

- Zotero read-only import.
- Zotero linked-file and storage resolvers.
- Attanger-style attachment root mapping.
- BibTeX / CSL JSON import.
- Other literature managers.

## Development Notes

See `TODO.md` for the current task list and `docs/superpowers/specs/2026-05-13-paper-cli-mvp-design.md` for the approved MVP design.
