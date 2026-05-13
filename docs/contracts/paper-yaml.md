# `paper.yaml` Contract

`paper.yaml` is the canonical record for one paper bundle. Folder names may change, indexes may be rebuilt, and converter sidecars may be regenerated, but `paper.yaml` is the stable source of truth for the paper identity and current state.

## Location

```text
<paper-bundle>/paper.yaml
```

Every valid paper bundle must contain this file.

## Current Schema

```yaml
schema_version: 1
id: sha256:<pdf-sha256>
name: Guo et al. - 2026 - Example Title
name_locked: false
previous_names: []
collection: plasma/lwfa
metadata:
  title: Example Title
  creators:
    - name: Guo
      role: author
  year: 2026
  language: en
  doi: null
source:
  type: local-folder
  imported_from: /absolute/source.pdf
  copied_pdf: original.pdf
  imported_at: "2026-05-13T00:00:00+00:00"
status:
  import: done
  conversion: pending
  metadata: partial
  naming: fast
naming:
  template: default
  rendered_from:
    - creators
    - year
    - title
  last_renamed_at: null
```

## Field Meanings

- `schema_version`: integer schema version. Current value is `1`.
- `id`: stable paper ID. MVP uses `sha256:<hash-of-source-pdf>`.
- `name`: current bundle directory name.
- `name_locked`: when `true`, automatic rename must not move the bundle.
- `previous_names`: prior bundle names after automatic renames.
- `collection`: collection path relative to `collections/`, or `null` for inbox papers.
- `metadata`: current best-known bibliographic metadata.
- `source`: import source information.
- `status`: workflow state summary for import, conversion, metadata, and naming.
- `naming`: naming-template bookkeeping.

## Status Values

Current status values are intentionally small:

- `status.import`: `done`
- `status.conversion`: `pending`, `done`, or `failed`
- `status.metadata`: `partial` or `complete`
- `status.naming`: `fast`, `metadata`, or `review`

## Rename Rules

After conversion, `paper-cli` may extract better metadata and rename the whole bundle. The stable `id` must not change. The old folder name should be appended to `previous_names`, and `naming.last_renamed_at` should be updated.

If `name_locked` is `true`, the bundle must not be renamed automatically. The naming status should move to `review` when better metadata would otherwise trigger a rename.

## Planned Compatible Extensions

The next schema refinement should add provenance and confidence without removing current fields:

```yaml
metadata_sources:
  title: mineru
  creators: filename-title-prefix
  year: filename
metadata_confidence:
  title: high
  creators: medium
  year: medium
```

Callers should ignore unknown top-level fields so future schema additions remain backward-compatible.
