import json

from paper_cli.ai.extract_summary import extract_summary_library
from paper_cli.ai.memory_build import build_memory_library
from paper_cli.cli import main
from paper_cli.models import PaperRecord, write_paper


class FakeSummaryProvider:
    name = "fake"
    model = "fake-summary-model"

    def complete_json(self, messages, *, schema_name):
        payload = json.loads(messages[-1]["content"])
        if schema_name == "extract-summary-blocks":
            return {
                "blocks": [
                    {
                        "block_id": block["block_id"],
                        "summary_text": f"Summary for {block['block_id']}",
                        "summary_level": "medium",
                        "key_points": [f"Key point for {block['block_id']}"],
                        "role": "method" if "Method" in "/".join(block["section_path"]) else "background",
                        "importance": "high",
                        "concepts": ["dual modality"],
                        "graph_candidates": [],
                    }
                    for block in payload["blocks"]
                ],
                "warnings": [],
            }
        if schema_name == "extract-summary-sections":
            return {
                "sections": [
                    {
                        "section_id": section["section_id"],
                        "summary": f"Section summary for {section['heading']}",
                        "key_points": [f"Point for {section['section_id']}"],
                        "role": "method" if "Method" in section["heading"] else "background",
                    }
                    for section in payload["sections"]
                ],
                "warnings": [],
            }
        if schema_name == "extract-summary-graph":
            first_block_id = payload["blocks"][0]["block_id"] if payload["blocks"] else "blk_000000"
            return {
                "nodes": [
                    {
                        "id": "node_0001",
                        "type": "concept",
                        "label": "dual modality",
                        "source_block_ids": [first_block_id],
                    },
                    {
                        "id": "node_0002",
                        "type": "method",
                        "label": "fusion imaging",
                        "source_block_ids": [first_block_id],
                    },
                ],
                "edges": [],
                "warnings": [],
            }
        raise AssertionError(schema_name)


class FakeMemoryProvider:
    name = "fake"
    model = "fake-memory-model"

    def __init__(self):
        self.calls = []

    def complete_json(self, messages, *, schema_name):
        self.calls.append(schema_name)
        payload = json.loads(messages[-1]["content"])
        if schema_name == "memory-build-collection":
            first_paper = payload["papers"][0]
            first_block_id = first_paper["memory"]["important_block_ids"][0]
            return {
                "overview_summary": f"Collection overview for {payload['collection_path']}",
                "collection_themes": [
                    {
                        "name": "dual modality",
                        "summary": "Shared dual-modality imaging theme",
                        "paper_ids": [paper["paper_id"] for paper in payload["papers"]],
                        "source_block_ids": [first_block_id],
                    }
                ],
                "relations": [],
                "representative_paper_ids": [first_paper["paper_id"]],
                "warnings": [],
            }
        if schema_name == "memory-build-library":
            first_collection = payload["collections"][0]
            first_paper_id = first_collection["representative_paper_ids"][0]
            return {
                "overview_summary": "Library overview",
                "collections": [
                    {
                        "collection_path": collection["collection_path"],
                        "summary": f"Summary for {collection['collection_path']}",
                        "main_themes": ["dual modality"],
                        "representative_paper_ids": collection["representative_paper_ids"],
                    }
                    for collection in payload["collections"]
                ],
                "global_themes": [
                    {
                        "name": "dual modality",
                        "summary": "Cross-collection dual-modality theme",
                        "collection_paths": [collection["collection_path"] for collection in payload["collections"]],
                        "paper_ids": [first_paper_id],
                    }
                ],
                "cross_collection_relations": [],
                "warnings": [],
            }
        raise AssertionError(schema_name)


class AlwaysFailsMemoryProvider(FakeMemoryProvider):
    def complete_json(self, messages, *, schema_name):
        raise RuntimeError(f"provider down for {schema_name}")


def fake_complete_json(self, messages, *, schema_name):
    if schema_name.startswith("extract-summary"):
        return FakeSummaryProvider().complete_json(messages, schema_name=schema_name)
    if schema_name.startswith("memory-build"):
        return FakeMemoryProvider().complete_json(messages, schema_name=schema_name)
    raise AssertionError(schema_name)


def make_bundle(library, *, name, paper_id, collection=None, with_summary=True, init=False):
    if init:
        main(["init", str(library)])
    bundle_root = library / "inbox"
    if collection:
        bundle_root = library / "collections" / collection
    bundle = bundle_root / name
    bundle.mkdir(parents=True, exist_ok=True)
    record = PaperRecord.new(
        paper_id=paper_id,
        name=name,
        collection=collection,
        imported_from="/tmp/example.pdf",
        metadata={
            "title": name,
            "creators": [{"name": "Author", "role": "author"}],
            "year": 2026,
            "language": "en",
            "doi": None,
        },
    )
    record.status["conversion"] = "done"
    write_paper(bundle, record)
    (bundle / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (bundle / "conversion.json").write_text(
        json.dumps({"schema_version": 1, "state": "done", "ok": True}),
        encoding="utf-8",
    )
    (bundle / "paper.md").write_text(
        "# Example Paper\n\n"
        "## Abstract\n\n"
        "This paper introduces dual-modality imaging.\n\n"
        "## Method\n\n"
        "The method combines gamma radiography with neutron radiography.\n",
        encoding="utf-8",
    )
    if with_summary:
        extract_summary_library(library, FakeSummaryProvider(), force=True)
    return bundle


def test_memory_build_dry_run_without_provider(tmp_path, capsys):
    library = tmp_path / "library"
    make_bundle(library, name="Paper A", paper_id="sha256:a", collection="dual", with_summary=True, init=True)
    make_bundle(library, name="Paper B", paper_id="sha256:b", collection="dual", with_summary=False)

    assert main(["--library", str(library), "memory", "build", "--dry-run", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert any(row["kind"] == "collection-memory" for row in payload["planned"])
    assert any(row["kind"] == "library-memory" for row in payload["planned"])
    assert any(row["reason"] == "missing-summary" for row in payload["skipped"])


def test_memory_build_writes_collection_and_library_outputs(tmp_path):
    library = tmp_path / "library"
    bundle = make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=True,
        init=True,
    )
    provider = FakeMemoryProvider()

    payload = build_memory_library(library, provider)

    collection_json = library / "collections" / "dual" / "_memory" / "collection-memory.json"
    collection_md = library / "collections" / "dual" / "_memory" / "collection-memory.md"
    paper_index = library / "collections" / "dual" / "_memory" / "paper-index.json"
    library_json = library / "_memory" / "library-memory.json"
    library_md = library / "_memory" / "library-memory.md"
    collection_index = library / "_memory" / "collection-index.json"

    assert payload["ok"] is True
    assert collection_json.exists()
    assert collection_md.exists()
    assert paper_index.exists()
    assert library_json.exists()
    assert library_md.exists()
    assert collection_index.exists()

    collection_payload = json.loads(collection_json.read_text(encoding="utf-8"))
    library_payload = json.loads(library_json.read_text(encoding="utf-8"))

    assert collection_payload["papers"][0]["paper_id"] == "sha256:a"
    assert collection_payload["papers"][0]["bundle_path"] == str(bundle.relative_to(library))
    assert collection_payload["themes"][0]["paper_ids"] == ["sha256:a"]
    assert library_payload["collections"][0]["collection_path"] == "dual"
    assert "memory-build-collection" in provider.calls
    assert "memory-build-library" in provider.calls


def test_memory_build_skips_existing_output_unless_force_and_reports_stale(tmp_path):
    library = tmp_path / "library"
    bundle = make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=True,
        init=True,
    )
    provider = FakeMemoryProvider()

    first = build_memory_library(library, provider)
    summary_path = bundle / "extracts" / "summary" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["warnings"].append("changed")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    second = build_memory_library(library, provider)
    third = build_memory_library(library, provider, force=True)

    assert first["ok"] is True
    collection_skip = next(row for row in second["skipped"] if row["kind"] == "collection-memory")
    library_skip = next(row for row in second["skipped"] if row["kind"] == "library-memory")
    assert collection_skip["stale"] is True
    assert library_skip["stale"] is True
    assert third["ok"] is True
    assert any(row["kind"] == "collection-memory" for row in third["written"])


def test_memory_build_reports_provider_failure_without_partial_output(tmp_path):
    library = tmp_path / "library"
    make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=True,
        init=True,
    )

    payload = build_memory_library(library, AlwaysFailsMemoryProvider())

    assert payload["ok"] is False
    assert payload["failed"][0]["kind"] == "collection-memory"
    assert not (library / "collections" / "dual" / "_memory" / "collection-memory.json").exists()
    assert not (library / "_memory" / "library-memory.json").exists()


def test_memory_build_fails_without_provider_config(tmp_path, capsys, monkeypatch):
    library = tmp_path / "library"
    make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=True,
        init=True,
    )
    monkeypatch.delenv("PAPER_AI_API_KEY", raising=False)
    monkeypatch.delenv("PAPER_AI_MODEL", raising=False)
    monkeypatch.delenv("PAPER_AI_BASE_URL", raising=False)

    assert main(["--library", str(library), "memory", "build", "--json"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "Missing AI provider configuration" in payload["error"]


def test_import_marks_memory_state_stale(tmp_path):
    library = tmp_path / "library"
    main(["init", str(library)])
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    assert main(["--library", str(library), "import", str(pdf), "--collection", "dual", "--json"]) == 0

    state = json.loads((library / "indexes" / "memory-state.json").read_text(encoding="utf-8"))
    assert state["library"]["stale"] is True
    assert state["library"]["reason"] == "import"
    assert state["collections"]["dual"]["stale"] is True
    paper_entry = next(iter(state["papers"].values()))
    assert paper_entry["stale"] is True
    assert paper_entry["reason"] == "import"


def test_extract_summary_auto_refreshes_memory_and_clears_state(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=False,
        init=True,
    )
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model")
    monkeypatch.setattr("paper_cli.ai.providers.OpenAICompatibleProvider.complete_json", fake_complete_json)

    assert main(["--library", str(library), "extract", "summary", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["memory_refresh"]["ok"] is True
    assert (library / "collections" / "dual" / "_memory" / "collection-memory.json").exists()
    assert (library / "_memory" / "library-memory.json").exists()
    state = json.loads((library / "indexes" / "memory-state.json").read_text(encoding="utf-8"))
    assert state["library"]["stale"] is False
    assert state["collections"]["dual"]["stale"] is False
    assert state["papers"]["sha256:a"]["stale"] is False


def test_repair_marks_memory_state_stale_after_existing_memory(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    make_bundle(
        library,
        name="Paper A",
        paper_id="sha256:a",
        collection="dual",
        with_summary=True,
        init=True,
    )
    build_memory_library(library, FakeMemoryProvider())

    def fake_post(url, **kwargs):
        return type(
            "Resp",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "proposed_metadata": {"title": "Paper A Revised"},
                                        "field_changes": [
                                            {
                                                "field": "title",
                                                "old": "Paper A",
                                                "new": "Paper A Revised",
                                                "confidence": "high",
                                                "source": "ai-md-head",
                                                "evidence": "Markdown heading",
                                            }
                                        ],
                                        "warnings": [],
                                    }
                                )
                            }
                        }
                    ]
                },
            },
        )()

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata", "--json"]) == 0
    _ = capsys.readouterr().out
    state = json.loads((library / "indexes" / "memory-state.json").read_text(encoding="utf-8"))
    assert state["library"]["stale"] is True
    assert state["collections"]["dual"]["stale"] is True
    paper_entry = next(iter(state["papers"].values()))
    assert paper_entry["stale"] is True
    assert paper_entry["reason"] == "repair"
