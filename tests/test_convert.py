from paper_cli.converters.local_zip import LocalFixtureConverter


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
