# CLAUDE.md

## Build & Test

```bash
make verify          # pytest -v + ruff check (always run before committing)
uv run --extra dev pytest -v -k "pattern"
uv run --extra dev ruff check src tests
```

## Project

`paper-cli` — local-first, agent-native literature management CLI (Python).

- **Entry point:** `src/paper_cli/cli.py` (argparse, no Click/Typer)
- **Config:** `paper-cli.yaml` in library root + env vars for secrets
- **Key env vars:** `PAPER_AI_BASE_URL`, `PAPER_AI_API_KEY`, `PAPER_AI_MODEL`, `MINERU_API_KEY`
- **Secrets:** `.env` at project root is gitignored, loaded in tests only
- **Package manager:** uv with `--extra dev` for test/lint deps

## Key directories

| Path | Purpose |
|---|---|
| `src/paper_cli/ai/` | AI repair, extract summary, memory build, provider, markdown blocks |
| `src/paper_cli/converters/` | `mineru.py`, `mineru_api_batch.py`, `mineru_local.py` |
| `tests/` | 127 tests, pytest with fake providers and mocked HTTP |
| `docs/contracts/` | CLI JSON output and artifact shape contracts |
| `docs/superpowers/specs/` | Approved design documents |

## Architecture notes

- Each paper is a self-contained **bundle** dir with `original.pdf`, `paper.md`, `images/`, `paper.yaml`, `conversion.json`
- Stable paper IDs are SHA-256 of PDF content; folder names can change via metadata-driven rename
- Indexes (`indexes/papers.jsonl`, `indexes/jobs.jsonl`) are rebuildable from bundles
- AI features use OpenAI-compatible chat completions (`src/paper_cli/ai/providers.py`)
- Markdown repair splits into blocks, classifies with `auto_repair` / `review_only` / `structural_warning` policies
- MinerU has 3 backends: serial API, cloud batch, local CLI — all normalize to the same bundle contract

## Memory stale tracking

`import`, `convert`, and non-dry-run `repair` mark affected memory stale in `indexes/memory-state.json`. `extract summary` auto-refreshes memory on success.

## AGENTS.md

Project philosophy, scope decisions, and data principles are in the repo-root `AGENTS.md`. See `TODO.md` for pending work and validation log.
