# Real AI Repair Smoke Test

Use this checklist to validate `paper repair` with a real OpenAI-compatible provider without committing PDFs, extracted images, backups, or model output.

## Preconditions

- A test library under `paper-libraries/` contains at least one converted bundle.
- The bundle has `paper.yaml`, `paper.md`, `original.pdf`, and `conversion.json`.
- Provider settings are available through environment variables or `paper-cli.yaml`.
- Secrets are stored in environment variables, not in `paper-cli.yaml`.

Check:

```bash
test -n "$PAPER_AI_API_KEY" && echo "PAPER_AI_API_KEY=set"
test -n "$PAPER_AI_MODEL" && echo "PAPER_AI_MODEL=$PAPER_AI_MODEL"
```

Optional provider config in `paper-cli.yaml`:

```yaml
ai:
  provider: openai-compatible
  base_url: https://api.openai.com/v1
  api_key_env: PAPER_AI_API_KEY
  model: gpt-4.1-mini
  temperature: 0
  timeout_seconds: 60
```

## Run

Choose the local test library:

```bash
library="paper-libraries/ai-repair-live-test"
```

Inspect current state:

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" list --json
```

Dry-run metadata repair first:

```bash
uv run python -m paper_cli --library "$library" repair --target metadata --dry-run --json
```

Apply repair:

```bash
uv run python -m paper_cli --library "$library" repair --json
```

Validate after repair:

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" doctor --json
uv run python -m paper_cli --library "$library" list --json
```

## Expected Result

- Dry-run reports proposed changes but does not write `repair.json` or `backups/`.
- Applied run writes `repair.json` in each repaired bundle.
- Applied metadata changes set `metadata_sources.<field>` to `ai-repair`.
- Backups exist only for files that changed:
  - `backups/paper.yaml.<timestamp>.bak`
  - `backups/paper.md.<timestamp>.bak`
- `indexes/papers.jsonl` reflects any renamed bundle or metadata update.
- `paper doctor --json` reports `{"ok": true, "issues": []}`.

## What Not To Commit

Do not commit:

- `paper-libraries/`
- copied PDFs
- extracted images
- `repair.json` from live papers
- `backups/`
- provider API keys or user-specific absolute paths

Record only a short validation summary in `TODO.md`.
