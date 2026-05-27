import subprocess

from paper_cli.converters.base import BatchConversionItem, ConversionResult
from paper_cli.converters.mineru_local import MinerULocalConverter


def test_mineru_local_runs_cli_and_normalizes_output(tmp_path, monkeypatch):
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    output = tmp_path / "bundle"
    commands = []

    def fake_run(command, capture_output, text, timeout, check):
        commands.append(command)
        out_dir = command[command.index("-o") + 1]
        result = tmp_path / "mineru-out" / "nested"
        result.mkdir(parents=True)
        (result / "full.md").write_text("# Local Converted\n", encoding="utf-8")
        (result / "images").mkdir()
        (result / "images" / "fig.png").write_bytes(b"png")
        assert str(tmp_path / "mineru-out") == out_dir
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("paper_cli.converters.mineru_local.subprocess.run", fake_run)
    monkeypatch.setattr("paper_cli.converters.mineru_local.tempfile.mkdtemp", lambda: str(tmp_path / "mineru-out"))

    result = MinerULocalConverter().convert(pdf, output)

    assert result.ok is True
    assert commands[0][:5] == ["mineru", "-p", str(pdf), "-o", str(tmp_path / "mineru-out")]
    assert (output / "paper.md").read_text(encoding="utf-8") == "# Local Converted\n"
    assert (output / "images" / "fig.png").exists()


def test_mineru_local_backend_adds_pipeline_flag(tmp_path, monkeypatch):
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    commands = []

    def fake_run(command, capture_output, text, timeout, check):
        commands.append(command)
        out_dir = command[command.index("-o") + 1]
        result = tmp_path / "mineru-out"
        result.mkdir()
        (result / "paper.md").write_text("# Pipeline\n", encoding="utf-8")
        assert out_dir == str(result)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("paper_cli.converters.mineru_local.subprocess.run", fake_run)
    monkeypatch.setattr("paper_cli.converters.mineru_local.tempfile.mkdtemp", lambda: str(tmp_path / "mineru-out"))

    result = MinerULocalConverter(local_backend="pipeline").convert(pdf, tmp_path / "bundle")

    assert result.ok is True
    assert commands[0][-2:] == ["-b", "pipeline"]


def test_mineru_local_uses_configured_backend_and_executable(tmp_path, monkeypatch):
    executable = tmp_path / "mineru"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    commands = []

    def fake_run(command, capture_output, text, timeout, check):
        commands.append(command)
        out_dir = command[command.index("-o") + 1]
        result = tmp_path / "mineru-out"
        result.mkdir()
        (result / "paper.md").write_text("# Configured\n", encoding="utf-8")
        assert out_dir == str(result)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("paper_cli.converters.mineru_local.subprocess.run", fake_run)
    monkeypatch.setattr("paper_cli.converters.mineru_local.tempfile.mkdtemp", lambda: str(tmp_path / "mineru-out"))

    result = MinerULocalConverter(
        executable=None,
        config={"mineru": {"executable": str(executable), "local_backend": "pipeline"}},
    ).convert(pdf, tmp_path / "bundle")

    assert result.ok is True
    assert commands[0][0] == str(executable)
    assert commands[0][-2:] == ["-b", "pipeline"]


def test_mineru_local_missing_cli_returns_clear_failure(tmp_path, monkeypatch):
    pdf = tmp_path / "original.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("mineru")

    monkeypatch.setattr("paper_cli.converters.mineru_local.subprocess.run", fake_run)

    result = MinerULocalConverter().convert(pdf, tmp_path / "bundle")

    assert result.ok is False
    assert "mineru CLI was not found" in (result.error or "")


def test_mineru_local_batch_uses_jobs_limit(tmp_path):
    class FakeLocalConverter(MinerULocalConverter):
        def convert(self, source_pdf, output_dir):
            markdown = output_dir / "paper.md"
            output_dir.mkdir(parents=True, exist_ok=True)
            markdown.write_text(f"# {output_dir.name}\n", encoding="utf-8")
            (output_dir / "images").mkdir()
            return ConversionResult(ok=True, markdown_path=markdown, images_dir=output_dir / "images")

    items = []
    for name in ["one", "two", "three"]:
        bundle = tmp_path / name
        bundle.mkdir()
        pdf = bundle / "original.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        items.append(
            BatchConversionItem(
                bundle_dir=bundle,
                source_pdf=pdf,
                output_dir=bundle,
                paper_id=f"sha256:{name}",
                attempt=1,
                submitted_at="2026-05-23T00:00:00+00:00",
            )
        )

    results = FakeLocalConverter().convert_batch(items, tmp_path, jobs=2)

    assert [result.ok for result in results] == [True, True, True]
    assert all(result.data_id == item.paper_id for result, item in zip(results, items, strict=True))
