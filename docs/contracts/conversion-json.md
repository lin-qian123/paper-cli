# `conversion.json` Contract

`conversion.json` records the latest conversion result for one paper bundle. It is written beside `paper.yaml` and `paper.md`.

## Location

```text
<paper-bundle>/conversion.json
```

The file exists after a conversion attempt has run.

## Current Success Shape

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "attempt": 1,
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:01:00+00:00",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

## Current Failure Shape

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": false,
  "state": "failed",
  "attempt": 1,
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": "MINERU_API_KEY is not set",
  "raw_output_dir": null,
  "markdown": "paper.md",
  "images": "images"
}
```

## Field Meanings

- `schema_version`: integer schema version. Current value is `1`.
- `converter`: converter name, such as `mineru` or `local-fixture`.
- `ok`: whether the latest conversion attempt succeeded.
- `state`: latest conversion state. Current values are `done` or `failed`.
- `attempt`: conversion attempt number for this bundle. Failed bundles are retried with the next attempt number.
- `submitted_at`: UTC timestamp immediately before converter execution starts.
- `converted_at`: UTC timestamp for when this result was written.
- `error`: `null` on success, diagnostic text on failure.
- `raw_output_dir`: converter raw-output directory relative to the bundle, or `null`.
- `markdown`: Markdown output path relative to the bundle.
- `images`: images directory path relative to the bundle.

## Bundle Output Contract

When conversion succeeds, the bundle should contain:

```text
paper.md
images/
conversion.json
raw/
  mineru/
```

`paper.md` and `images/` are the primary agent reading surface. MinerU sidecar files such as `layout.json`, `*_content_list.json`, and `*_origin.pdf` belong under `raw/mineru/`.

## Job History

`indexes/jobs.jsonl` is an append-only conversion event log. Each conversion attempt writes a start event and a finish event.

```jsonl
{"event":"conversion-started","at":"2026-05-13T00:00:00+00:00","paper_id":"sha256:...","bundle_path":"inbox/Example","converter":"mineru","attempt":1,"state":"running"}
{"event":"conversion-finished","at":"2026-05-13T00:01:00+00:00","paper_id":"sha256:...","bundle_path":"inbox/Example","converter":"mineru","attempt":1,"state":"done","ok":true}
```

For failed conversions, the finish event uses `state: "failed"`, `ok: false`, and includes `error`.

Future readers should ignore unknown fields.
