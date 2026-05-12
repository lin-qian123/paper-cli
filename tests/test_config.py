import subprocess
import sys


def test_module_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "paper_cli", "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "paper-cli" in result.stdout
