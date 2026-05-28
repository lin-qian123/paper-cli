import subprocess
import sys

from paper_cli.cli import main
from paper_cli.config import load_config


def test_module_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "paper_cli", "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "usage: paper" in result.stdout


def test_init_creates_library_layout(tmp_path):
    library = tmp_path / "library"
    assert main(["init", str(library)]) == 0
    assert (library / "paper-cli.yaml").exists()
    assert (library / "collections").is_dir()
    assert (library / "inbox").is_dir()
    assert (library / "indexes" / "papers.jsonl").exists()
    assert (library / "indexes" / "jobs.jsonl").exists()
    config = load_config(library)
    assert config["schema_version"] == 1
    assert "naming" in config
    assert config["mineru"] == {
        "executable": "mineru",
        "local_backend": None,
        "local_jobs": "auto",
        "max_wait_seconds": None,
    }


def test_load_config_merges_mineru_overrides(tmp_path):
    library = tmp_path / "library"
    assert main(["init", str(library)]) == 0
    (library / "paper-cli.yaml").write_text(
        """
schema_version: 1
mineru:
  executable: /tmp/mineru/bin/mineru
  local_backend: pipeline
  local_jobs: 1
""",
        encoding="utf-8",
    )

    config = load_config(library)

    assert config["mineru"]["executable"] == "/tmp/mineru/bin/mineru"
    assert config["mineru"]["local_backend"] == "pipeline"
    assert config["mineru"]["local_jobs"] == 1
    assert config["mineru"]["max_wait_seconds"] is None
    assert "naming" in config
