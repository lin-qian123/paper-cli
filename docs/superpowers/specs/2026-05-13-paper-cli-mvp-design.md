# paper-cli MVP Design

Date: 2026-05-13

## Purpose

`paper-cli` is a local-first, agent-native literature management CLI. It helps AI agents manage and read literature by converting PDF-centered collections into structured paper bundles with Markdown text, extracted images, metadata, conversion state, and rebuildable indexes.

The MVP focuses on building a reliable local literature library skeleton. It does not try to replace Zotero for human reading or PDF annotation. It gives agents a stable filesystem and CLI contract for import, conversion, naming, listing, status inspection, and diagnosis.

## Scope

The first version supports local PDF folder import only.

Included:

- Initialize a `paper-cli` library.
- Import one PDF or a folder of PDFs.
- Copy each PDF into a paper bundle.
- Create and update `paper.yaml`.
- Convert PDFs with MinerU.
- Store `paper.md` and `images/` beside `original.pdf`.
- Use metadata-first naming.
- Let users configure the naming template.
- Automatically rename bundles after MinerU conversion improves metadata.
- Maintain rebuildable JSONL indexes.
- Provide status and doctor commands.

Deferred:

- Zotero import.
- Attanger-specific attachment mapping.
- BibTeX / CSL JSON import.
- Other literature manager adapters.
- Bidirectional sync.
- GUI.
- Full-text search UI.
- Automated literature review generation.
- Complex knowledge graph features.

## Technology Strategy

The MVP should be implemented in Python. This is a pragmatic MVP choice, not a permanent product identity. The first phase needs fast iteration around local files, PDF metadata extraction, MinerU HTTP integration, YAML/JSONL persistence, and tests; Python is the most direct fit for those jobs and matches the existing MinerU workflow experience.

The long-term system should remain language-neutral. The durable API is the filesystem contract: paper bundle layout, `paper.yaml`, `conversion.json`, JSONL indexes, CLI commands, structured `--json` output, and exit codes. These contracts should be explicit enough that a Rust implementation can replace or wrap the Python MVP later.

Rust is a strong candidate for later larger-scope development, especially if `paper-cli` grows into a widely distributed CLI with high-volume indexing, concurrent job orchestration, stricter reliability requirements, and cross-platform packaging. The trigger for revisiting Rust should be stabilized product contracts, not early uncertainty.

## Design Principles

1. Keep paper bundles self-contained.
2. Copy PDFs into the managed library by default.
3. Never modify source PDFs in place.
4. Use stable paper IDs independent of folder names.
5. Treat folder names as presentation and organization, not identity.
6. Keep MinerU output as the authoritative extracted reading surface.
7. Persist conversion status and failures.
8. Make indexes rebuildable from paper bundles.
9. Keep source adapters thin and optional.
10. Avoid user-specific assumptions in the core.

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
        notes/
          README.md
  inbox/
    <paper-name>/
      paper.yaml
      original.pdf
      paper.md
      images/
      conversion.json
      notes/
        README.md
  indexes/
    papers.jsonl
    jobs.jsonl
```

`collections/` stores classified papers. `inbox/` stores imported papers without a chosen collection. Each paper directory is a paper bundle.

The MVP intentionally keeps `original.pdf`, `paper.md`, and `images/` at the same level. This makes the common agent workflow short and direct. A later multi-extractor version can migrate to nested paths such as `source/original.pdf` and `extracted/mineru/paper.md`.

## Commands

### `paper init <library-dir>`

Create a managed library:

- Create the library directory.
- Write `paper-cli.yaml`.
- Create `collections/`, `inbox/`, and `indexes/`.
- Write empty index files.

### `paper import <pdf-or-folder> --collection <path>`

Import one PDF or recursively import PDFs from a folder:

- Scan PDFs.
- Compute stable IDs.
- Extract fast metadata from PDF metadata and filename patterns.
- Render an initial paper name from the naming template.
- Sanitize the name for the filesystem.
- Create `collections/<path>/<paper-name>/`.
- Copy the PDF as `original.pdf`.
- Write `paper.yaml`.
- Write or update indexes.
- Mark conversion as `pending`.

### `paper import <pdf-or-folder> --inbox`

Same import behavior, but the destination root is `inbox/`.

### `paper convert --pending`

Convert all pending papers:

- Find papers where `status.conversion` is `pending` or retryable.
- Send `original.pdf` to MinerU.
- Poll conversion status.
- Download and extract output.
- Normalize the main Markdown file to `paper.md`.
- Normalize extracted figures to `images/`.
- Write `conversion.json`.
- Extract better metadata from MinerU Markdown where possible.
- Re-render the configured paper name.
- Automatically rename the whole bundle if the rendered name changes and `name_locked` is false.
- Record rename history in `paper.yaml`.
- Rebuild indexes.

### `paper list`

List papers in the library. MVP output should include:

- ID or short ID.
- Current collection path.
- Current name.
- Conversion status.
- Metadata completeness.

### `paper status`

Show aggregate state:

- Total papers.
- Imported papers.
- Converted papers.
- Failed conversions.
- Pending conversions.
- Papers with incomplete metadata.
- Papers whose names changed after conversion.

### `paper doctor`

Validate the library:

- Missing `original.pdf`.
- Missing `paper.yaml`.
- Missing `paper.md` after a done conversion.
- Broken or missing `images/`.
- Invalid YAML.
- Duplicate IDs.
- Stale indexes.
- Failed conversions.
- Folder names inconsistent with metadata when `name_locked` is false.

## Paper Metadata

Initial `paper.yaml` example:

```yaml
schema_version: 1
id: "sha256:abc123..."
name: "Vallieres et al. - 2025 - High average-flux laser-driven neutron source"
name_locked: false
previous_names: []
collection: "plasma/lwfa"

metadata:
  title: "High average-flux laser-driven neutron source"
  creators:
    - name: "Vallieres"
      role: "author"
  year: 2025
  language: "en"
  doi: null

source:
  type: "local-folder"
  imported_from: "/absolute/path/to/source.pdf"
  copied_pdf: "original.pdf"
  imported_at: "2026-05-13T00:00:00+08:00"

status:
  import: "done"
  conversion: "pending"
  metadata: "partial"
  naming: "fast"

naming:
  template: "default"
  rendered_from:
    - "creators"
    - "year"
    - "title"
  last_renamed_at: null
```

After conversion:

```yaml
status:
  import: "done"
  conversion: "done"
  metadata: "complete"
  naming: "metadata"

previous_names:
  - "high-average-flux-laser-driven-neutron-source"

naming:
  template: "default"
  last_renamed_at: "2026-05-13T00:10:00+08:00"
```

## Naming

Default naming template:

```text
{{if language == "zh"}}
{{ firstCreator suffix=" - " }}
{{elseif language == "zh-CN"}}
{{ firstCreator suffix=" - " }}
{{else}}
{{creators  max="1" suffix=" et al. - "}}
{{ endif }}
{{ year suffix=" - " }}
{{ title truncate="100" }}
```

The template is stored in `paper-cli.yaml` and can be changed by users.

Rendered names must be sanitized before becoming folder names:

- Remove or replace path separators.
- Remove control characters.
- Normalize whitespace.
- Trim leading and trailing punctuation and spaces.
- Enforce a configurable maximum length.
- Resolve duplicates by appending a counter or short ID.

## Import And Rename Flow

The MVP uses a fast import followed by automatic post-conversion rename.

Import:

1. Copy the PDF into a destination paper bundle.
2. Use fast metadata and filename parsing to render an initial name.
3. Persist `paper.yaml` with `status.conversion = pending`.

Convert:

1. Run MinerU.
2. Write `paper.md` and `images/`.
3. Extract better metadata from converted text.
4. Re-render the paper name.
5. If the new name differs and `name_locked` is false, move the entire bundle.
6. Record old names in `previous_names`.
7. Rebuild indexes.

If the target name already exists, append a suffix such as `-2` or a short ID.

If `name_locked: true`, do not rename automatically. Instead mark `status.naming = review`.

## MinerU Conversion

The MVP should wrap MinerU behind an internal conversion adapter.

The adapter should:

- Read credentials from environment variables or non-committed config.
- Upload the PDF.
- Poll status.
- Download the ZIP result.
- Extract the main Markdown and images.
- Normalize the main Markdown to `paper.md`.
- Normalize images to `images/`.
- Write `conversion.json`.
- Return structured success or failure.

No API keys should be hard-coded.

## Indexes

`indexes/papers.jsonl` is a convenience index, not the source of truth. It can be rebuilt from `paper.yaml` files.

Each line should include:

- `id`
- `name`
- `collection`
- `path`
- `title`
- `creators`
- `year`
- `language`
- `status`

`indexes/jobs.jsonl` records conversion job summaries and failures.

## Error Handling

Import failures:

- Leave the source PDF untouched.
- Do not create half-written bundles when avoidable.
- If a bundle was partially created, mark it clearly.

Conversion failures:

- Write `conversion.json` with error state.
- Keep `original.pdf`.
- Keep partial output only if useful and clearly marked.
- Allow retry through a later command.

Rename failures:

- Do not lose the bundle.
- Keep the old path if move fails.
- Record the attempted name and error.
- Rebuild indexes only after successful move.

## Testing Strategy

Focused tests should cover:

- Naming template rendering.
- Chinese vs non-Chinese creator formatting.
- Filename sanitization.
- Duplicate name handling.
- Stable ID generation.
- Import idempotency.
- Bundle layout creation.
- Post-conversion rename behavior.
- `name_locked` behavior.
- Index rebuild from bundle metadata.
- Doctor checks for missing files and stale indexes.

MinerU network calls should be behind an adapter so tests can use fake converter outputs.

## Phase 2

Zotero support should be implemented as a source adapter, not as a core assumption.

Future adapters:

- Zotero read-only SQLite import.
- Zotero local API import.
- Zotero internal storage resolver.
- Zotero linked-file resolver.
- Attanger-style attachment-root resolver.
- BibTeX import.
- CSL JSON import.

The core must only require a resolved PDF path and metadata. It should not care how the PDF was discovered.

## Open Questions

1. Should indexes remain JSONL-only for the MVP?
2. How much metadata extraction should run before MinerU conversion?
3. Should a local fallback extractor exist for metadata only?
4. Should `paper convert --pending` process files serially first, or include limited concurrency in the MVP?
5. When should the project evaluate a Rust rewrite or Rust CLI wrapper after the file and CLI contracts stabilize?
