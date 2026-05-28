# CLI JSON Contract

Every user-facing command should support `--json`. JSON output is for agents and scripts, so it must stay valid, compact, and stable.

## Global Rules

- JSON is printed to stdout.
- Human-oriented output may change, but JSON shape should remain compatible.
- Successful commands return exit code `0`.
- `doctor` returns exit code `1` when it finds validation issues.
- `resolve`, `get`, and `inspect` return exit code `1` when the query is missing or ambiguous.
- Invalid CLI usage follows argparse behavior, normally exit code `2`.
- JSON errors must not include API keys, bearer tokens, cookies, or full secret-bearing headers.

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

Dry-run command:

```bash
paper --library /path/to/library convert --pending --converter mineru-local --dry-run --json
```

Output:

```json
{
  "ok": true,
  "dry_run": true,
  "converter": "mineru-local",
  "batch_size": 20,
  "jobs": 1,
  "local_backend": "pipeline",
  "pending_count": 1,
  "pending": [
    {
      "id": "sha256:...",
      "name": "Example et al. - 2026 - Title",
      "collection": null,
      "status": {
        "conversion": "pending"
      },
      "path": "/path/to/library/inbox/Example et al. - 2026 - Title",
      "relative_path": "inbox/Example et al. - 2026 - Title"
    }
  ],
  "diagnostics": {
    "configured_executable": "mineru"
  },
  "planned_writes": [
    "paper.md",
    "images/",
    "raw/mineru/",
    "conversion.json",
    "indexes/papers.jsonl",
    "indexes/jobs.jsonl"
  ]
}
```

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
      "path": "/path/to/library/inbox/Guo et al. - 2026 - Title",
      "relative_path": "inbox/Guo et al. - 2026 - Title"
    }
  ]
}
```

## `resolve`

Command:

```bash
paper --library /path/to/library resolve "Guo" --json
```

Success output:

```json
{
  "ok": true,
  "query": "Guo",
  "paper": {
    "id": "sha256:...",
    "name": "Guo et al. - 2026 - Title",
    "collection": null,
    "status": {
      "conversion": "done"
    },
    "path": "/path/to/library/inbox/Guo et al. - 2026 - Title",
    "relative_path": "inbox/Guo et al. - 2026 - Title"
  },
  "reasons": [
    "name-substring"
  ]
}
```

Ambiguous output:

```json
{
  "ok": false,
  "query": "Guo",
  "error": "ambiguous",
  "matches": []
}
```

`query` may be a paper ID, ID prefix, exact or partial name/title, relative path, absolute bundle path, or a file path inside a bundle. Callers should treat `id` as the stable identifier and `path` as the current filesystem location.

## `get`

Command:

```bash
paper --library /path/to/library get sha256:abc --json
```

Output:

```json
{
  "ok": true,
  "paper": {
    "id": "sha256:...",
    "name": "Guo et al. - 2026 - Title",
    "collection": null,
    "status": {},
    "path": "/path/to/library/inbox/Guo et al. - 2026 - Title",
    "relative_path": "inbox/Guo et al. - 2026 - Title",
    "metadata": {},
    "metadata_sources": {},
    "metadata_confidence": {},
    "source": {},
    "naming": {},
    "name_locked": false,
    "previous_names": [],
    "schema_version": 1
  }
}
```

## `inspect`

Command:

```bash
paper --library /path/to/library inspect sha256:abc --json
```

Output:

```json
{
  "ok": true,
  "paper": {
    "id": "sha256:...",
    "relative_path": "inbox/Guo et al. - 2026 - Title",
    "metadata": {}
  },
  "artifacts": {
    "paper_yaml": {
      "path": "/path/to/bundle/paper.yaml",
      "exists": true,
      "type": "file",
      "bytes": 1024
    },
    "paper_md": {
      "path": "/path/to/bundle/paper.md",
      "exists": true,
      "type": "file",
      "bytes": 2048
    }
  },
  "conversion": null,
  "repair": null,
  "extract_summary": {
    "summary": null,
    "source_map": null
  }
}
```

`inspect` is read-only. If sidecar JSON is present but invalid, the corresponding field contains an `error` string instead of raising an uncaught exception.

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
  "issues": [],
  "diagnostics": {
    "library": {
      "path": "/path/to/library",
      "config_path": "/path/to/library/paper-cli.yaml",
      "config_exists": true,
      "inbox_exists": true,
      "collections_exists": true,
      "indexes_exists": true
    },
    "mineru": {
      "api_key_env": "MINERU_API_KEY",
      "api_key_available": false,
      "configured_executable": "mineru",
      "configured_local_backend": null,
      "configured_local_jobs": "auto",
      "configured_max_wait_seconds": null
    },
    "ai": {
      "provider": "openai-compatible",
      "api_key_env": "PAPER_AI_API_KEY",
      "api_key_available": false,
      "base_url_configured": false,
      "model_configured": false
    }
  }
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
- `missing-library-config`
- `duplicate-id`
- `missing-original-pdf`
- `missing-paper-md`
- `stale-index`
- `invalid-creators`
- `failed-conversion`
- `pending-conversion`
- `invalid-job-json`
- `dangling-conversion-job`
- `invalid-conversion-json`
- `missing-batch-conversion-mapping`
- `stale-running-conversion`
- `invalid-conversion-timestamp`
- `missing-mineru-local-executable`
- `invalid-mineru-local-executable`

## `repair`

Missing provider configuration:

```json
{
  "ok": false,
  "error": "Missing AI provider configuration: PAPER_AI_API_KEY, PAPER_AI_MODEL or ai.model",
  "repaired": [],
  "failed": []
}
```

Success output:

```json
{
  "ok": true,
  "target": "all",
  "dry_run": false,
  "repaired": [],
  "failed": []
}
```

`repaired` and `failed` contain bundle-local result objects. Applied repair writes are recorded in each bundle's `repair.json`.

## `extract summary`

Dry-run output:

```json
{
  "ok": true,
  "dry_run": true,
  "planned": [],
  "extracted": [],
  "skipped": [],
  "failed": []
}
```

Write output uses the same top-level shape, with generated bundle results under `extracted`. The command writes `extracts/summary/summary.json`, `summary.md`, and `source-map.json`; those file contracts are intentionally separate from this CLI envelope contract.

## `validate qed`

Command:

```bash
paper validate qed --source /path/to/QED --library-root /tmp --no-convert --json
```

Output:

```json
{
  "ok": true,
  "library": "/tmp/paper-cli-qed-...",
  "report": "/tmp/paper-cli-qed-...-test-report.md",
  "sampled": 3,
  "imported": 3,
  "converted": 0,
  "failed": 0,
  "pending": 3,
  "incomplete_metadata": 0,
  "renamed": 0,
  "artifact_counts": {},
  "issues": []
}
```
