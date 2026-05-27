import subprocess

from paper_cli.converters.mineru_env import (
    probe_mineru_version,
    resolve_mineru_environment,
)


def test_resolve_mineru_environment_uses_configured_path(tmp_path):
    executable = tmp_path / "mineru"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    env = resolve_mineru_environment({"mineru": {"executable": str(executable)}})

    assert env.exists is True
    assert env.executable == str(executable)


def test_resolve_mineru_environment_reports_missing_path(tmp_path):
    env = resolve_mineru_environment({"mineru": {"executable": str(tmp_path / "missing")}})

    assert env.exists is False
    assert "not found" in (env.error or "")


def test_resolve_mineru_environment_falls_back_to_path(monkeypatch):
    monkeypatch.setattr("paper_cli.converters.mineru_env.shutil.which", lambda value: "/usr/bin/mineru")

    env = resolve_mineru_environment({"mineru": {"executable": "mineru"}})

    assert env.exists is True
    assert env.executable == "/usr/bin/mineru"


def test_probe_mineru_version_parses_version(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="mineru, version 3.1.15\n", stderr="")

    monkeypatch.setattr("paper_cli.converters.mineru_env.subprocess.run", fake_run)

    assert probe_mineru_version("/usr/bin/mineru") == "3.1.15"
