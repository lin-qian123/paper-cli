import json

from paper_cli.cli import main
from paper_cli.models import PaperRecord, write_paper


def test_resolve_get_and_inspect_paper_by_id_prefix(tmp_path, capsys):
    library = tmp_path / "library"
    main(["init", str(library)])
    bundle = library / "inbox" / "Example et al. - 2026 - Traceable Paper"
    record = PaperRecord.new(
        paper_id="sha256:abcdef123456",
        name="Example et al. - 2026 - Traceable Paper",
        collection=None,
        imported_from="/tmp/source.pdf",
        metadata={"title": "Traceable Paper", "creators": [{"name": "Example"}], "year": 2026},
    )
    record.status["conversion"] = "done"
    write_paper(bundle, record)
    (bundle / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (bundle / "paper.md").write_text("# Traceable Paper\n", encoding="utf-8")
    (bundle / "conversion.json").write_text('{"state":"done"}', encoding="utf-8")

    assert main(["--library", str(library), "resolve", "sha256:abc", "--json"]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["ok"] is True
    assert resolved["paper"]["id"] == "sha256:abcdef123456"
    assert "id-prefix" in resolved["reasons"]

    assert main(["--library", str(library), "get", "Traceable", "--json"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["paper"]["metadata"]["title"] == "Traceable Paper"

    assert main(["--library", str(library), "inspect", str(bundle), "--json"]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["artifacts"]["paper_md"]["exists"] is True
    assert inspected["conversion"]["state"] == "done"


def test_resolve_reports_ambiguous_matches(tmp_path, capsys):
    library = tmp_path / "library"
    main(["init", str(library)])
    for paper_id, name in [
        ("sha256:one", "Example One"),
        ("sha256:two", "Example Two"),
    ]:
        bundle = library / "inbox" / name
        write_paper(
            bundle,
            PaperRecord.new(
                paper_id=paper_id,
                name=name,
                collection=None,
                imported_from="/tmp/source.pdf",
                metadata={"title": name, "creators": []},
            ),
        )
        (bundle / "original.pdf").write_bytes(b"%PDF-1.4\n")

    assert main(["--library", str(library), "resolve", "Example", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "ambiguous"
    assert len(payload["matches"]) == 2


def test_convert_dry_run_reports_pending_without_writing(tmp_path, capsys):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Pending Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
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
                "mineru-local",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["converter"] == "mineru-local"
    assert payload["pending_count"] == 1
    assert not (library / "inbox" / "A et al. - 2025 - Pending Paper" / "conversion.json").exists()


def test_convert_defaults_to_batch_api_with_long_pdf_splitting(tmp_path, capsys):
    library = tmp_path / "library"
    pdf = tmp_path / "Pending Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert (
        main(
            [
                "--library",
                str(library),
                "convert",
                "--pending",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["converter"] == "mineru-api-batch"
