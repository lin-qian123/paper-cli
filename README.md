# paper-cli

`paper-cli` is a local-first, agent-native literature management CLI.

Its purpose is to make research papers easier for AI agents to manage and read. Instead of treating PDF files as the main working surface, `paper-cli` builds structured paper bundles that contain the copied PDF, MinerU-converted Markdown, extracted images, metadata, conversion state, and indexes.

## Current Status

Local-folder MVP implemented. The current code supports initializing a library, importing local PDFs, converting pending bundles through MinerU or fixture output, rebuilding indexes, listing papers, reporting status, and running library checks.

The approved MVP direction is:

- Import local PDF files or folders.
- Copy each PDF into a self-contained paper bundle.
- Convert PDFs with MinerU.
- Store `original.pdf`, `paper.md`, `images/`, `paper.yaml`, and conversion state together.
- Use metadata-first naming with a configurable naming template.
- Import quickly first, then automatically rename bundles after conversion provides better metadata.
- Defer Zotero and other source adapters to a later phase.

## Technology Direction

The MVP is implemented in Python because it is the fastest path for PDF metadata extraction, MinerU API integration, YAML/JSONL persistence, and test-driven iteration.

The long-term architecture should remain language-neutral. The stable contract is the paper bundle format, metadata files, indexes, CLI commands, structured `--json` output, and exit codes.

Rust is a strong candidate for later large-scale development, especially if the project needs a polished single-binary CLI, stronger concurrency, faster indexing, and easier cross-platform distribution. The MVP should therefore avoid exposing Python internals as the product API.

## MVP Commands

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper list
paper status
paper doctor
```

## Install For Development

```bash
uv run --extra dev pytest -v
```

You can also install the project in editable mode:

```bash
python3 -m pip install -e ".[dev]"
```

Preferred local verification:

```bash
make verify
```

## Basic Workflow

```bash
python3 -m paper_cli init /path/to/paper-library
python3 -m paper_cli --library /path/to/paper-library import /path/to/papers --collection "plasma/lwfa" --json
python3 -m paper_cli --library /path/to/paper-library convert --pending --json
python3 -m paper_cli --library /path/to/paper-library status --json
python3 -m paper_cli --library /path/to/paper-library doctor --json
```

Real MinerU conversion reads the API key from `MINERU_API_KEY`.

For tests and dry runs, `convert` can use fixture output instead of the network:

```bash
python3 -m paper_cli --library /tmp/lib convert --pending --fixture-output /tmp/mineru-fixture --json
```

## Library Shape

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

See `TODO.md` for the current task list, `docs/superpowers/specs/2026-05-13-paper-cli-mvp-design.md` for the approved MVP design, `docs/superpowers/specs/2026-05-13-paper-cli-engineering-design.md` for the engineering design, and `docs/superpowers/specs/2026-05-21-paper-cli-ai-repair-design.md` for the planned AI repair layer.

Contract docs:

- `docs/contracts/paper-yaml.md`
- `docs/contracts/conversion-json.md`
- `docs/contracts/cli-json.md`
- `docs/contracts/source-adapters.md`
- `docs/smoke-tests/mineru.md`

Chinese documentation is available under `docs/zh/`.

Local test libraries can be kept under `paper-libraries/`. That directory is ignored by git because it may contain copied PDFs and MinerU outputs.
