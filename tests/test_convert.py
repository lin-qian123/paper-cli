from paper_cli.converters.local_zip import LocalFixtureConverter
from paper_cli.cli import main


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
    assert main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)]) == 0
    renamed = library / "inbox" / "Zhang et al. - 2025 - Better Paper Title"
    assert (renamed / "paper.md").exists()
    assert (renamed / "conversion.json").exists()
