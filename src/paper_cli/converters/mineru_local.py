from __future__ import annotations

import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .base import BatchConversionItem, BatchConversionResult, ConversionResult


class MinerULocalConverter:
    name = "mineru-local"

    def __init__(
        self,
        *,
        executable: str = "mineru",
        local_backend: str | None = None,
        timeout: float | None = None,
    ):
        self.executable = executable
        self.local_backend = local_backend
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
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_files = sorted(tmp_output.glob("**/*.md"))
        if not markdown_files:
            return ConversionResult(
                ok=False,
                error="mineru CLI output did not contain Markdown",
                raw={"stdout": completed.stdout, "stderr": completed.stderr},
            )

        markdown_path = output_dir / "paper.md"
        shutil.copy2(markdown_files[0], markdown_path)

        images_dir = output_dir / "images"
        if images_dir.exists():
            shutil.rmtree(images_dir)
        source_images = [
            path for path in tmp_output.glob("**/images") if path.is_dir() and any(path.iterdir())
        ]
        if source_images:
            shutil.copytree(source_images[0], images_dir)
        else:
            images_dir.mkdir(parents=True, exist_ok=True)

        raw_dir = output_dir / "raw" / "mineru"
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)
        for path in tmp_output.glob("**/*"):
            if path.is_dir() or path == markdown_files[0] or "images" in path.relative_to(tmp_output).parts:
                continue
            target = raw_dir / "_".join(path.relative_to(tmp_output).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

        return ConversionResult(
            ok=True,
            markdown_path=markdown_path,
            images_dir=images_dir,
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
