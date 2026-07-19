import yaml

from paper_cli.cli import main
from paper_cli.models import PaperRecord, read_paper, write_paper


def test_paper_yaml_round_trip(tmp_path):
    record = PaperRecord.new(
        paper_id="sha256:abc",
        name="Example et al. - 2025 - Paper",
        collection="plasma/lwfa",
        imported_from="/tmp/source.pdf",
        metadata={"title": "Paper", "creators": [{"name": "Example", "role": "author"}]},
        metadata_sources={"title": "filename", "creators": "filename"},
        metadata_confidence={"title": "medium", "creators": "medium"},
    )
    write_paper(tmp_path, record)
    loaded = read_paper(tmp_path)
    assert loaded.id == "sha256:abc"
    assert loaded.status["conversion"] == "pending"
    assert loaded.collection == "plasma/lwfa"
    assert loaded.metadata_sources["title"] == "filename"
    assert loaded.metadata_confidence["creators"] == "medium"


def test_import_pdf_copies_bundle(tmp_path):
    library = tmp_path / "library"
    source = (
        tmp_path / "Vallieres et al. - 2025 - High average-flux laser-driven neutron source.pdf"
    )
    source.write_bytes(b"%PDF-1.4\n%fake\n")
    assert main(["init", str(library)]) == 0
    assert (
        main(["--library", str(library), "import", str(source), "--collection", "plasma/lwfa"]) == 0
    )

    bundle = (
        library
        / "collections"
        / "plasma"
        / "lwfa"
        / "Vallieres et al. - 2025 - High average-flux laser-driven neutron source"
    )
    assert (bundle / "original.pdf").read_bytes() == source.read_bytes()
    assert (bundle / "paper.yaml").exists()
    assert (bundle / "notes" / "README.md").exists()
    record = read_paper(bundle)
    assert record.id.startswith("sha256:")
    assert record.status["conversion"] == "pending"
    assert record.metadata_sources == {
        "title": "filename",
        "creators": "filename",
        "year": "filename",
        "language": "detected",
    }
    assert record.metadata_confidence == {
        "title": "medium",
        "creators": "medium",
        "year": "medium",
        "language": "medium",
    }


def test_import_duplicate_pdf_skips_existing_bundle(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "A et al. - 2025 - Same.pdf"
    duplicate = tmp_path / "B et al. - 2025 - Different Name.pdf"
    payload = b"%PDF-1.4\nsame\n"
    source.write_bytes(payload)
    duplicate.write_bytes(payload)
    main(["init", str(library)])
    assert main(["--library", str(library), "import", str(source), "--inbox"]) == 0
    assert main(["--library", str(library), "import", str(duplicate), "--inbox"]) == 0
    bundles = [p for p in (library / "inbox").iterdir() if p.is_dir()]
    assert len(bundles) == 1


def test_import_pdf_honors_sync_safe_sanitize_config(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "García et al. - 2025 - γ source with ${}^{99}Mo.pdf"
    source.write_bytes(b"%PDF-1.4\n%fake\n")
    assert main(["init", str(library)]) == 0
    config_path = library / "paper-cli.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["naming"]["sanitize"] = {"max_length": 40, "ascii_slug": True}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    assert main(["--library", str(library), "import", str(source), "--inbox"]) == 0

    bundles = [p for p in (library / "inbox").iterdir() if p.is_dir()]
    assert len(bundles) == 1
    assert bundles[0].name == "garcia-et-al-2025-gamma-source-with-99-m"
    assert len(bundles[0].name) <= 40
