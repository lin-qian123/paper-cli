from __future__ import annotations

import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .base import BatchConversionItem, BatchConversionResult, ConversionResult
from .mineru_env import resolve_mineru_environment
from .mineru_normalize import normalize_mineru_directory


class MinerULocalConverter:
    name = "mineru-local"

    def __init__(
        self,
        *,
        executable: str | None = "mineru",
        local_backend: str | None = None,
        timeout: float | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.config = config or {}
        env = resolve_mineru_environment(self.config, cli_executable=executable)
        self.executable = env.executable or executable or "mineru"
        mineru_config = self.config.get("mineru", {}) if isinstance(self.config, dict) else {}
        self.local_backend = local_backend if local_backend is not None else mineru_config.get("local_backend")
        self.timeout = timeout

    def convert(self, source_pdf: Path, output_dir: Path) -> ConversionResult:
        if not source_pdf.exists():
            return ConversionResult(ok=False, error=f"PDF not found: {source_pdf}")
        tmp_output = Path(tempfile.mkdtemp())
        command = [self.executable, "-p", str(source_pdf), "-o", str(tmp_output)]
        if self.local_backend:
            command.extend(["-b", self.local_backend])
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError:
            shutil.rmtree(tmp_output, ignore_errors=True)
            return ConversionResult(ok=False, error="mineru CLI was not found on PATH")
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(tmp_output, ignore_errors=True)
            return ConversionResult(ok=False, error=f"mineru CLI timed out: {exc}")

        if completed.returncode != 0:
            shutil.rmtree(tmp_output, ignore_errors=True)
            detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
            return ConversionResult(ok=False, error=f"mineru CLI failed: {detail}")

        try:
            return self._normalize_output(tmp_output, output_dir, completed)
        except Exception as exc:
            return ConversionResult(ok=False, error=f"mineru local output normalization failed: {exc}")
        finally:
            shutil.rmtree(tmp_output, ignore_errors=True)

    def _normalize_output(
        self,
        tmp_output: Path,
        output_dir: Path,
        completed: subprocess.CompletedProcess,
    ) -> ConversionResult:
        try:
            normalized = normalize_mineru_directory(tmp_output, output_dir)
        except ValueError:
            return ConversionResult(
                ok=False,
                error="mineru CLI output did not contain Markdown",
                raw={"stdout": completed.stdout, "stderr": completed.stderr},
            )

        return ConversionResult(
            ok=True,
            markdown_path=normalized.markdown_path,
            images_dir=normalized.images_dir,
            raw={"stdout": completed.stdout, "stderr": completed.stderr},
        )

    def convert_batch(
        self,
        items: list[BatchConversionItem],
        output_dir: Path,
        *,
        jobs: int = 1,
    ) -> list[BatchConversionResult]:
        workers = max(1, min(int(jobs), len(items) or 1))

        def run_one(item: BatchConversionItem) -> BatchConversionResult:
            result = self.convert(item.source_pdf, item.output_dir)
            return BatchConversionResult(
                bundle_dir=item.bundle_dir,
                ok=result.ok,
                markdown_path=result.markdown_path,
                images_dir=result.images_dir,
                error=result.error,
                raw=result.raw,
                data_id=item.paper_id,
                remote_state="done" if result.ok else "failed",
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(run_one, items))
