import json
import threading
import time

from paper_cli.ai.extract_summary import (
    DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
    DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
    DEFAULT_EXTRACT_SUMMARY_RETRY_WAIT_SECONDS,
    DEFAULT_EXTRACT_SUMMARY_WORKERS,
    build_source_map,
    effective_worker_count,
    extract_summary_library,
)
from paper_cli.ai.providers import OpenAICompatibleProvider, ProviderConfig, ProviderRequestTimeout
from paper_cli.cli import main
from paper_cli.models import PaperRecord, write_paper


class FakeSummaryProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self):
        self.calls = []

    def complete_json(self, messages, *, schema_name):
        self.calls.append((schema_name, messages))
        payload = json.loads(messages[-1]["content"])
        if schema_name == "extract-summary-blocks":
            return {
                "blocks": [
                    {
                        "block_id": block["block_id"],
                        "summary_text": f"Summary for {block['block_id']}",
                        "summary_level": "short",
                        "key_points": [f"Point for {block['block_id']}"],
                        "role": "background",
                        "importance": "medium",
                        "concepts": ["dual modality"],
                        "graph_candidates": [
                            {
                                "node_type": "concept",
                                "label": "dual modality",
                            }
                        ],
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
                        "key_points": [f"Section point for {section['section_id']}"],
                        "role": "background",
                    }
                    for section in payload["sections"]
                ],
                "warnings": [],
            }
        if schema_name == "extract-summary-graph":
            return {
                "nodes": [
                    {
                        "id": "node_0001",
                        "type": "concept",
                        "label": "dual modality",
                        "source_block_ids": [payload["blocks"][0]["block_id"]],
                    }
                ],
                "edges": [],
                "warnings": [],
            }
        raise AssertionError(schema_name)


class OmitsOnceProvider(FakeSummaryProvider):
    def __init__(self):
        super().__init__()
        self.omitted = False

    def complete_json(self, messages, *, schema_name):
        response = super().complete_json(messages, schema_name=schema_name)
        if schema_name == "extract-summary-blocks" and not self.omitted:
            self.omitted = True
            response["blocks"] = response["blocks"][:1]
        return response


class SlowTrackingProvider(FakeSummaryProvider):
    def __init__(self):
        super().__init__()
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def complete_json(self, messages, *, schema_name):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.02)
            return super().complete_json(messages, schema_name=schema_name)
        finally:
            with self.lock:
                self.active -= 1


class FailsOnceProvider(FakeSummaryProvider):
    def __init__(self):
        super().__init__()
        self.failed = False

    def complete_json(self, messages, *, schema_name):
        if schema_name == "extract-summary-blocks" and not self.failed:
            self.failed = True
            raise RuntimeError("temporary provider outage")
        return super().complete_json(messages, schema_name=schema_name)


class AlwaysFailsProvider(FakeSummaryProvider):
    def complete_json(self, messages, *, schema_name):
        raise RuntimeError(f"provider down for {schema_name}")


def make_summary_bundle(library, *, paper_id="sha256:abc", name="Example Paper", init=True):
    if init:
        main(["init", str(library)])
    bundle = library / "inbox" / name
    bundle.mkdir(parents=True)
    record = PaperRecord.new(
        paper_id=paper_id,
        name=name,
        collection=None,
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
        "This paper introduces dual-modality imaging for dense objects.\n\n"
        "## Method\n\n"
        "The method combines gamma radiography with neutron radiography.\n\n"
        "$$\nE = mc^2\n$$\n\n"
        "## Funding\n\n"
        "This work was supported by a grant.\n\n"
        "## References\n\n"
        "1. A. Author, Journal, 2026.\n",
        encoding="utf-8",
    )
    return bundle


def test_build_source_map_keeps_traceability_and_filters_non_main_blocks():
    markdown = (
        "# Title\n\n"
        "## Abstract\n\n"
        "Main abstract paragraph.\n\n"
        "$$\nE = mc^2\n$$\n\n"
        "## Funding\n\n"
        "This work was supported by a grant.\n\n"
        "## References\n\n"
        "1. Reference item.\n"
    )

    source_map = build_source_map(markdown)
    by_text = {block["text"]: block for block in source_map["blocks"]}

    abstract = by_text["Main abstract paragraph."]
    formula = by_text["$$\nE = mc^2\n$$"]
    funding = by_text["This work was supported by a grant."]
    reference = by_text["1. Reference item."]

    assert abstract["block_id"] == "blk_000002"
    assert abstract["summary_policy"] == "summarize"
    assert abstract["section_path"] == ["Abstract"]
    assert abstract["start_line"] == 5
    assert abstract["text_hash"].startswith("sha256:")
    assert formula["summary_policy"] == "context_only"
    assert funding["summary_policy"] == "skip"
    assert funding["skip_reason"] == "non_main_section"
    assert reference["summary_policy"] == "skip"
    assert reference["skip_reason"] == "reference_section"


def test_extract_summary_writes_traceable_outputs_without_modifying_source(tmp_path):
    library = tmp_path / "library"
    bundle = make_summary_bundle(library)
    original_markdown = (bundle / "paper.md").read_text(encoding="utf-8")
    provider = FakeSummaryProvider()

    payload = extract_summary_library(library, provider, workers=2)

    summary_dir = bundle / "extracts" / "summary"
    summary = json.loads((summary_dir / "summary.json").read_text(encoding="utf-8"))
    source_map = json.loads((summary_dir / "source-map.json").read_text(encoding="utf-8"))
    summary_md = (summary_dir / "summary.md").read_text(encoding="utf-8")

    assert payload["ok"] is True
    assert payload["extracted"][0]["blocks_summarized"] == 2
    assert (bundle / "paper.md").read_text(encoding="utf-8") == original_markdown
    assert summary["paper_id"] == "sha256:abc"
    assert summary["provider"] == "fake"
    assert summary["blocks"][0]["block_id"] == source_map["blocks"][2]["block_id"]
    assert summary["blocks"][0]["source_ref"]["text_hash"] == source_map["blocks"][2]["text_hash"]
    assert summary["sections"][0]["block_ids"]
    assert summary["graph"]["nodes"][0]["source_block_ids"] == [summary["blocks"][0]["block_id"]]
    assert "Source blocks:" in summary_md
    assert [call[0] for call in provider.calls] == [
        "extract-summary-blocks",
        "extract-summary-sections",
        "extract-summary-graph",
    ]


def test_extract_summary_enforces_paper_budget_for_openai_compatible_provider(tmp_path, monkeypatch):
    library = tmp_path / "library"
    make_summary_bundle(library)

    def slow_post(url, **kwargs):
        time.sleep(0.2)
        raise AssertionError("the response should be abandoned by the wall-clock timeout")

    monkeypatch.setattr("paper_cli.ai.providers.requests.post", slow_post)
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            base_url="http://example.test/v1",
            api_key="key",
            model="model-a",
            timeout_seconds=10,
        )
    )

    started = time.monotonic()
    payload = extract_summary_library(
        library,
        provider,
        force=True,
        retries=0,
        paper_timeout_seconds=0.02,
    )

    assert payload["ok"] is False
    assert "wall-clock limit" in payload["failed"][0]["error"]
    assert time.monotonic() - started < 0.12


def test_extract_summary_does_not_retry_a_hard_provider_timeout(tmp_path):
    class TimedOutProvider:
        name = "fake"
        model = "fake-model"

        def __init__(self):
            self.calls = 0

        def complete_json(self, messages, *, schema_name):
            self.calls += 1
            raise ProviderRequestTimeout("hard timeout")

    library = tmp_path / "library"
    make_summary_bundle(library)
    provider = TimedOutProvider()

    payload = extract_summary_library(library, provider, force=True, retries=2)

    assert payload["ok"] is False
    assert provider.calls == 1


def test_extract_summary_skips_existing_output_unless_force(tmp_path):
    library = tmp_path / "library"
    bundle = make_summary_bundle(library)
    output_dir = bundle / "extracts" / "summary"
    output_dir.mkdir(parents=True)
    (output_dir / "summary.json").write_text('{"old": true}\n', encoding="utf-8")
    provider = FakeSummaryProvider()

    skipped = extract_summary_library(library, provider)
    forced = extract_summary_library(library, provider, force=True)

    assert skipped["skipped"][0]["reason"] == "summary_exists"
    assert provider.calls
    assert forced["extracted"][0]["blocks_summarized"] == 2


def test_extract_summary_retries_missing_block_summaries(tmp_path):
    library = tmp_path / "library"
    bundle = make_summary_bundle(library)
    provider = OmitsOnceProvider()

    payload = extract_summary_library(library, provider, force=True)

    summary = json.loads(
        (bundle / "extracts" / "summary" / "summary.json").read_text(encoding="utf-8")
    )
    block_calls = [call for call in provider.calls if call[0] == "extract-summary-blocks"]

    assert payload["extracted"][0]["blocks_summarized"] == 2
    assert len(summary["blocks"]) == 2
    assert len(block_calls) == 2


def test_extract_summary_cli_dry_run_does_not_require_provider(tmp_path, capsys):
    library = tmp_path / "library"
    bundle = make_summary_bundle(library)

    assert main(["--library", str(library), "extract", "summary", "--dry-run", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["planned"][0]["path"] == str(bundle)
    assert payload["planned"][0]["summarizable_blocks"] == 2
    assert not (bundle / "extracts").exists()


def test_extract_summary_default_workers_and_effective_worker_count():
    assert DEFAULT_EXTRACT_SUMMARY_WORKERS == 16
    assert DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS == 16
    assert DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS == 500
    assert DEFAULT_EXTRACT_SUMMARY_RETRY_WAIT_SECONDS == 10.0
    assert effective_worker_count(workers=200, batch_count=7) == 7
    assert effective_worker_count(workers=16, batch_count=35) == 16
    assert effective_worker_count(workers=0, batch_count=35) == 1
    assert effective_worker_count(workers=16, batch_count=0) == 0


def test_extract_summary_processes_multiple_papers_concurrently(tmp_path):
    library = tmp_path / "library"
    make_summary_bundle(library, paper_id="sha256:one", name="Paper One")
    make_summary_bundle(library, paper_id="sha256:two", name="Paper Two", init=False)
    make_summary_bundle(library, paper_id="sha256:three", name="Paper Three", init=False)
    provider = SlowTrackingProvider()

    payload = extract_summary_library(
        library,
        provider,
        paper_workers=3,
        workers=1,
        max_requests=3,
        force=True,
    )

    assert payload["ok"] is True
    assert len(payload["extracted"]) == 3
    assert provider.max_active > 1


def test_extract_summary_global_request_limit_caps_parallel_provider_calls(tmp_path):
    library = tmp_path / "library"
    make_summary_bundle(library, paper_id="sha256:one", name="Paper One")
    make_summary_bundle(library, paper_id="sha256:two", name="Paper Two", init=False)
    make_summary_bundle(library, paper_id="sha256:three", name="Paper Three", init=False)
    provider = SlowTrackingProvider()

    payload = extract_summary_library(
        library,
        provider,
        paper_workers=16,
        workers=16,
        max_requests=2,
        force=True,
    )

    assert payload["ok"] is True
    assert provider.max_active <= 2


def test_extract_summary_retries_temporary_provider_failures(tmp_path):
    library = tmp_path / "library"
    make_summary_bundle(library)
    provider = FailsOnceProvider()

    payload = extract_summary_library(library, provider, force=True, retries=1, retry_wait=0)

    assert payload["ok"] is True
    assert payload["extracted"][0]["blocks_summarized"] == 2
    assert len([call for call in provider.calls if call[0] == "extract-summary-blocks"]) == 1


def test_extract_summary_reports_provider_failure_after_retries(tmp_path):
    library = tmp_path / "library"
    bundle = make_summary_bundle(library)
    provider = AlwaysFailsProvider()

    payload = extract_summary_library(library, provider, force=True, retries=1, retry_wait=0)

    assert payload["ok"] is False
    assert payload["failed"][0]["path"] == str(bundle)
    assert "extract-summary-blocks failed after 2 attempt(s)" in payload["failed"][0]["error"]
    assert "provider down for extract-summary-blocks" in payload["failed"][0]["error"]
    assert not (bundle / "extracts" / "summary" / "summary.json").exists()
