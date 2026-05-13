import json

from paper_cli.cli import main


def test_import_updates_papers_index(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Indexed Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])
    lines = (library / "indexes" / "papers.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["name"] == "A et al. - 2025 - Indexed Paper"
    assert row["status"]["conversion"] == "pending"
    assert row["collection"] is None
    assert row["metadata_sources"]["title"] == "filename"
    assert row["metadata_confidence"]["title"] == "medium"
