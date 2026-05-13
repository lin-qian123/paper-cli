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
  "ok": true,
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": null
}
```

## Current Failure Shape

```json
{
  "ok": false,
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": "MINERU_API_KEY is not set"
}
```

## Field Meanings

- `ok`: whether the latest conversion attempt succeeded.
- `converted_at`: UTC timestamp for when this result was written.
- `error`: `null` on success, diagnostic text on failure.

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

## Planned Compatible Extensions

The engineering version should expand the file into a diagnostic record:

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:01:00+00:00",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

Future readers should tolerate the current minimal shape and ignore unknown fields.
