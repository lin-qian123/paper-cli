# paper-cli

[English](README.md) | [简体中文](README.zh-CN.md)

> Turn PDF piles into agent-readable research libraries.

PDFs are where papers live.
Markdown is where agents can actually work.

`paper-cli` is a local-first, agent-native literature management CLI. It turns local paper collections into durable, inspectable bundles: copied PDFs, MinerU Markdown, extracted images, YAML metadata, JSON state, AI repair records, source-traceable summaries, and layered library memory all live as explicit files on disk.

## Why paper-cli?

Most literature managers are designed for people.

That is the right design for collecting references, reading papers, adding tags, syncing attachments, and producing citations. But an AI agent sees a traditional PDF library very differently:

- A PDF is a layout document, not an agent-native reading surface.
- Agents usually need ad-hoc Python tools, PDF parsers, OCR scripts, or custom skills before they can inspect the actual paper content.
- GUI-first managers often keep important state behind application databases, attachment conventions, or plugin-specific storage.
- Conversion outputs, images, metadata, repair decisions, summaries, and indexes are rarely exposed together as one stable filesystem contract.

`paper-cli` takes a different route: every paper becomes a self-contained directory that an agent can read, check, repair, summarize, and remember without reverse-engineering an application backend.

## What makes it different?

`paper-cli` is not trying to replace Zotero, Papis, OCR engines, or PaperQA-style tools. Those projects solve important problems. `paper-cli` focuses on the layer they usually do not make explicit: a durable local paper substrate for AI agents.

| Tool type | Human-facing library | Agent-readable text | Explicit filesystem contract | AI repair / extraction state | Best role |
| --- | --- | --- | --- | --- | --- |
| Zotero / reference managers | Excellent | Limited | Mostly app-managed | No | Collecting, citing, and organizing references |
| Papis-like CLI libraries | Good | Partial | File-oriented | No | Lightweight human-controlled paper collections |
| PDF parsers / OCR tools | No | Partial | Usually per-run outputs | No | Converting individual PDFs |
| Paper QA / RAG tools | Partial | Internalized | Often index-managed | Partial | Asking questions over documents |
| `paper-cli` | Useful, but secondary | First-class | Yes | Yes | Building durable paper bundles for agents |

The project is built around one practical idea: the paper bundle is the API.

```text
paper bundle = PDF + Markdown + images + YAML metadata + JSON state + AI outputs
```

That means an agent does not need to guess where the paper is, where the figures are, whether conversion failed, which blocks were repaired, what summary was produced, or whether collection memory is stale. The evidence is on disk.

## Layered Agent Memory

`paper-cli` does more than convert PDFs into Markdown. It can turn converted papers into durable memory for future agent work:

1. Per-paper summaries live under `extracts/summary/` with source maps, block IDs, line ranges, text hashes, section paths, and graph source blocks.
2. Collection memory lives under each collection's `_memory/` directory and distills the main themes, methods, evidence, and cross-paper connections of that collection.
3. Library memory lives under the library root `_memory/` directory and gives agents a persistent overview of what the whole paper library contains.

This is intentionally different from a one-off chat summary. The memory files are persistent artifacts. Agents can come back later, inspect what was extracted, trace claims back to source blocks, and build new work on top of a stable research memory instead of rereading every PDF from scratch.

## Status

`paper-cli` is at `v0.1.0` initial preview.

The first release is usable for local PDF libraries and agent workflows:

- Import local PDF files or folders into self-contained paper bundles.
- Convert PDFs with MinerU through serial API, batch API, local CLI, or test fixture backends.
- Preserve `original.pdf`, `paper.md`, `images/`, `paper.yaml`, `conversion.json`, and indexes.
- Run structural checks with `paper doctor` and stricter batch-audit checks with `paper doctor --strict`.
- Repair metadata and low-risk Markdown extraction defects with an OpenAI-compatible AI provider.
- Extract article skeleton summaries with block, section, graph, and source-map traceability.
- Build collection-level and library-level agent memory from existing summary outputs.

This is not yet a full literature manager. Zotero, BibTeX/CSL JSON, full-text search, and review queues are planned for later phases.

## Install

Recommended user install with `pipx`:

```bash
brew install pipx
pipx ensurepath
pipx install "git+https://github.com/lin-qian123/paper-cli.git"
paper --help
```

`pipx` installs `paper-cli` from GitHub into an isolated Python environment and exposes the `paper` command on your shell `PATH`. If `paper` is not found immediately after `pipx ensurepath`, restart your terminal or follow the shell instruction printed by `pipx`.

Alternative install with `pip` inside a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "git+https://github.com/lin-qian123/paper-cli.git"
paper --help
```

After installation, normal usage is always `paper ...`.

Requirements:

- Python 3.11+
- `pipx` for the recommended user install
- `MINERU_API_KEY` for MinerU cloud conversion
- An OpenAI-compatible provider for AI repair, summary extraction, and memory build

## Quick Start

```bash
paper init /path/to/paper-library
paper --library /path/to/paper-library import /path/to/pdfs --collection "plasma/qed" --json
paper --library /path/to/paper-library convert --pending --dry-run --json
paper --library /path/to/paper-library convert --pending --json
paper --library /path/to/paper-library doctor --strict --json
paper --library /path/to/paper-library list --json
```

The default cloud backend is `mineru-api-batch`. It provides bounded parallelism and automatically splits PDFs above the MinerU page limit into 195-page parts. Use `--converter mineru-api` only when the legacy serial API path is explicitly required.

## Configuration

MinerU cloud conversion reads:

```bash
export MINERU_API_KEY="..."
export MINERU_API_BASE="https://mineru.net/api/v4"  # optional
export MINERU_MAX_WAIT_SECONDS=7200                 # optional
```

AI commands read an OpenAI-compatible chat completions provider:

```bash
export PAPER_AI_BASE_URL="https://api.openai.com/v1"
export PAPER_AI_API_KEY="..."
export PAPER_AI_MODEL="gpt-5.4-mini"
```

Local MinerU settings can be stored in `paper-cli.yaml`:

```yaml
mineru:
  executable: /path/to/mineru
  local_backend: pipeline
  local_jobs: auto
```

Libraries synchronized through services with strict filename or path limits can use sync-safe naming:

```yaml
naming:
  rename_on_convert: false
  sanitize:
    max_length: 86
    ascii_slug: true
```

`ascii_slug` applies to newly imported bundle names. Set `rename_on_convert: false` when an existing library already has stable directory identifiers that conversion must preserve.

Secrets should stay in environment variables or uncommitted local config files.

## Core Commands

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper list
paper resolve <id-or-prefix-or-name-or-path>
paper get <paper-id-or-query>
paper inspect <paper-id-or-query>
paper status
paper doctor
paper doctor --strict
```

Agent-facing commands support `--json` wherever structured output is useful.

## Conversion

Cloud batch conversion:

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --batch-size 20 \
  --jobs 4 \
  --json
```

`mineru-api-batch`:

- caps upload-link requests at 50 files;
- uploads and downloads with bounded concurrency;
- records `batch_id`, `data_id`, and remote state in `conversion.json`;
- resumes existing running batches when possible;
- splits PDFs above MinerU API's page limit into smaller PDFs before upload.

Long-PDF splitting defaults to 195 pages per part, leaving headroom below MinerU API's 200-page service ceiling:

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --max-pages-per-part 195 \
  --json
```

Split outputs are merged back into the original bundle:

```text
paper.md
images/part-001/
images/part-002/
raw/mineru/part-001/
raw/mineru/part-002/
conversion.json
```

`conversion.json.raw.split_parts` records page ranges and per-part remote diagnostics. Split conversions keep existing `paper.yaml` metadata and leave uncertain title/author cleanup to AI metadata repair.

Local MinerU conversion:

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 2 \
  --json
```

Fixture conversion for tests and dry runs:

```bash
paper --library /tmp/lib convert \
  --pending \
  --converter local-fixture \
  --fixture-output /tmp/mineru-fixture \
  --json
```

## AI Repair

```bash
paper --library /path/to/paper-library repair --target metadata --dry-run --json
paper --library /path/to/paper-library repair --target markdown --paper sha256:abc --limit 1 --json
paper --library /path/to/paper-library repair --json
```

`paper repair` defaults to `--target all`.

It can:

- repair metadata in `paper.yaml`;
- rename bundles after metadata repair;
- patch low-risk suspicious Markdown extraction defects;
- create bundle-local backups before writes;
- record the latest run in `repair.json`.

Higher-risk scientific content, formulas, tables, references, and long uncertain OCR prose are recorded as warnings instead of being automatically rewritten.

## Summary Extraction

```bash
paper --library /path/to/paper-library extract summary --dry-run --json
paper --library /path/to/paper-library extract summary --paper-workers 16 --workers 16 --max-requests 500 --json
paper --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` reads converted bundles and writes:

```text
extracts/summary/summary.json
extracts/summary/summary.md
extracts/summary/source-map.json
```

It does not modify source PDFs, `paper.md`, `paper.yaml`, or `repair.json`. Source traceability is preserved with block IDs, line ranges, text hashes, section paths, section block IDs, and graph source block IDs. The goal is not to produce a disposable abstract; it is to create a structured, source-grounded reading layer that later agents can inspect and reuse.

## Memory Build

```bash
paper --library /path/to/paper-library memory build --dry-run --json
paper --library /path/to/paper-library memory build --collection plasma/qed --json
paper --library /path/to/paper-library memory build --force --json
```

`paper memory build` consumes existing summary outputs only. It turns source-grounded per-paper summaries into collection-level and library-level memory that agents can reuse across sessions. It writes:

```text
collections/<collection>/_memory/collection-memory.json
collections/<collection>/_memory/collection-memory.md
collections/<collection>/_memory/paper-index.json
_memory/library-memory.json
_memory/library-memory.md
_memory/collection-index.json
```

Library-changing commands mark memory stale, and successful summary extraction refreshes affected collection and library memory automatically. This gives agents a durable map of the library: not just where files are, but what the papers are about, how collections relate, and which sources support those claims.

## Library Layout

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
        repair.json
        extracts/
          summary/
            summary.json
            summary.md
            source-map.json
        backups/
        notes/
          README.md
      _memory/
        collection-memory.json
        collection-memory.md
        paper-index.json
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

## Data And Privacy

`paper-cli` is local-first: bundle metadata, converted Markdown, images, repair records, summaries, and indexes are written to your chosen local library directory.

External services are used when you choose commands that require them:

- MinerU cloud conversion uploads PDFs or split PDF parts to MinerU.
- AI repair, summary extraction, and memory build send bounded text/evidence packets to the configured OpenAI-compatible provider.

Do not use cloud conversion or AI commands on sensitive PDFs unless you are comfortable with the configured provider receiving that content.

## Validation

The current release has been validated with:

- `uv run --extra dev pytest -q`
- `uv run --extra dev ruff check src tests`
- QED corpus `mineru-api-batch` validation with 519 PDFs
- targeted long-PDF split validation for 242-, 270-, and 226-page PDFs
- real-provider smoke tests for AI repair, summary extraction, and memory build

Latest release details are in [CHANGELOG.md](CHANGELOG.md).

## Documentation

Contracts:

- [paper-yaml.md](docs/contracts/paper-yaml.md)
- [conversion-json.md](docs/contracts/conversion-json.md)
- [cli-json.md](docs/contracts/cli-json.md)
- [extract-summary-output.md](docs/contracts/extract-summary-output.md)
- [source-adapters.md](docs/contracts/source-adapters.md)

Smoke tests:

- [mineru.md](docs/smoke-tests/mineru.md)
- [ai-repair.md](docs/smoke-tests/ai-repair.md)

Development history and open work are tracked in [TODO.md](TODO.md). Chinese documentation is available under `docs/zh/`.

## Development

```bash
git clone git@github.com:lin-qian123/paper-cli.git
cd paper-cli
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
paper --help
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
make verify
```

`uv run ...` is a development convenience for running commands from the repository. User-facing examples use the installed `paper` command.

Local test libraries can be kept under `paper-libraries/`; that directory is ignored by git because it may contain copied PDFs and generated MinerU outputs.

## License

MIT. See [LICENSE](LICENSE).
