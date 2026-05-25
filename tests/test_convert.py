import io
import json
import zipfile

import pytest

from paper_cli.cli import main
from paper_cli.convert import convert_pending
from paper_cli.converters.base import BatchConversionResult
from paper_cli.converters.local_zip import LocalFixtureConverter
from paper_cli.converters.mineru import MinerUConverter
from paper_cli.models import read_paper, write_paper


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_local_fixture_converter_writes_markdown_and_images(tmp_path):
    source_pdf = tmp_path / "original.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n")
    out = tmp_path / "out"
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text("# Better Title\n", encoding="utf-8")
    (fixture / "images").mkdir()
    result = LocalFixtureConverter(fixture).convert(source_pdf, out)
    assert result.ok is True
    assert (out / "paper.md").exists()
    assert (out / "images").is_dir()


def test_convert_pending_writes_markdown_and_renames(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# Better Paper Title\nAuthors: Zhang\nYear: 2025\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])
    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )
    renamed = library / "inbox" / "Zhang et al. - 2025 - Better Paper Title"
    assert (renamed / "paper.md").exists()
    assert (renamed / "conversion.json").exists()


def test_convert_pending_strips_private_use_title_glyphs(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# Better Paper Title \ue907\nAuthors: Zhang\nYear: 2025\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    renamed = library / "inbox" / "Zhang et al. - 2025 - Better Paper Title"
    record = read_paper(renamed)
    assert record.metadata["title"] == "Better Paper Title"
    assert (renamed / "paper.md").exists()


def test_convert_pending_writes_diagnostic_conversion_json(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text("# Better Paper Title\n", encoding="utf-8")
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    bundle = library / "inbox" / "Better Paper Title"
    payload = json.loads((bundle / "conversion.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["converter"] == "local-fixture"
    assert payload["ok"] is True
    assert payload["state"] == "done"
    assert payload["attempt"] == 1
    assert payload["submitted_at"]
    assert payload["converted_at"]
    assert payload["error"] is None
    assert payload["raw_output_dir"] is None
    assert payload["markdown"] == "paper.md"
    assert payload["images"] == "images"


def test_convert_pending_appends_job_history(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text("# Better Paper Title\n", encoding="utf-8")
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    events = [
        json.loads(line)
        for line in (library / "indexes" / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == ["conversion-started", "conversion-finished"]
    assert events[0]["paper_id"].startswith("sha256:")
    assert events[0]["converter"] == "local-fixture"
    assert events[0]["attempt"] == 1
    assert events[0]["state"] == "running"
    assert events[1]["state"] == "done"
    assert events[1]["ok"] is True
    assert events[1]["bundle_path"] == "inbox/Better Paper Title"


def test_convert_pending_records_failure_and_retries_failed_bundle(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    failed_bundle = library / "inbox" / "Unknown"
    failed_payload = json.loads((failed_bundle / "conversion.json").read_text(encoding="utf-8"))
    assert failed_payload["ok"] is False
    assert failed_payload["state"] == "failed"
    assert failed_payload["attempt"] == 1
    assert "Missing fixture markdown" in failed_payload["error"]

    (fixture / "paper.md").write_text("# Recovered Title\n", encoding="utf-8")
    (fixture / "images").mkdir()
    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    recovered_bundle = library / "inbox" / "Recovered Title"
    recovered_payload = json.loads((recovered_bundle / "conversion.json").read_text(encoding="utf-8"))
    assert recovered_payload["ok"] is True
    assert recovered_payload["state"] == "done"
    assert recovered_payload["attempt"] == 2
    events = [
        json.loads(line)
        for line in (library / "indexes" / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["state"] for event in events] == ["running", "failed", "running", "done"]


def test_convert_pending_records_interrupted_job_before_reraising(tmp_path):
    class InterruptingConverter:
        name = "interrupting"

        def convert(self, source_pdf, output_dir):
            raise KeyboardInterrupt()

    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    try:
        convert_pending(library, InterruptingConverter())
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("Expected KeyboardInterrupt")

    bundle = library / "inbox" / "Unknown"
    record = read_paper(bundle)
    assert record.status["conversion"] == "failed"
    payload = json.loads((bundle / "conversion.json").read_text(encoding="utf-8"))
    assert payload["state"] == "interrupted"
    events = [
        json.loads(line)
        for line in (library / "indexes" / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["state"] for event in events] == ["running", "interrupted"]
    assert events[-1]["ok"] is False


def test_convert_pending_rejects_bad_ocr_title_for_rename(tmp_path):
    library = tmp_path / "library"
    pdf = (
        tmp_path
        / "Bargmann V. et al. - 1959 - Precession of the Polarization of Particles Moving in a Homogeneous Electromagnetic Field.pdf"
    )
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# PRECESSION OF THE POLARIZATION OF PARTICLES MOVING IN A HOMOGENEOUSELECTROMAGNETIC FIELD\\\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    original_name = (
        "Bargmann V. et al. - 1959 - Precession of the Polarization of Particles Moving in a "
        "Homogeneous Electromagnetic Field"
    )
    bundle = library / "inbox" / original_name
    record = read_paper(bundle)
    assert bundle.exists()
    assert record.status["naming"] == "review"
    assert record.metadata["title"] == (
        "Precession of the Polarization of Particles Moving in a Homogeneous Electromagnetic Field"
    )


def test_convert_pending_infers_creator_from_filename_title_prefix(tmp_path):
    library = tmp_path / "library"
    pdf = (
        tmp_path
        / "Advanced Science - 2026 - Guo - Helical Electron Beam Micro‐Bunching by High‐Order Modes.pdf"
    )
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# Helical Electron Beam Micro-Bunching by High-Order Modes\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    renamed = (
        library
        / "inbox"
        / "Guo et al. - 2026 - Helical Electron Beam Micro-Bunching by High-Order Modes"
    )
    assert (renamed / "paper.yaml").exists()


def test_convert_pending_splits_authors_line_into_creator_objects(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# Correct Title\nAuthors: W.L. Huang, Q.F. Li and Y.Z. Lin\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    renamed = library / "inbox" / "W.L. Huang et al. - Correct Title"
    record = read_paper(renamed)
    assert record.metadata["creators"] == [
        {"name": "W.L. Huang", "role": "author"},
        {"name": "Q.F. Li", "role": "author"},
        {"name": "Y.Z. Lin", "role": "author"},
    ]


def test_convert_pending_records_metadata_provenance(tmp_path):
    library = tmp_path / "library"
    pdf = (
        tmp_path
        / "Advanced Science - 2026 - Guo - Helical Electron Beam Micro‐Bunching by High‐Order Modes.pdf"
    )
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text(
        "# Helical Electron Beam Micro-Bunching by High-Order Modes\n",
        encoding="utf-8",
    )
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    bundle = (
        library
        / "inbox"
        / "Guo et al. - 2026 - Helical Electron Beam Micro-Bunching by High-Order Modes"
    )
    record = read_paper(bundle)
    assert record.metadata_sources["title"] == "mineru"
    assert record.metadata_confidence["title"] == "high"
    assert record.metadata_sources["creators"] == "filename-title-prefix"
    assert record.metadata_confidence["creators"] == "medium"
    assert record.metadata_sources["year"] == "filename"
    assert record.metadata_confidence["year"] == "medium"


def test_convert_pending_does_not_overwrite_high_confidence_creator(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Journal - 2026 - Guo - Better Title.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text("# Better Title\n", encoding="utf-8")
    (fixture / "images").mkdir()
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])
    bundle = library / "inbox" / "Journal et al. - 2026 - Guo - Better Title"
    record = read_paper(bundle)
    record.metadata["creators"] = [{"name": "Correct Author", "role": "author"}]
    record.metadata_sources["creators"] = "user"
    record.metadata_confidence["creators"] = "high"
    write_paper(bundle, record)

    assert (
        main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)])
        == 0
    )

    renamed = library / "inbox" / "Correct Author et al. - 2026 - Better Title"
    converted = read_paper(renamed)
    assert converted.metadata["creators"] == [{"name": "Correct Author", "role": "author"}]
    assert converted.metadata_sources["creators"] == "user"
    assert converted.metadata_confidence["creators"] == "high"


def test_convert_cli_accepts_explicit_local_fixture_converter(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "Unknown.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "paper.md").write_text("# Explicit Fixture\n", encoding="utf-8")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(
            [
                "--library",
                str(library),
                "convert",
                "--pending",
                "--converter",
                "local-fixture",
                "--fixture-output",
                str(fixture),
            ]
        )
        == 0
    )

    assert (library / "inbox" / "Explicit Fixture" / "paper.md").exists()


def test_convert_cli_rejects_unknown_converter():
    with pytest.raises(SystemExit):
        main(["convert", "--pending", "--converter", "unknown"])


def test_convert_cli_selects_existing_mineru_api_converter(tmp_path, monkeypatch):
    selected = {}

    class FakeMinerUConverter:
        name = "mineru"

        def __init__(self):
            selected["called"] = True

    monkeypatch.setattr("paper_cli.converters.mineru.MinerUConverter", FakeMinerUConverter)
    monkeypatch.setattr("paper_cli.cli.convert_pending", lambda library, converter, **kwargs: [])

    assert main(["--library", str(tmp_path / "library"), "convert", "--pending", "--converter", "mineru-api"]) == 0
    assert selected["called"] is True


def test_convert_pending_batch_converter_writes_success_and_failure(tmp_path):
    class FakeBatchConverter:
        name = "fake-batch"

        def convert_batch(self, items, output_dir, *, jobs=1):
            assert len(items) == 2
            results = []
            for item in items:
                if item.bundle_dir.name.startswith("A"):
                    markdown = item.output_dir / "paper.md"
                    item.output_dir.mkdir(parents=True, exist_ok=True)
                    markdown.write_text("# Batch Success\n", encoding="utf-8")
                    (item.output_dir / "images").mkdir()
                    results.append(
                        BatchConversionResult(
                            bundle_dir=item.bundle_dir,
                            ok=True,
                            markdown_path=markdown,
                            images_dir=item.output_dir / "images",
                        )
                    )
                else:
                    results.append(
                        BatchConversionResult(
                            bundle_dir=item.bundle_dir,
                            ok=False,
                            error="remote item failed",
                        )
                    )
            return results

    library = tmp_path / "library"
    main(["init", str(library)])
    for name in ["A.pdf", "B.pdf"]:
        pdf = tmp_path / name
        pdf.write_bytes(f"%PDF-1.4\n{name}\n".encode())
        main(["--library", str(library), "import", str(pdf), "--inbox"])

    converted = convert_pending(library, FakeBatchConverter(), batch_size=2)

    assert len(converted) == 1
    assert (library / "inbox" / "Batch Success" / "paper.md").exists()
    failed_record = read_paper(library / "inbox" / "B")
    assert failed_record.status["conversion"] == "failed"
    failed_payload = json.loads((library / "inbox" / "B" / "conversion.json").read_text())
    assert failed_payload["state"] == "failed"
    assert failed_payload["error"] == "remote item failed"


def test_convert_pending_batch_records_interrupted_jobs_before_reraising(tmp_path):
    class InterruptingBatchConverter:
        name = "interrupting-batch"

        def convert_batch(self, items, output_dir, *, jobs=1):
            raise KeyboardInterrupt()

    library = tmp_path / "library"
    main(["init", str(library)])
    for name in ["A.pdf", "B.pdf"]:
        pdf = tmp_path / name
        pdf.write_bytes(f"%PDF-1.4\n{name}\n".encode())
        main(["--library", str(library), "import", str(pdf), "--inbox"])

    with pytest.raises(KeyboardInterrupt):
        convert_pending(library, InterruptingBatchConverter(), batch_size=2)

    for bundle_name in ["A", "B"]:
        bundle = library / "inbox" / bundle_name
        record = read_paper(bundle)
        payload = json.loads((bundle / "conversion.json").read_text(encoding="utf-8"))
        assert record.status["conversion"] == "failed"
        assert payload["state"] == "interrupted"
        assert payload["converter"] == "interrupting-batch"

    events = [
        json.loads(line)
        for line in (library / "indexes" / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["state"] for event in events] == [
        "running",
        "running",
        "interrupted",
        "interrupted",
    ]


def test_convert_pending_batch_does_not_start_future_chunks_on_interruption(tmp_path):
    class InterruptingBatchConverter:
        name = "interrupting-batch"

        def convert_batch(self, items, output_dir, *, jobs=1):
            raise KeyboardInterrupt()

    library = tmp_path / "library"
    main(["init", str(library)])
    for name in ["A.pdf", "B.pdf", "C.pdf"]:
        pdf = tmp_path / name
        pdf.write_bytes(f"%PDF-1.4\n{name}\n".encode())
        main(["--library", str(library), "import", str(pdf), "--inbox"])

    with pytest.raises(KeyboardInterrupt):
        convert_pending(library, InterruptingBatchConverter(), batch_size=2)

    assert not (library / "inbox" / "C" / "conversion.json").exists()
    events = [
        json.loads(line)
        for line in (library / "indexes" / "jobs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(events) == 4
    assert {event["bundle_path"] for event in events} == {"inbox/A", "inbox/B"}


def test_mineru_converter_fails_without_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("MINERU_API_KEY", raising=False)
    result = MinerUConverter().convert(tmp_path / "missing.pdf", tmp_path / "out")
    assert result.ok is False
    assert "MINERU_API_KEY" in (result.error or "")


def test_mineru_converter_normalizes_mocked_zip(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr("result/full.md", "# Converted\n")
        archive.writestr("result/images/fig.png", b"png")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example"],
                },
            }
        )

    def fake_put(*args, **kwargs):
        return FakeResponse({})

    def fake_get(url, *args, **kwargs):
        if "extract-results" in url:
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {"state": "done", "full_zip_url": "https://download.example/result.zip"}
                        ]
                    },
                }
            )
        return FakeResponse(content=zip_buffer.getvalue())

    monkeypatch.setattr("paper_cli.converters.mineru.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.get", fake_get)
    result = MinerUConverter(api_key="test-key", poll_interval=0).convert(pdf, tmp_path / "out")
    assert result.ok is True
    assert (tmp_path / "out" / "paper.md").read_text(encoding="utf-8") == "# Converted\n"
    assert (tmp_path / "out" / "images").is_dir()


def test_mineru_converter_retries_transient_upload_failure(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr("result/full.md", "# Converted\n")
    put_calls = {"count": 0}

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {"code": 0, "data": {"batch_id": "batch-1", "file_urls": ["https://upload.example"]}}
        )

    def fake_put(*args, **kwargs):
        put_calls["count"] += 1
        if put_calls["count"] == 1:
            raise TimeoutError("temporary upload timeout")
        return FakeResponse({})

    def fake_get(url, *args, **kwargs):
        if "extract-results" in url:
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {"state": "done", "full_zip_url": "https://download.example/result.zip"}
                        ]
                    },
                }
            )
        return FakeResponse(content=zip_buffer.getvalue())

    monkeypatch.setattr("paper_cli.converters.mineru.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.get", fake_get)

    result = MinerUConverter(api_key="test-key", poll_interval=0, retry_wait=0).convert(
        pdf, tmp_path / "out"
    )

    assert result.ok is True
    assert put_calls["count"] == 2


def test_mineru_converter_times_out_long_running_task(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {"code": 0, "data": {"batch_id": "batch-1", "file_urls": ["https://upload.example"]}}
        )

    def fake_put(*args, **kwargs):
        return FakeResponse({})

    def fake_get(*args, **kwargs):
        return FakeResponse({"code": 0, "data": {"extract_result": [{"state": "running"}]}})

    monkeypatch.setattr("paper_cli.converters.mineru.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.get", fake_get)

    result = MinerUConverter(
        api_key="test-key",
        poll_interval=0,
        max_wait_seconds=0,
        retry_wait=0,
    ).convert(pdf, tmp_path / "out")

    assert result.ok is False
    assert "timed out" in (result.error or "")


def test_mineru_converter_moves_sidecars_to_raw_dir(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr("result/full.md", "# Converted\n")
        archive.writestr("result/layout.json", "{}")
        archive.writestr("result/abc_content_list.json", "{}")
        archive.writestr("result/abc_origin.pdf", b"%PDF-1.4\n")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example"],
                },
            }
        )

    def fake_put(*args, **kwargs):
        return FakeResponse({})

    def fake_get(url, *args, **kwargs):
        if "extract-results" in url:
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {"state": "done", "full_zip_url": "https://download.example/result.zip"}
                        ]
                    },
                }
            )
        return FakeResponse(content=zip_buffer.getvalue())

    monkeypatch.setattr("paper_cli.converters.mineru.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru.requests.get", fake_get)

    result = MinerUConverter(api_key="test-key", poll_interval=0).convert(pdf, tmp_path / "out")

    assert result.ok is True
    assert (tmp_path / "out" / "raw" / "mineru" / "layout.json").exists()
    assert (tmp_path / "out" / "raw" / "mineru" / "abc_content_list.json").exists()
    assert (tmp_path / "out" / "raw" / "mineru" / "abc_origin.pdf").exists()
    assert not (tmp_path / "out" / "layout.json").exists()
