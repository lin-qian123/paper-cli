# paper-cli AI Repair Design

## Goal

Add a built-in AI repair layer to `paper-cli` through one user-facing command:

```bash
paper repair
paper repair --target metadata
paper repair --target markdown
paper repair --target all
```

`paper repair` defaults to `--target all` and applies repairs directly. The command should repair both `paper.yaml` metadata and `paper.md` extraction defects while preserving the project's local-first bundle contract.

The AI layer is not a replacement for MinerU or future Zotero-style identifier lookup. It is a review-and-repair layer that uses bounded evidence from each paper bundle to catch obvious metadata and Markdown extraction problems after conversion.

## Non-Goals

- Do not send an entire paper Markdown file to the model in one request.
- Do not rewrite paper content stylistically.
- Do not translate the article.
- Do not change scientific meaning, formulas, tables, or references unless the defect is explicit and local.
- Do not hard-code API keys, model names, or user-specific paths.
- Do not add native Anthropic or Gemini support in the first implementation pass.
- Do not make AI repair part of `import` or `convert` by default.

## Command Behavior

### Default Command

```bash
paper --library /path/to/library repair
```

Default behavior:

- Select converted bundles that contain `paper.yaml` and `paper.md`.
- Run metadata repair and Markdown repair.
- Apply safe changes directly.
- Write a repair record into the bundle.
- Rebuild `indexes/papers.jsonl`.
- Return compact structured output when `--json` is used.

### Target Selection

```bash
paper repair --target metadata
paper repair --target markdown
paper repair --target all
```

`--target all` is the default. `metadata` only updates `paper.yaml`. `markdown` only updates `paper.md`.

### Safety Options

First implementation should include:

```bash
paper repair --dry-run
paper repair --target metadata --dry-run
```

Even though the default applies changes, `--dry-run` is important for tests, debugging, and expensive real-paper runs.

## AI Provider Scope

The first version should support an OpenAI-compatible chat completions provider only. This covers OpenAI-compatible cloud services and local endpoints such as LM Studio, Ollama OpenAI-compatible mode, vLLM, OpenRouter-style routers, and similar providers.

Configuration should support environment variables first:

```bash
PAPER_AI_BASE_URL=https://api.openai.com/v1
PAPER_AI_API_KEY=...
PAPER_AI_MODEL=gpt-4.1-mini
```

Optional library config support can be added under `paper-cli.yaml`:

```yaml
ai:
  provider: openai-compatible
  base_url: https://api.openai.com/v1
  api_key_env: PAPER_AI_API_KEY
  model: gpt-4.1-mini
  temperature: 0
  timeout_seconds: 60
```

Do not store secrets in `paper-cli.yaml`. The config should name an environment variable, not contain the key itself.

## Internal Components

### Provider Layer

New module shape:

```text
src/paper_cli/ai/
  __init__.py
  providers.py
  schema.py
  prompts.py
  repair.py
  markdown_blocks.py
```

Provider responsibilities:

- Read provider configuration from environment and library config.
- Send chat-completions requests.
- Require JSON-only model responses.
- Parse and validate response JSON.
- Surface request errors without corrupting bundle files.

Initial provider protocol:

```python
class AIProvider(Protocol):
    name: str

    def complete_json(self, messages: list[dict], *, schema_name: str) -> dict:
        ...
```

The implementation should use `requests`, which is already a project dependency.

### Repair Record

Each repair run should write:

```text
<paper-bundle>/repair.json
```

This file records the latest repair run. A later version can add append-only history under `indexes/repair-jobs.jsonl`, but the first version can stay per-bundle.

Suggested shape:

```json
{
  "schema_version": 1,
  "repaired_at": "2026-05-21T00:00:00+00:00",
  "provider": "openai-compatible",
  "model": "gpt-4.1-mini",
  "targets": ["metadata", "markdown"],
  "dry_run": false,
  "metadata": {
    "changed": true,
    "changes": [
      {
        "field": "title",
        "old": "Old title",
        "new": "Correct title",
        "confidence": "high",
        "evidence": "The title appears in the first Markdown heading."
      }
    ],
    "warnings": []
  },
  "markdown": {
    "changed": true,
    "blocks_checked": 42,
    "blocks_changed": 3,
    "warnings": []
  }
}
```

## Metadata Repair

Metadata repair should not send the full article to AI. It should build a bounded evidence packet.

### Evidence Packet

Input to the model:

- Current `paper.yaml` metadata.
- `metadata_sources` and `metadata_confidence`.
- Current bundle directory name.
- Source PDF filename from `source.imported_from`.
- The first part of `paper.md`, bounded by character count and paragraph count.
- Detected identifier candidates from the Markdown head, including DOI, arXiv ID, PMID, and ISBN when simple regexes find them.
- Current conversion diagnostics from `conversion.json`.

Suggested limits:

- `markdown_head_max_chars`: 8000
- `markdown_head_max_blocks`: 40

### Model Output

Require strict JSON:

```json
{
  "proposed_metadata": {
    "title": "Correct title",
    "creators": [{"name": "Guo", "role": "author"}],
    "year": 2026,
    "doi": "10.xxxx/example",
    "language": "en"
  },
  "field_changes": [
    {
      "field": "title",
      "old": "Old title",
      "new": "Correct title",
      "confidence": "high",
      "source": "ai-md-head",
      "evidence": "Short evidence quote or explanation"
    }
  ],
  "warnings": []
}
```

### Apply Rules

Only apply metadata field changes when:

- The response is valid JSON.
- The field is supported by `paper.yaml`.
- The new value is non-empty and type-valid.
- The AI confidence is `medium` or `high`.
- Existing confidence is not `high` from `user`.
- Evidence is present for high-impact fields such as title, creators, year, and DOI.

When applied:

- Update `metadata`.
- Set `metadata_sources[field] = "ai-repair"`.
- Set `metadata_confidence[field]` from the AI response.
- Run existing bundle rename logic unless `name_locked` is true.
- Record old and new values in `repair.json`.

## Markdown Repair

Markdown repair should operate on blocks, not full documents.

### Block Splitting

Create a deterministic Markdown block splitter:

- `heading`: lines starting with `#`.
- `paragraph`: contiguous prose lines.
- `formula`: display math blocks and obvious equation blocks.
- `image`: Markdown image references.
- `table`: Markdown table rows.
- `reference`: reference-list blocks after a references heading.
- `raw`: fallback block for unsupported structures.

Each block should have:

```json
{
  "id": "b00042",
  "type": "paragraph",
  "start_line": 120,
  "end_line": 128,
  "text": "..."
}
```

### Candidate Selection

Do not send every block blindly. First version should select suspicious blocks using cheap local checks:

- Very short isolated fragments in prose.
- Repeated page headers or footers.
- Page-number-only lines.
- Broken Markdown image links.
- Heading-level jumps.
- Unclosed display math markers.
- High ratio of unusual replacement characters or mojibake.
- Paragraphs with excessive single-character spacing.

Normal-looking blocks should be left untouched.

### Model Output

For each small batch of suspicious blocks, require JSON:

```json
{
  "block_patches": [
    {
      "block_id": "b00042",
      "action": "replace",
      "old_text": "...",
      "new_text": "...",
      "reason": "Removed repeated page footer.",
      "confidence": "high"
    }
  ],
  "warnings": []
}
```

### Apply Rules

Only apply a block patch when:

- `old_text` exactly matches the current block text.
- The replacement is not empty unless the action is an allowed deletion of page header/footer noise.
- The patch size is local and bounded.
- The block is not a formula/table/reference block unless the defect is simple and explicit.
- Confidence is `medium` or `high`.

Markdown repair should preserve original line endings as much as practical and should never modify `original.pdf`.

## Backups and Reversibility

Because `paper repair` defaults to applying changes, the first implementation must create backups before writing:

```text
<paper-bundle>/backups/
  paper.yaml.<timestamp>.bak
  paper.md.<timestamp>.bak
```

Backups should only be created for files that will actually change.

Do not add a `paper undo-repair` command in the first implementation. Keep backup files and repair records sufficient for manual rollback.

## JSON Output

`paper repair --json` should return:

```json
{
  "ok": true,
  "repaired": [
    {
      "path": "/path/to/bundle",
      "targets": ["metadata", "markdown"],
      "metadata_changed": true,
      "markdown_changed": false,
      "warnings": []
    }
  ],
  "failed": []
}
```

Failures should be per-bundle where possible. One failed bundle should not stop repair for the rest of the library unless provider configuration is missing or invalid.

## Error Handling

Handle these cases explicitly:

- Missing provider config: fail with a clear message and exit code `1`.
- Missing `paper.md`: skip Markdown repair and record a warning.
- Invalid AI JSON: do not modify files; record the error.
- API timeout or HTTP error: do not modify files; record the error.
- Patch mismatch: do not apply that block patch; record a warning.
- Unsupported target value: argparse usage error.

## Testing Strategy

Unit tests:

- Provider config loading from environment and `paper-cli.yaml`.
- OpenAI-compatible request payload shape with mocked `requests.post`.
- JSON response parsing and invalid response errors.
- Metadata evidence packet construction.
- Metadata apply rules, including user/high-confidence protection.
- Markdown block splitter.
- Suspicious block candidate selection.
- Patch apply rules and mismatch rejection.
- Backup creation only when changes are applied.

CLI tests:

- `paper repair --target metadata --dry-run --json`.
- `paper repair --target markdown --dry-run --json`.
- `paper repair --json` default target all.
- Missing provider config failure.
- Per-bundle failure does not corrupt files.

Integration-style tests should use fake providers, not real network calls.

Manual smoke test:

- Create a library under `paper-libraries/ai-repair-live-test`.
- Import and convert one real PDF.
- Set `PAPER_AI_*` environment variables.
- Run `paper repair --json`.
- Verify `paper.yaml`, `paper.md`, `repair.json`, backups, `paper status --json`, and `paper doctor --json`.
- Do not commit copied PDFs, extracted images, raw outputs, or repair backups from live tests.

## Implementation Milestones

### Milestone 1: Provider and Dry-Run Metadata Repair

- Add `paper repair` parser and target argument.
- Add OpenAI-compatible provider.
- Build metadata evidence packet.
- Parse strict JSON repair response.
- Support `--dry-run`.
- Add focused tests.

### Milestone 2: Apply Metadata Repairs

- Apply safe metadata changes to `paper.yaml`.
- Update provenance and confidence.
- Rename bundle using existing naming logic.
- Write `repair.json`.
- Create backups before modification.
- Rebuild index.

### Milestone 3: Markdown Block Repair

- Add Markdown block splitter.
- Add suspicious block detector.
- Batch suspicious blocks into bounded AI requests.
- Apply exact-match block patches.
- Record Markdown repair summary.

### Milestone 4: Documentation and Smoke Test

- Update `README.md`, `TODO.md`, and Chinese docs.
- Add AI repair contract docs if the schema stabilizes.
- Add manual smoke-test checklist.
- Run `make verify`.

## Open Decisions

- Whether `repair.json` should be latest-only or append-only after the first implementation.
- Whether to add a future `paper repair --bundle <path>` selector, or use library-wide repair only.
- Whether to add DOI/Crossref/OpenAlex lookup before AI repair. This is likely valuable, but it should be a separate metadata resolver layer rather than part of the first AI provider milestone.
