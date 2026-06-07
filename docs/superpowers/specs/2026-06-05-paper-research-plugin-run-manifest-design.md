# paper research plugin run-manifest design

Date: 2026-06-05

## Status

This document records the approved direction for a future `paper-cli` companion plugin. The plugin should help an agent conduct literature research, produce a research report, create an executable import manifest, and optionally run the import/conversion/summary workflow against a `paper-cli` library.

This is a design document only. It does not implement the plugin, add new `paper-cli` commands, or change the current bundle contract.

## Repository Boundary

This spec lives in the `paper-cli` repository because the plugin is tightly coupled to `paper-cli` contracts. The plugin implementation should initially live outside the `paper_cli` Python package and outside the core CLI command surface.

Recommended local layout:

```text
/path/to/workspace/
  paper-cli/
  paper-research-plugin/
```

The two directories should be treated as separate Git repositories and can be published as two separate GitHub repositories. `paper-cli` is the execution backend and file-contract owner. `paper-research-plugin` is the agent workflow layer.

## Goal

Build a `paper research` plugin around a run-manifest workflow:

```text
research question
  -> agent-led literature discovery
  -> research report
  -> executable import manifest
  -> scripted paper-cli ingest
  -> converted and summarized bundles
  -> optional synthesis of relations, categories, differences, and reading priority
```

The plugin should use Codex or another capable agent for open-ended discovery and judgment. `paper-cli` should remain the local-first system of record for imported papers, converted Markdown, images, metadata, indexes, and extraction artifacts.

## Core Position

The project should not make `paper-cli` a general literature search engine in the core CLI.

Modern agents already have strong search and browsing capabilities, and different research tasks need different search strategies. The durable value for `paper-cli` is the local bundle contract and agent-readable artifacts. The plugin should therefore bridge agent research into that contract through standardized run directories, manifests, logs, and scripts.

## Non-Goals

The first design does not include:

- A built-in `paper search` command in `paper-cli`.
- A universal search index or hosted literature database.
- Automatic bypass of paywalls, institution login, or complex captcha flows.
- Zotero bidirectional sync.
- A mandatory knowledge graph for every import run.
- A requirement that every selected paper must have an available PDF before it can appear in a report.
- Open-ended research judgment inside deterministic scripts.
- Changes to the current `paper.yaml`, `conversion.json`, or `extracts/summary/` contracts unless a later implementation plan explicitly requires them.

## Plugin Shape

The plugin should contain multiple skills plus shared schemas, scripts, and templates:

```text
paper-research-plugin/
  skills/
    topic-research/
      SKILL.md
    author-team-research/
      SKILL.md
    single-paper-research/
      SKILL.md
    paper-cli-ingest/
      SKILL.md
    library-synthesis/
      SKILL.md

  shared/
    schemas/
      research-run.schema.json
      import-manifest.schema.json
      paper-relations.schema.json
      reading-plan.schema.json
    scripts/
      run_ingest.py
      validate_manifest.py
      resolve_metadata.py
      fetch_open_access_pdf.py
      export_run_summary.py
    templates/
      research-report.md
      reading-plan.md
      run-log.md
```

The research-entry skills define how an agent investigates a problem. The shared ingest and synthesis skills define how the selected result set is written into `paper-cli`.

## Research Entry Skills

### topic-research

Use when the user wants to understand a direction, field, question, method family, or emerging topic.

The skill should:

- Clarify the research boundary and intended depth.
- Search for key reviews, surveys, tutorials, landmark papers, recent papers, and competing approaches.
- Use reviews as central orientation points when suitable.
- Expand from review references, citing papers, related work, and recent updates.
- Distinguish background, seminal, representative, recent, controversial, and optional papers.
- Produce a field map and reading path.

Typical report-specific sections:

- Field map.
- Review-centered entry points.
- Historical development.
- Method or topic branches.
- Key controversies and open problems.
- Recent progress.

### author-team-research

Use when the user wants to understand an author, team, lab, institution, or collaboration cluster.

The skill should:

- Resolve the target author/team identity and disambiguate names where needed.
- Build a publication timeline.
- Identify representative works, recurring topics, and topic shifts.
- Map collaborators, institutions, venues, and research lineages.
- Compare early, middle, and recent work where enough data exists.
- Identify papers worth importing for understanding the author or team.

Typical report-specific sections:

- Author or team profile.
- Publication timeline.
- Representative papers.
- Collaboration network.
- Topic migration.
- Influence and follow-up work.

### single-paper-research

Use when the user starts from one seed paper.

The skill should:

- Resolve the seed paper metadata.
- Examine references for upstream foundations.
- Examine citing papers for downstream influence.
- Search similar papers, replications, critiques, code, datasets, and follow-up work.
- Identify what must be read before the seed paper and what should be read after it.
- Position the seed paper inside a small local literature map.

Typical report-specific sections:

- Seed paper role.
- Upstream references.
- Downstream citing papers.
- Similar and contrasting papers.
- Reproduction or code ecosystem.
- Reading expansion path.

## Shared Ingest Skill

`paper-cli-ingest` should take a run directory and manifest, then execute the deterministic part of the workflow.

The default completion target is:

```text
import + convert + extract summary
```

That means a successfully processed paper should usually have:

```text
paper.yaml
original.pdf
paper.md
images/
conversion.json
extracts/summary/summary.json
extracts/summary/source-map.json
```

The skill should prefer the shared script:

```bash
python3 shared/scripts/run_ingest.py /path/to/research-run/import-manifest.json
```

It should also keep an agent-executable path available. If the script fails or the user wants direct control, the agent may manually run `paper-cli` commands, update the manifest, and resume.

## Shared Synthesis Skill

`library-synthesis` should be optional in the first version.

It should operate after papers have been imported and summarized. It can read `paper.yaml`, `paper.md`, `summary.json`, `source-map.json`, and the research run evidence to produce:

- `paper-relations.json`
- `reading-plan.md`
- relationship sections in `research-report.md`
- optional category or priority updates in the run metadata

This stage should be explicitly requested or enabled with a flag such as:

```bash
python3 shared/scripts/run_ingest.py import-manifest.json --synthesize
```

The plugin should not require this stage for a run to count as successfully ingested.

## Research Run Directory

Every research task should create one run directory:

```text
research-runs/
  2026-06-05-laser-plasma-qed/
    research-run.json
    research-report.md
    import-manifest.json
    paper-relations.json
    reading-plan.md
    sources.jsonl
    run-log.md
    artifacts/
      downloaded-pdfs/
      metadata/
      search-results/
```

### research-run.json

`research-run.json` is the run-level control record.

Suggested fields:

```json
{
  "schema_version": 1,
  "run_id": "2026-06-05-laser-plasma-qed",
  "created_at": "2026-06-05T00:00:00+08:00",
  "research_type": "topic",
  "question": "How is strong-field QED studied in laser-plasma experiments?",
  "library": "/path/to/paper-library",
  "default_collection": "plasma/qed/review",
  "status": "planned"
}
```

Allowed `research_type` values for the first version:

- `topic`
- `author_team`
- `single_paper`

Allowed run statuses:

- `planned`
- `researching`
- `manifest_ready`
- `ingesting`
- `ingested`
- `synthesizing`
- `complete`
- `needs_agent_review`
- `failed`

### research-report.md

The shared report structure should be:

```text
# <research title>

## 1. Question and Scope
## 2. Search Strategy and Evidence
## 3. Core Papers
## 4. Structured Findings
## 5. Recommended Import Set
## 6. Reading Path
## 7. Open Questions and Next Steps
```

Each research-entry skill may add specialized subsections under this shared structure.

### sources.jsonl

`sources.jsonl` stores evidence records behind the report and manifest. It should preserve enough information for an agent to audit how a paper was found.

Example record:

```json
{
  "source_id": "src_0001",
  "kind": "openalex_search",
  "query": "laser plasma strong-field QED review",
  "retrieved_at": "2026-06-05T00:00:00+08:00",
  "url": "https://api.openalex.org/works?...",
  "result_count": 25,
  "notes": "Used to identify review-centered entry points."
}
```

## Import Manifest Contract

`import-manifest.json` is the central executable interface between research judgment and deterministic ingest.

Example:

```json
{
  "schema_version": 1,
  "run_id": "2026-06-05-laser-plasma-qed",
  "library": "/path/to/paper-library",
  "default_collection": "plasma/qed/review",
  "default_actions": {
    "import": true,
    "convert": true,
    "extract_summary": true,
    "synthesize_relations": false
  },
  "papers": [
    {
      "manifest_id": "paper_001",
      "title": "Strong-field QED in laser-plasma experiments",
      "authors": ["Example Author"],
      "year": 2024,
      "doi": "10.0000/example",
      "arxiv_id": null,
      "source_urls": ["https://example.org/paper"],
      "pdf_url": "https://example.org/paper.pdf",
      "local_pdf": null,
      "target_collection": "plasma/qed/review",
      "priority": "must_read",
      "role": "key_review",
      "reason": "Defines the main taxonomy and connects the major experimental branches.",
      "status": "planned"
    }
  ]
}
```

### Required Paper Fields

Each `papers[]` item should include:

- `manifest_id`
- at least one of `title`, `doi`, `arxiv_id`, `pdf_url`, or `local_pdf`
- `target_collection` or a manifest-level `default_collection`
- `priority`
- `role`
- `reason`
- `status`

### Priority Values

First-version priority values:

- `must_read`
- `should_read`
- `background`
- `optional`
- `parked`

### Role Values

First-version role values:

- `key_review`
- `seminal`
- `method`
- `dataset`
- `experiment`
- `theory`
- `application`
- `critique`
- `replication`
- `recent_update`
- `author_representative`
- `seed`
- `context`

These should remain extensible. Unknown roles should not crash a run, but validators should warn.

### Status Values

Paper status values:

- `planned`
- `metadata_resolved`
- `pdf_ready`
- `pdf_unavailable`
- `download_failed`
- `imported`
- `duplicate`
- `conversion_failed`
- `summary_failed`
- `done`
- `needs_agent_review`
- `skipped`

The script should update statuses as it proceeds. It should not silently drop failed papers.

## Optional Paper Relations

`paper-relations.json` is optional in the first version.

It can represent relationships discovered during research or synthesis:

```json
{
  "schema_version": 1,
  "run_id": "2026-06-05-laser-plasma-qed",
  "nodes": [
    {
      "id": "paper_001",
      "kind": "paper",
      "title": "Strong-field QED in laser-plasma experiments",
      "paper_id": null,
      "manifest_id": "paper_001",
      "role": "key_review"
    }
  ],
  "edges": [
    {
      "source": "paper_001",
      "target": "paper_002",
      "type": "cites",
      "evidence": "Reference list in paper_001.",
      "confidence": "high"
    }
  ]
}
```

First-version edge types:

- `cites`
- `cited_by`
- `extends`
- `contrasts`
- `uses_method`
- `uses_dataset`
- `same_topic`
- `same_author_lineage`
- `review_covers`
- `replicates`
- `criticizes`

Confidence values:

- `high`
- `medium`
- `low`

Relations should preserve evidence text or source identifiers where possible.

## Reading Plan

`reading-plan.md` is optional but recommended for completed research reports.

It should organize papers into reading stages:

```text
## Stage 1: Orientation
## Stage 2: Foundations
## Stage 3: Main Branches
## Stage 4: Recent Updates
## Stage 5: Open Problems
```

Each entry should explain why the paper belongs in that stage and whether it has been imported and summarized.

## Scripted Execution

`run_ingest.py` should be the default deterministic executor.

Recommended flow:

```text
1. validate manifest
2. resolve metadata
3. fetch open-access PDF or use local PDF
4. call paper import for ready PDFs
5. call paper convert --pending
6. call paper extract summary for imported papers or target collection
7. call paper doctor --strict --json
8. update manifest statuses
9. append run-log.md
10. export run summary
```

The script should use `uv run paper ...` when run from the `paper-cli` repository and plain `paper ...` when configured for an installed command. This should be explicit in configuration or detected conservatively.

### Agent-Executable Fallback

Every scripted operation should be expressible as plain commands so Codex can take over:

```bash
uv run paper --library /path/to/library import /path/to/pdf-dir --collection plasma/qed/review --json
uv run paper --library /path/to/library convert --pending --json
uv run paper --library /path/to/library extract summary --collection plasma/qed/review --json
uv run paper --library /path/to/library doctor --strict --json
```

The skill should document this fallback path. It is important for cases where the script cannot handle a publisher page, missing PDF, metadata ambiguity, or collection decision.

## Metadata and PDF Resolution

The plugin may use external APIs and agent browsing during research, but deterministic scripts should keep their scope bounded.

First-version metadata helpers may use:

- DOI and Crossref.
- arXiv IDs and arXiv metadata.
- OpenAlex work records.
- Existing local PDF paths.
- Existing Zotero-exported metadata if provided as files.

First-version PDF helpers may use:

- Direct `pdf_url` from the manifest.
- Open-access URLs found in metadata.
- User-provided local PDFs.
- Previously downloaded run artifacts.

The script should not attempt complex browser automation, login, or paywall work. Those cases should become `needs_agent_review`.

## Failure Handling

The workflow must be resumable. A partial run should be useful rather than opaque.

Failure rules:

- Validation failure stops before network or filesystem writes.
- Missing metadata does not necessarily stop the whole run if a local PDF exists.
- Missing PDF should mark the paper as `pdf_unavailable` or `needs_agent_review`.
- Download failures should preserve URL, error text, and retry count.
- Import failures should preserve command, exit code, and stderr summary.
- Conversion failures should defer to existing `paper-cli` conversion diagnostics.
- Summary failures should not mark import or conversion as failed.
- `paper doctor --strict` issues should be copied into `run-log.md`.

The script should update `run-log.md` after each major stage.

## Interaction With paper-cli

The plugin should treat `paper-cli` as a stable external command and filesystem contract.

It should rely on:

- `paper init`
- `paper import`
- `paper convert --pending`
- `paper extract summary`
- `paper resolve`
- `paper get`
- `paper inspect`
- `paper status`
- `paper doctor --strict`

The plugin should not import Python internals from `paper_cli` in the first version. Keeping the boundary at CLI and file contracts preserves the option to rewrite or wrap `paper-cli` later.

## Documentation Expectations

The plugin documentation should make clear:

- Which skill to use for each research entry path.
- What files a research run creates.
- What the script will and will not automate.
- How to resume a failed run.
- How to manually edit `import-manifest.json`.
- How to ask Codex to continue from a run directory.

`paper-cli` documentation should mention the plugin only after an implementation exists or when the plugin is installed in a known location. Until then, this spec is the project record.

## First-Version Acceptance Criteria

A successful first version should demonstrate one topic research run that:

1. Creates a run directory.
2. Writes `research-run.json`.
3. Writes `research-report.md`.
4. Writes a schema-valid `import-manifest.json`.
5. Downloads or uses local PDFs for at least some selected papers.
6. Calls `paper-cli` to import those PDFs into the requested collection.
7. Runs conversion for imported pending papers.
8. Runs `paper extract summary` for imported converted papers.
9. Writes `run-log.md` with commands, outcomes, and failures.
10. Leaves failed or unavailable papers in explicit manifest statuses.
11. Allows the agent to manually fix the manifest and resume.
12. Optionally writes `paper-relations.json` and `reading-plan.md` when synthesis is enabled.

## Open Questions

- Should metadata-only records be importable into `paper-cli`, or should the plugin keep them only in the run directory until a PDF is available?
- Should relation outputs eventually become bundle-local artifacts, library-level indexes, or remain run-local?
- Should Zotero import be handled by this plugin first, by a future `paper-cli` source adapter first, or by both with different scopes?
- Should `run_ingest.py` live inside a Codex plugin bundle, inside this repository, or in a separate companion repository?
- How strict should schemas be about role names and relation types?
- Should the plugin eventually expose MCP tools, or remain skill-plus-script based until workflows stabilize?
