# Contributing

Thanks for your interest in `paper-cli`.

This project is in an initial preview stage. Contributions should keep the core design local-first, agent-readable, and file-contract driven.

## Development Setup

```bash
git clone git@github.com:lin-qian123/paper-cli.git
cd paper-cli
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
```

Editable install:

```bash
python3 -m pip install -e ".[dev]"
paper --help
```

## Verification

Before submitting changes, run:

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
```

For conversion-related changes, prefer adding focused unit tests plus a small local fixture test. Real MinerU or AI-provider smoke tests should use non-sensitive PDFs and should not commit generated libraries.

## Project Conventions

- Keep the bundle contract explicit and documented.
- Prefer structured `--json` output for agent-facing commands.
- Do not hard-code user paths, API keys, or provider secrets.
- Do not modify source PDFs in place.
- Keep AI repair conservative; avoid automatic rewrites of high-risk scientific content.
- Update `README.md`, `TODO.md`, and relevant contract docs when behavior or user-facing commands change.

## Pull Requests

Good pull requests include:

- a clear summary of behavior changes;
- focused tests;
- documentation updates when needed;
- validation commands and results.

Avoid unrelated refactors in feature or bug-fix pull requests.
