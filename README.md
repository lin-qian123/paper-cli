# paper-cli

`paper-cli` is a local-first, agent-native literature management CLI.

It turns PDF collections into structured paper bundles that AI agents can inspect reliably: copied PDFs, MinerU Markdown, extracted images, metadata, conversion state, indexes, repair records, summaries, and library memory all live in explicit files on disk.

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

For development or local use from the repository:

```bash
git clone git@github.com:lin-qian123/paper-cli.git
cd paper-cli
uv run paper --help
```

Editable install:

```bash
python3 -m pip install -e ".[dev]"
paper --help
```

Requirements:

- Python 3.11+
- `uv` for the recommended development workflow
- `MINERU_API_KEY` for MinerU cloud conversion
- An OpenAI-compatible provider for AI repair, summary extraction, and memory build

## Quick Start

```bash
uv run paper init /path/to/paper-library
uv run paper --library /path/to/paper-library import /path/to/pdfs --collection "plasma/qed" --json
uv run paper --library /path/to/paper-library convert --pending --dry-run --json
uv run paper --library /path/to/paper-library convert --pending --converter mineru-api-batch --json
uv run paper --library /path/to/paper-library doctor --strict --json
uv run paper --library /path/to/paper-library list --json
```

The default cloud backend is serial `mineru-api`. For larger libraries, use `mineru-api-batch`.

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
uv run paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-api-batch \
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
uv run paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-api-batch \
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
uv run paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 2 \
  --json
```

Fixture conversion for tests and dry runs:

```bash
uv run paper --library /tmp/lib convert \
  --pending \
  --converter local-fixture \
  --fixture-output /tmp/mineru-fixture \
  --json
```

## AI Repair

```bash
uv run paper --library /path/to/paper-library repair --target metadata --dry-run --json
uv run paper --library /path/to/paper-library repair --target markdown --paper sha256:abc --limit 1 --json
uv run paper --library /path/to/paper-library repair --json
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
uv run paper --library /path/to/paper-library extract summary --dry-run --json
uv run paper --library /path/to/paper-library extract summary --paper-workers 16 --workers 16 --max-requests 500 --json
uv run paper --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` reads converted bundles and writes:

```text
extracts/summary/summary.json
extracts/summary/summary.md
extracts/summary/source-map.json
```

It does not modify source PDFs, `paper.md`, `paper.yaml`, or `repair.json`. Source traceability is preserved with block IDs, line ranges, text hashes, section paths, section block IDs, and graph source block IDs.

## Memory Build

```bash
uv run paper --library /path/to/paper-library memory build --dry-run --json
uv run paper --library /path/to/paper-library memory build --collection plasma/qed --json
uv run paper --library /path/to/paper-library memory build --force --json
```

`paper memory build` consumes existing summary outputs only. It writes:

```text
collections/<collection>/_memory/collection-memory.json
collections/<collection>/_memory/collection-memory.md
collections/<collection>/_memory/paper-index.json
_memory/library-memory.json
_memory/library-memory.md
_memory/collection-index.json
```

Library-changing commands mark memory stale, and successful summary extraction refreshes affected collection and library memory automatically.

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
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
make verify
```

Local test libraries can be kept under `paper-libraries/`; that directory is ignored by git because it may contain copied PDFs and generated MinerU outputs.

## License

MIT. See [LICENSE](LICENSE).
