# CLI JSON Contract

Every user-facing command should support `--json`. JSON output is for agents and scripts, so it must stay valid, compact, and stable.

## Global Rules

- JSON is printed to stdout.
- Human-oriented output may change, but JSON shape should remain compatible.
- Successful commands return exit code `0`.
- `doctor` returns exit code `1` when it finds validation issues.
- Invalid CLI usage follows argparse behavior, normally exit code `2`.

## `init`

Command:

```bash
python3 -m paper_cli init /path/to/library --json
```

Output:

```json
{
  "ok": true,
  "library": "/path/to/library"
}
```

## `import`

Command:

```bash
python3 -m paper_cli --library /path/to/library import /path/to/papers --inbox --json
```

Output:

```json
{
  "ok": true,
  "imported": [
    "/path/to/library/inbox/Example et al. - 2026 - Title"
  ]
}
```

`imported` contains newly imported bundle paths. Duplicate PDFs skipped by SHA-256 are currently omitted from this list.

## `convert`

Command:

```bash
python3 -m paper_cli --library /path/to/library convert --pending --json
```

Output:

```json
{
  "ok": true,
  "converted": [
    "/path/to/library/inbox/Guo et al. - 2026 - Title"
  ]
}
```

`converted` contains successfully converted bundle paths after any automatic rename.

## `list`

Command:

```bash
python3 -m paper_cli --library /path/to/library list --json
```

Output:

```json
{
  "papers": [
    {
      "id": "sha256:...",
      "name": "Guo et al. - 2026 - Title",
      "collection": null,
      "status": {
        "import": "done",
        "conversion": "done",
        "metadata": "complete",
        "naming": "metadata"
      },
      "path": "/path/to/library/inbox/Guo et al. - 2026 - Title"
    }
  ]
}
```

## `status`

Command:

```bash
python3 -m paper_cli --library /path/to/library status --json
```

Output:

```json
{
  "total": 1,
  "converted": 1,
  "failed": 0,
  "pending": 0,
  "incomplete_metadata": 0,
  "renamed": 1
}
```

## `doctor`

Command:

```bash
python3 -m paper_cli --library /path/to/library doctor --json
```

Success output:

```json
{
  "ok": true,
  "issues": []
}
```

Issue output:

```json
{
  "ok": false,
  "issues": [
    {
      "code": "missing-original-pdf",
      "path": "/path/to/bundle",
      "message": "Missing original.pdf"
    }
  ]
}
```

Known issue codes currently include:

- `invalid-paper-yaml`
- `duplicate-id`
- `missing-original-pdf`
- `missing-paper-md`
- `stale-index`
