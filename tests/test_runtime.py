import json

from paper_cli.cli import main
from paper_cli.runtime import RuntimeReporter


def test_runtime_reporter_records_jsonl_events_and_stderr_progress(tmp_path, capsys):
    library = tmp_path / "library"
    main(["init", str(library)])
    reporter = RuntimeReporter(library, "extract-summary")

    reporter.started({"stage": "summary", "count": 2})
    reporter.emit("paper-started", {"path": "inbox/example", "stage": "summary"})
    reporter.finished(ok=True, details={"stage": "summary", "count": 1})

    events = [
        json.loads(line)
        for line in (library / "indexes" / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    captured = capsys.readouterr()

    assert [event["event"] for event in events] == ["run-started", "paper-started", "run-finished"]
    assert {event["run_id"] for event in events} == {reporter.run_id}
    assert all(event["command"] == "extract-summary" for event in events)
    assert "paper[extract-summary] paper-started" in captured.err
