from paper_cli.models import PaperRecord, read_paper, write_paper
from paper_cli.cli import main


def test_paper_yaml_round_trip(tmp_path):
    record = PaperRecord.new(
        paper_id="sha256:abc",
        name="Example et al. - 2025 - Paper",
        collection="plasma/lwfa",
        imported_from="/tmp/source.pdf",
    )
    write_paper(tmp_path, record)
    loaded = read_paper(tmp_path)
    assert loaded.id == "sha256:abc"
    assert loaded.status["conversion"] == "pending"
    assert loaded.collection == "plasma/lwfa"


def test_import_pdf_copies_bundle(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "Vallieres et al. - 2025 - High average-flux laser-driven neutron source.pdf"
    source.write_bytes(b"%PDF-1.4\n%fake\n")
    assert main(["init", str(library)]) == 0
    assert main(["--library", str(library), "import", str(source), "--collection", "plasma/lwfa"]) == 0

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
