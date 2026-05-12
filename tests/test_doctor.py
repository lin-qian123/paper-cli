import json

from paper_cli.cli import main
from paper_cli.doctor import run_doctor


def test_doctor_reports_missing_original_pdf(tmp_path):
    bundle = tmp_path / "library" / "inbox" / "Broken"
    bundle.mkdir(parents=True)
    (bundle / "paper.yaml").write_text(
        "schema_version: 1\nid: abc\nname: Broken\nstatus:\n  conversion: pending\n",
        encoding="utf-8",
    )
    issues = run_doctor(tmp_path / "library")
    assert any(issue.code == "missing-original-pdf" for issue in issues)


def test_status_json_reports_counts(tmp_path, capsys):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Status Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])
    assert main(["--library", str(library), "--json", "status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total"] == 1
    assert payload["pending"] == 1
