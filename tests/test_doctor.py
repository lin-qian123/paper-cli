import json

from paper_cli.cli import main
from paper_cli.doctor import run_doctor
from paper_cli.indexes import append_job


def test_doctor_reports_missing_original_pdf(tmp_path):
    bundle = tmp_path / "library" / "inbox" / "Broken"
    bundle.mkdir(parents=True)
    (bundle / "paper.yaml").write_text(
        "schema_version: 1\nid: abc\nname: Broken\nstatus:\n  conversion: pending\n",
        encoding="utf-8",
    )
    issues = run_doctor(tmp_path / "library")
    assert any(issue.code == "missing-original-pdf" for issue in issues)


def test_doctor_reports_invalid_creator_shape(tmp_path):
    bundle = tmp_path / "library" / "inbox" / "Malformed"
    bundle.mkdir(parents=True)
    (bundle / "original.pdf").write_bytes(b"%PDF-1.4\n")
    (bundle / "paper.yaml").write_text(
        "schema_version: 1\n"
        "id: abc\n"
        "name: Malformed\n"
        "metadata:\n"
        "  title: Malformed\n"
        "  creators:\n"
        "    - W.L. Huang\n"
        "status:\n"
        "  conversion: pending\n",
        encoding="utf-8",
    )

    issues = run_doctor(tmp_path / "library")

    assert any(issue.code == "invalid-creators" for issue in issues)


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


def test_json_flag_is_accepted_after_subcommand(tmp_path, capsys):
    library = tmp_path / "library"
    assert main(["init", str(library), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_doctor_strict_reports_failed_pending_and_dangling_jobs(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Pending Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])
    append_job(
        library,
        {
            "event": "conversion-started",
            "paper_id": "sha256:test",
            "attempt": 1,
            "state": "running",
            "bundle_path": "inbox/Pending Paper",
        },
    )

    normal_issues = run_doctor(library)
    strict_issues = run_doctor(library, strict=True)

    assert not any(issue.code == "pending-conversion" for issue in normal_issues)
    assert any(issue.code == "pending-conversion" for issue in strict_issues)
    assert any(issue.code == "dangling-conversion-job" for issue in strict_issues)


def test_doctor_cli_strict_exits_nonzero_for_incomplete_batch(tmp_path, capsys):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Pending Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])
    main(["--library", str(library), "import", str(pdf), "--inbox"])

    assert main(["--library", str(library), "doctor", "--strict", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert any(issue["code"] == "pending-conversion" for issue in payload["issues"])
