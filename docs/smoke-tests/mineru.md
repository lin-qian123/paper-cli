# Real MinerU Smoke Test

Use this checklist to validate the real MinerU path without committing user PDFs or extracted outputs.

## Preconditions

- `MINERU_API_KEY` is set in the environment.
- A small local PDF is available.
- The working directory is the `paper-cli` repository root.
- `paper-libraries/` is ignored by git.

Check:

```bash
test -n "$MINERU_API_KEY" && echo "MINERU_API_KEY=set"
git status --short --ignored paper-libraries
```

## Run

Choose a local test library name:

```bash
library="paper-libraries/desktop-live-test"
pdf="/absolute/path/to/paper.pdf"
rm -rf "$library"
```

Initialize and import:

```bash
uv run python -m paper_cli init "$library" --json
uv run python -m paper_cli --library "$library" import "$pdf" --inbox --json
```

Convert with real MinerU:

```bash
uv run python -m paper_cli --library "$library" convert --pending --json
```

Validate:

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" doctor --json
uv run python -m paper_cli --library "$library" list --json
```

## Expected Result

- `status` reports `failed: 0`.
- `doctor` reports `{"ok": true, "issues": []}`.
- The bundle contains:
  - `original.pdf`
  - `paper.yaml`
  - `paper.md`
  - `images/`
  - `conversion.json`
  - `raw/mineru/`
  - `notes/README.md`
- MinerU sidecar files are under `raw/mineru/`, not the bundle root.

## What Not To Commit

Do not commit:

- `paper-libraries/`
- copied PDFs
- extracted images
- MinerU raw output
- user-specific absolute paths in generated bundle files

Record only the validation summary in `TODO.md`.
