import io
import zipfile

from paper_cli.cli import main
from paper_cli.converters.local_zip import LocalFixtureConverter
from paper_cli.converters.mineru import MinerUConverter


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
