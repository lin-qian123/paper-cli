import json

import pytest
import yaml

from paper_cli.ai.providers import OpenAICompatibleProvider, ProviderConfig, load_provider_config
from paper_cli.cli import main
from paper_cli.models import PaperRecord, read_paper, write_paper


class FakeResponse:
    def __init__(self, payload, status_error=None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


def make_converted_bundle(library, *, title="Old Title", creators=None, confidence=None):
    main(["init", str(library)])
    bundle = library / "inbox" / "Old Title"
    bundle.mkdir(parents=True)
    record = PaperRecord.new(
        paper_id="sha256:abc",
        name="Old Title",
        collection=None,
        imported_from="/tmp/Old Title.pdf",
        metadata={
            "title": title,
            "creators": creators or [{"name": "Old", "role": "author"}],
            "year": 2024,
            "language": "en",
            "doi": None,
        },
        metadata_sources={
            "title": "filename",
            "creators": "filename",
            "year": "filename",
            "language": "detected",
        },
        metadata_confidence=confidence
        or {
            "title": "medium",
            "creators": "medium",
            "year": "medium",
            "language": "medium",
        },
    )
    record.status["conversion"] = "done"
    write_paper(bundle, record)
    (bundle / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (bundle / "paper.md").write_text(
        "# Correct Title\nAuthors: Correct Author\nDOI: 10.1234/example\n\n"
        "This is a normal paragraph.\n\n"
        "P a g e  1\n",
        encoding="utf-8",
    )
    (bundle / "conversion.json").write_text(
        json.dumps({"schema_version": 1, "state": "done", "ok": True}),
        encoding="utf-8",
    )
    return bundle


def chat_payload(content):
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


def test_provider_config_loads_env_and_library_settings(tmp_path, monkeypatch):
    library = tmp_path / "library"
    main(["init", str(library)])
    config_path = library / "paper-cli.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["ai"] = {
        "provider": "openai-compatible",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "CUSTOM_AI_KEY",
        "model": "local-model",
        "temperature": 0.2,
        "timeout_seconds": 5,
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("CUSTOM_AI_KEY", "secret")

    loaded = load_provider_config(library)

    assert loaded == ProviderConfig(
        base_url="http://localhost:11434/v1",
        api_key="secret",
        model="local-model",
        temperature=0.2,
        timeout_seconds=5,
    )


def test_openai_compatible_provider_sends_json_request(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(chat_payload({"ok": True}))

    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            base_url="http://example.test/v1",
            api_key="key",
            model="model-a",
            temperature=0,
            timeout_seconds=30,
        )
    )

    result = provider.complete_json([{"role": "user", "content": "Return JSON"}], schema_name="x")

    assert result == {"ok": True}
    assert calls[0][0] == "http://example.test/v1/chat/completions"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer key"
    assert calls[0][1]["json"]["model"] == "model-a"
    assert calls[0][1]["json"]["response_format"] == {"type": "json_object"}


def test_repair_fails_without_provider_config(tmp_path, monkeypatch):
    library = tmp_path / "library"
    make_converted_bundle(library)
    monkeypatch.delenv("PAPER_AI_API_KEY", raising=False)
    monkeypatch.delenv("PAPER_AI_MODEL", raising=False)

    assert main(["--library", str(library), "repair", "--json"]) == 1


def test_repair_metadata_dry_run_reports_change_without_writing(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)
    original_yaml = (bundle / "paper.yaml").read_text(encoding="utf-8")

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "proposed_metadata": {"title": "Correct Title"},
                    "field_changes": [
                        {
                            "field": "title",
                            "old": "Old Title",
                            "new": "Correct Title",
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "The first Markdown heading is Correct Title.",
                        }
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata", "--dry-run", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repaired"][0]["metadata_changed"] is True
    assert (bundle / "paper.yaml").read_text(encoding="utf-8") == original_yaml
    assert not (bundle / "repair.json").exists()
    assert not (bundle / "backups").exists()


def test_repair_accepts_paper_selector_and_limit(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    make_converted_bundle(library)
    second = library / "inbox" / "Second Paper"
    record = PaperRecord.new(
        paper_id="sha256:def",
        name="Second Paper",
        collection=None,
        imported_from="/tmp/Second Paper.pdf",
        metadata={
            "title": "Second Paper",
            "creators": [{"name": "Two", "role": "author"}],
            "year": 2023,
            "language": "en",
            "doi": None,
        },
    )
    record.status["conversion"] = "done"
    write_paper(second, record)
    (second / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (second / "paper.md").write_text("# Second Paper\n\nP a g e  1\n", encoding="utf-8")
    (second / "conversion.json").write_text(
        json.dumps({"schema_version": 1, "state": "done", "ok": True}),
        encoding="utf-8",
    )

    def fake_post(url, **kwargs):
        return FakeResponse(chat_payload({"block_patches": [], "warnings": []}))

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert (
        main(
            [
                "--library",
                str(library),
                "repair",
                "--target",
                "markdown",
                "--paper",
                "Second",
                "--limit",
                "1",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["paper"] == "Second"
    assert payload["limit"] == 1
    assert len(payload["repaired"]) == 1
    assert payload["repaired"][0]["path"] == str(second)


def test_repair_markdown_reports_warning_summary(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)
    (bundle / "paper.md").write_text(
        "# Correct Title\n\n"
        "T h i s shows $E = m c ^ 2$ and $F = m a$ with $\\alpha = \\beta$\n",
        encoding="utf-8",
    )

    def fake_post(url, **kwargs):
        return FakeResponse(chat_payload({"block_patches": [], "warnings": []}))

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "markdown", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    summary = payload["repaired"][0]["markdown_warning_summary"]
    repair_json = json.loads((bundle / "repair.json").read_text(encoding="utf-8"))

    assert any(row["reason"] == "review_only:math_heavy" for row in summary)
    assert any(row["reason"] == "review_only:all" for row in summary)
    assert repair_json["markdown"]["warning_summary"] == summary


def test_repair_metadata_applies_safe_change_with_backup_record_and_index(
    tmp_path, monkeypatch, capsys
):
    library = tmp_path / "library"
    make_converted_bundle(library)

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "proposed_metadata": {"title": "Correct Title", "doi": "10.1234/example"},
                    "field_changes": [
                        {
                            "field": "title",
                            "old": "Old Title",
                            "new": "Correct Title",
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "The first Markdown heading is Correct Title.",
                        },
                        {
                            "field": "doi",
                            "old": None,
                            "new": "10.1234/example",
                            "confidence": "medium",
                            "source": "ai-md-head",
                            "evidence": "The Markdown head contains DOI: 10.1234/example.",
                        },
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    repaired_path = payload["repaired"][0]["path"]
    repaired_bundle = library / "inbox" / "Old et al. - 2024 - Correct Title"
    record = read_paper(repaired_bundle)
    repair = json.loads((repaired_bundle / "repair.json").read_text(encoding="utf-8"))
    index = (library / "indexes" / "papers.jsonl").read_text(encoding="utf-8")

    assert repaired_path == str(repaired_bundle)
    assert record.metadata["title"] == "Correct Title"
    assert record.metadata["doi"] == "10.1234/example"
    assert record.metadata_sources["title"] == "ai-repair"
    assert record.metadata_confidence["doi"] == "medium"
    assert repair["metadata"]["changed"] is True
    assert len(list((repaired_bundle / "backups").glob("paper.yaml.*.bak"))) == 1
    assert "Correct Title" in index


def test_repair_metadata_normalizes_string_creator_list_and_renames(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    make_converted_bundle(library, creators=[])

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "proposed_metadata": {
                        "creators": ["W.L. Huang", "Q.F. Li", "Y.Z. Lin"],
                        "year": 2005,
                    },
                    "field_changes": [
                        {
                            "field": "creators",
                            "old": [],
                            "new": ["W.L. Huang", "Q.F. Li", "Y.Z. Lin"],
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "Markdown head lists authors as W.L. Huang, Q.F. Li, Y.Z. Lin.",
                        },
                        {
                            "field": "year",
                            "old": 2024,
                            "new": 2005,
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "Markdown head includes a 2005 publication date.",
                        },
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    repaired_bundle = library / "inbox" / "W.L. Huang et al. - 2005 - Old Title"
    record = read_paper(repaired_bundle)
    repair = json.loads((repaired_bundle / "repair.json").read_text(encoding="utf-8"))

    assert payload["repaired"][0]["path"] == str(repaired_bundle)
    assert record.metadata["creators"] == [
        {"name": "W.L. Huang", "role": "author"},
        {"name": "Q.F. Li", "role": "author"},
        {"name": "Y.Z. Lin", "role": "author"},
    ]
    assert record.metadata_sources["creators"] == "ai-repair"
    assert repair["metadata"]["warnings"] == []


def test_repair_metadata_normalizes_creator_string_and_renames(tmp_path, monkeypatch, capsys):
    library = tmp_path / "library"
    make_converted_bundle(library, creators=[])

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "proposed_metadata": {"creators": "W.L. Huang, Q.F. Li and Y.Z. Lin"},
                    "field_changes": [
                        {
                            "field": "creators",
                            "old": [],
                            "new": "W.L. Huang, Q.F. Li and Y.Z. Lin",
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "Markdown head lists authors as W.L. Huang, Q.F. Li and Y.Z. Lin.",
                        }
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    repaired_bundle = library / "inbox" / "W.L. Huang et al. - 2024 - Old Title"
    record = read_paper(repaired_bundle)

    assert payload["repaired"][0]["path"] == str(repaired_bundle)
    assert record.metadata["creators"][0]["name"] == "W.L. Huang"
    assert len(record.metadata["creators"]) == 3


def test_repair_metadata_preserves_user_high_confidence_field(tmp_path, monkeypatch):
    library = tmp_path / "library"
    bundle = make_converted_bundle(
        library,
        title="User Title",
        confidence={
            "title": "high",
            "creators": "medium",
            "year": "medium",
            "language": "medium",
        },
    )
    record = read_paper(bundle)
    record.metadata_sources["title"] = "user"
    write_paper(bundle, record)

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "proposed_metadata": {"title": "AI Title"},
                    "field_changes": [
                        {
                            "field": "title",
                            "old": "User Title",
                            "new": "AI Title",
                            "confidence": "high",
                            "source": "ai-md-head",
                            "evidence": "AI suggestion.",
                        }
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "metadata"]) == 0

    assert read_paper(bundle).metadata["title"] == "User Title"


def test_repair_markdown_applies_exact_match_patch(tmp_path, monkeypatch):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "block_patches": [
                        {
                            "block_id": "b00002",
                            "action": "replace",
                            "old_text": "P a g e  1",
                            "new_text": "",
                            "reason": "Removed OCR page footer noise.",
                            "confidence": "high",
                        }
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "markdown"]) == 0

    markdown = (bundle / "paper.md").read_text(encoding="utf-8")
    repair = json.loads((bundle / "repair.json").read_text(encoding="utf-8"))
    assert "P a g e  1" not in markdown
    assert repair["markdown"]["blocks_changed"] == 1
    assert len(list((bundle / "backups").glob("paper.md.*.bak"))) == 1


def test_repair_markdown_rejects_patch_mismatch(tmp_path, monkeypatch):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)
    original = (bundle / "paper.md").read_text(encoding="utf-8")

    def fake_post(url, **kwargs):
        return FakeResponse(
            chat_payload(
                {
                    "block_patches": [
                        {
                            "block_id": "b00002",
                            "action": "replace",
                            "old_text": "Different text",
                            "new_text": "",
                            "reason": "Mismatch.",
                            "confidence": "high",
                        }
                    ],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "markdown"]) == 0

    repair = json.loads((bundle / "repair.json").read_text(encoding="utf-8"))
    assert (bundle / "paper.md").read_text(encoding="utf-8") == original
    assert repair["markdown"]["blocks_changed"] == 0
    assert "Patch old_text mismatch" in repair["markdown"]["warnings"][0]


def test_repair_markdown_does_not_send_review_only_formula_to_provider(tmp_path, monkeypatch):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)
    (bundle / "paper.md").write_text(
        "$$\n"
        "s l o p e = { \\frac { A t t _ { n } } { A t t _ { X } } }\n"
        "$$\n",
        encoding="utf-8",
    )

    def fake_post(url, **kwargs):
        raise AssertionError("review-only formula block should not be sent to provider")

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--target", "markdown"]) == 0

    repair = json.loads((bundle / "repair.json").read_text(encoding="utf-8"))
    assert repair["markdown"]["changed"] is False
    assert repair["markdown"]["blocks_changed"] == 0
    assert any("review_only" in warning for warning in repair["markdown"]["warnings"])
    assert not (bundle / "backups").exists()


def test_repair_all_does_not_partially_write_metadata_when_markdown_provider_fails(
    tmp_path, monkeypatch
):
    library = tmp_path / "library"
    bundle = make_converted_bundle(library)

    calls = 0

    def fake_post(url, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeResponse(
                chat_payload(
                    {
                        "proposed_metadata": {"title": "Correct Title"},
                        "field_changes": [
                            {
                                "field": "title",
                                "old": "Old Title",
                                "new": "Correct Title",
                                "confidence": "high",
                                "source": "ai-md-head",
                                "evidence": "The first Markdown heading is Correct Title.",
                            }
                        ],
                        "warnings": [],
                    }
                )
            )
        raise RuntimeError("markdown provider failed")

    monkeypatch.setenv("PAPER_AI_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("PAPER_AI_API_KEY", "key")
    monkeypatch.setenv("PAPER_AI_MODEL", "model-a")
    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)

    assert main(["--library", str(library), "repair", "--json"]) == 1

    record = read_paper(bundle)
    assert record.metadata["title"] == "Old Title"
    assert record.metadata_sources["title"] == "filename"
    assert not (bundle / "repair.json").exists()
    assert not (bundle / "backups").exists()


def test_provider_rejects_invalid_json(monkeypatch):
    def fake_post(url, **kwargs):
        return FakeResponse({"choices": [{"message": {"content": "not-json"}}]})

    monkeypatch.setattr("paper_cli.ai.providers.requests.post", fake_post)
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            base_url="http://example.test/v1",
            api_key="key",
            model="model-a",
            temperature=0,
            timeout_seconds=30,
        )
    )

    with pytest.raises(ValueError, match="valid JSON"):
        provider.complete_json([{"role": "user", "content": "Return JSON"}], schema_name="x")
