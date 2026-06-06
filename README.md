# paper-cli

`paper-cli` is a local-first, agent-native literature management CLI.

Its purpose is to make research papers easier for AI agents to manage and read. Instead of treating PDF files as the main working surface, `paper-cli` builds structured paper bundles that contain the copied PDF, MinerU-converted Markdown, extracted images, metadata, conversion state, and indexes.

## Current Status

Local-folder MVP implemented. The current code supports initializing a library, importing local PDFs, converting pending bundles through the serial MinerU API backend, the MinerU precise API batch backend, a local MinerU CLI backend, or fixture output, rebuilding indexes, listing papers, reporting status, running library checks, repairing converted bundles with an OpenAI-compatible AI provider, extracting AI article skeleton summaries from converted Markdown, and building collection-level plus library-level agent memory from existing summary outputs.

Recent real-library hardening added MinerU network retry/backoff, a per-file or per-batch MinerU wait limit, interrupted-conversion job cleanup, a strict doctor mode for batch audits, guards against OCR-damaged MinerU titles causing bad bundle renames, and selectable `mineru-api-batch` / `mineru-local` conversion backends.

The built-in AI repair phase is now usable as a conservative post-conversion repair layer. It can repair metadata, rename bundles from repaired metadata, and patch low-risk Markdown extraction defects. Formula-heavy, table, reference, and math-heavy blocks are recorded as review-only warnings instead of being automatically rewritten.

The built-in AI extract summary phase is usable as a structured reading layer. `paper extract summary` creates block-level summaries, section-level skeletons, and a lightweight knowledge graph under `extracts/summary/`, with `source-map.json` preserving block IDs, line ranges, text hashes, and section paths for future side-by-side reading UIs. When summary extraction writes updated outputs, it now also refreshes the affected collection and library memory automatically.

The built-in AI memory build phase is now usable as a higher-level memory layer. `paper memory build` consumes existing `extracts/summary/summary.json` outputs, skips missing summaries instead of auto-generating them, writes collection memory under collection `_memory/`, writes top-level library memory under library `_memory/`, preserves links back to paper IDs, bundle paths, summary paths, source-map paths, section IDs, and block IDs, and keeps dirty/stale state in `indexes/memory-state.json`.

## Companion Research Plugin

`paper-cli` is intentionally not a general literature search engine. Open-ended literature discovery, paper selection, author/team analysis, and research judgment should remain agent-led.

The planned companion project is a separate sibling repository:

```text
/Users/yuxiangzhang/Documents/program/
  paper-cli/
  paper-research-plugin/
```

`paper-research-plugin` owns topic research, author/team research, single-paper research, research reports, executable import manifests, and ingest orchestration. It calls `paper-cli` as the local backend for import, conversion, summary extraction, inspection, and doctor checks.

The design record lives in this repository because the plugin is tightly coupled to `paper-cli` contracts:

```text
docs/superpowers/specs/2026-06-05-paper-research-plugin-run-manifest-design.md
```

The plugin implementation should initially live outside `src/paper_cli/` and outside the core CLI command surface so the two projects can be published as separate GitHub repositories.

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
paper convert --pending --converter mineru-api-batch --batch-size 20 --jobs 4
paper convert --pending --converter mineru-local --local-backend pipeline --jobs 2
paper convert --pending --dry-run
paper list
paper resolve <id-or-prefix-or-name-or-path>
paper get <paper-id-or-query>
paper inspect <paper-id-or-query>
paper status
paper doctor
paper doctor --strict
paper repair
paper memory build
paper extract summary
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
uv run paper init /path/to/paper-library
uv run paper --library /path/to/paper-library import /path/to/papers --collection "plasma/lwfa" --json
uv run paper --library /path/to/paper-library convert --pending --dry-run --json
uv run paper --library /path/to/paper-library convert --pending --json
uv run paper --library /path/to/paper-library status --json
uv run paper --library /path/to/paper-library doctor --json
uv run paper --library /path/to/paper-library doctor --strict --json
```

During development, prefer `uv run paper ...` from the repository. The package also exposes the console script `paper` when installed in editable mode.

Real MinerU cloud conversion reads the API key from `MINERU_API_KEY`. The default `paper convert --pending` behavior remains the serial `mineru-api` backend. For larger libraries, use `--converter mineru-api-batch`; it submits MinerU precise API batches, caps API upload-link requests at 50 files, uploads/downloads with bounded concurrency, records `batch_id` / `data_id` in `conversion.json`, and resumes an existing running batch before submitting duplicates. `--batch-size` defaults to `20`, and `--jobs` defaults to `4` for cloud upload/download work. Network calls are retried, and long-running remote tasks are bounded by `MINERU_MAX_WAIT_SECONDS`, defaulting to 30 minutes per file or batch.

Local MinerU conversion uses an installed `mineru` executable:

```bash
python3 -m paper_cli --library /path/to/paper-library convert --pending --converter mineru-local --local-backend pipeline --jobs 2 --json
```

`--local-backend` is passed to MinerU as `-b`, for example `pipeline`. The executable and default local settings can also be stored in `paper-cli.yaml`:

```yaml
mineru:
  executable: /Volumes/PHILIPS/programs/mineru/.venv/bin/mineru
  local_backend: pipeline
  local_jobs: auto
```

`local_jobs: auto` is intentionally conservative and currently resolves to one local MinerU process unless `--jobs` or a numeric config value overrides it. The local backend writes the same bundle contract as the cloud backends: `paper.md`, `images/`, `raw/mineru/`, and `conversion.json`.

`paper doctor` checks structural integrity by default. `paper doctor --strict` additionally reports pending or failed conversions, dangling conversion job history, stale running conversions, missing MinerU batch mapping fields, and configured local MinerU executable problems, which is useful after batch conversion runs.

`paper doctor --json` also reports setup diagnostics without printing secrets: library/config presence, MinerU API key availability, local MinerU executable information, and AI provider environment/config availability.

For tests and dry runs, `convert` can use fixture output instead of the network:

```bash
python3 -m paper_cli --library /tmp/lib convert --pending --converter local-fixture --fixture-output /tmp/mineru-fixture --json
```

To plan a conversion without writing bundle files or contacting MinerU:

```bash
uv run paper --library /path/to/paper-library convert --pending --converter mineru-local --dry-run --json
```

The dry-run output includes the effective backend, batch size, jobs, pending bundles, setup diagnostics, and planned write targets.

Agent-facing paper lookup commands:

```bash
uv run paper --library /path/to/paper-library resolve <id-prefix-or-name-or-path> --json
uv run paper --library /path/to/paper-library get <paper-id-or-query> --json
uv run paper --library /path/to/paper-library inspect <paper-id-or-query> --json
```

`resolve` turns a paper ID, ID prefix, title/name fragment, relative path, or bundle path into a single bundle. Ambiguous queries return non-zero with candidate matches. `get` returns the durable `paper.yaml` metadata surface, while `inspect` adds artifact presence plus parsed `conversion.json`, `repair.json`, and extract-summary JSON when present.

For repeatable QED corpus validation, use the local validation helper. It samples PDFs deterministically, creates a symlink input folder and sample list, imports the sample, optionally converts it, runs doctor checks, counts artifacts, and writes a Markdown report under the requested library root:

```bash
python3 -m paper_cli validate qed \
  --source /Volumes/PHILIPS/programs/paper-cache/QED \
  --library-root /Volumes/PHILIPS/programs/paper-cache \
  --count 30 \
  --seed 20260525 \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 1 \
  --replace \
  --json
```

Use `--no-convert` for a fast import/list/doctor validation without running MinerU.

AI repair reads an OpenAI-compatible chat completions provider from environment variables:

```bash
export PAPER_AI_BASE_URL="https://api.openai.com/v1"
export PAPER_AI_API_KEY="..."
export PAPER_AI_MODEL="gpt-5.4-mini"
python3 -m paper_cli --library /path/to/paper-library repair --target metadata --dry-run --json
python3 -m paper_cli --library /path/to/paper-library repair --target markdown --paper sha256:abc --limit 1 --json
python3 -m paper_cli --library /path/to/paper-library repair --json
```

`paper repair` defaults to `--target all`. It can repair metadata in `paper.yaml` and low-risk suspicious Markdown extraction blocks in `paper.md`; applied runs write `repair.json`, create bundle-local backups before file changes, and rebuild `indexes/papers.jsonl`. Use `--paper`, `--collection`, and `--limit` to scope repairs to specific converted bundles. Higher-risk scientific content is preserved and recorded as `review_only` warnings for later inspection; `repair.json` now includes aggregated `markdown.warning_summary` counts by reason together with affected block IDs.

AI extract summary uses the same provider configuration and writes extraction outputs without modifying the paper source files:

```bash
python3 -m paper_cli --library /path/to/paper-library extract summary --dry-run --json
python3 -m paper_cli --library /path/to/paper-library extract summary --workers 16 --json
python3 -m paper_cli --library /path/to/paper-library extract summary --paper-workers 16 --max-requests 500 --retries 2 --json
python3 -m paper_cli --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` defaults to converted bundles that do not already have `extracts/summary/summary.json`. Use `--force` to regenerate existing outputs, `--paper`, `--collection`, or `--limit` to control scope. Concurrency has three controls: `--paper-workers` for paper-level parallelism, `--workers` for per-paper block-batch parallelism, and `--max-requests` as a global provider request cap. `--paper-workers` and `--workers` default to `16`; `--max-requests` defaults to `500`. Per-paper workers are capped to the current paper count, and block workers are capped to the current paper's block-batch count. Provider requests are retried with `--retries` retries, default `2`, with a fixed 10-second wait between attempts. The command writes `summary.json`, `summary.md`, and `source-map.json`, then automatically refreshes the affected collection and library memory when extraction succeeds.

AI memory build uses the same provider configuration but reads only existing summary outputs:

```bash
python3 -m paper_cli --library /path/to/paper-library memory build --dry-run --json
python3 -m paper_cli --library /path/to/paper-library memory build --collection dual-modality --json
python3 -m paper_cli --library /path/to/paper-library memory build --force --json
```

`paper memory build` defaults to converted bundles that already have `extracts/summary/summary.json`. It skips missing summaries and reports them instead of auto-running `paper extract summary`. Collection memory is written to `collections/<collection>/_memory/collection-memory.json`, `collection-memory.md`, and `paper-index.json`. Top-level library memory is written to `_memory/library-memory.json`, `library-memory.md`, and `collection-index.json`. Existing memory outputs are skipped by default and marked stale when source summary hashes no longer match; use `--force` to rebuild them. Library-change commands such as `import`, `convert`, and `repair` mark memory stale in `indexes/memory-state.json`, and successful `extract summary` runs clear and refresh the affected memory automatically.

## Library Shape

```text
paper-library/
  paper-cli.yaml
  collections/
    <collection-path>/
      _memory/
        collection-memory.json
        collection-memory.md
        paper-index.json
      <paper-name>/
        paper.yaml
        original.pdf
        paper.md
        images/
        conversion.json
        repair.json
        extracts/
          summary/
            summary.json
            summary.md
            source-map.json
        backups/
        notes/
          README.md
  inbox/
    <paper-name>/
      paper.yaml
      original.pdf
      paper.md
      images/
      conversion.json
      repair.json
      extracts/
        summary/
          summary.json
          summary.md
          source-map.json
      backups/
      notes/
        README.md
  indexes/
    papers.jsonl
    jobs.jsonl
    memory-state.json
  _memory/
    library-memory.json
    library-memory.md
    collection-index.json
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

See `TODO.md` for the current task list, `docs/superpowers/specs/2026-05-13-paper-cli-mvp-design.md` for the approved MVP design, `docs/superpowers/specs/2026-05-13-paper-cli-engineering-design.md` for the engineering design, `docs/superpowers/specs/2026-05-21-paper-cli-ai-repair-design.md` for the AI repair design, `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md` for the AI extract summary design, `docs/superpowers/specs/2026-06-05-paper-cli-memory-build-design.md` for the AI memory build design, `docs/superpowers/specs/2026-05-23-paper-cli-mineru-conversion-backends-plan.md` for the MinerU conversion backend plan, `docs/development/2026-05-21-ai-repair-suspicious-blocks.md` for the AI repair suspicious-block optimization record, and `docs/contracts/extract-summary-output.md` for the summary artifact contract.

Contract docs:

- `docs/contracts/paper-yaml.md`
- `docs/contracts/conversion-json.md`
- `docs/contracts/cli-json.md`
- `docs/contracts/source-adapters.md`
- `docs/smoke-tests/mineru.md`
- `docs/smoke-tests/ai-repair.md`

Chinese documentation is available under `docs/zh/`.

Local test libraries can be kept under `paper-libraries/`. That directory is ignored by git because it may contain copied PDFs and MinerU outputs.
