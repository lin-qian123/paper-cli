from __future__ import annotations

import io
import os
import shutil
import time
import zipfile
from pathlib import Path

import requests

from .base import ConversionResult


class MinerUConverter:
    name = "mineru"

    def __init__(
        self, api_key: str | None = None, api_base: str | None = None, poll_interval: float = 3.0
    ):
        self.api_key = api_key or os.environ.get("MINERU_API_KEY")
        self.api_base = (
            api_base or os.environ.get("MINERU_API_BASE") or "https://mineru.net/api/v4"
        ).rstrip("/")
        self.poll_interval = poll_interval

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def convert(self, source_pdf: Path, output_dir: Path) -> ConversionResult:
        if not self.api_key:
            return ConversionResult(ok=False, error="MINERU_API_KEY is not set")
        if not source_pdf.exists():
            return ConversionResult(ok=False, error=f"PDF not found: {source_pdf}")
        try:
            zip_url = self._submit_and_wait(source_pdf)
            if not zip_url:
                return ConversionResult(ok=False, error="MinerU conversion failed without ZIP URL")
            return self._download_and_normalize(zip_url, output_dir)
        except Exception as exc:
            return ConversionResult(ok=False, error=str(exc))

    def _submit_and_wait(self, source_pdf: Path) -> str | None:
        file_info = {"name": source_pdf.name, "size": source_pdf.stat().st_size}
        response = requests.post(
            f"{self.api_base}/file-urls/batch",
            json={"files": [file_info]},
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or "MinerU upload URL request failed")
        batch_id = payload["data"]["batch_id"]
        upload_url = payload["data"]["file_urls"][0]

        with source_pdf.open("rb") as handle:
            upload = requests.put(upload_url, data=handle, timeout=120)
        upload.raise_for_status()

        polling_url = f"{self.api_base}/extract-results/batch/{batch_id}"
        while True:
            poll = requests.get(polling_url, headers=self.headers, timeout=30)
            poll.raise_for_status()
            content = poll.json()
            if content.get("code") != 0:
                raise RuntimeError(content.get("msg") or "MinerU polling failed")
            results = content.get("data", {}).get("extract_result", [])
            if not results:
                time.sleep(self.poll_interval)
                continue
            status = results[0]
            state = status.get("state")
            if state == "done":
                return status.get("full_zip_url")
            if state in {"error", "failed", "cancelled"}:
                raise RuntimeError(status.get("err_msg") or f"MinerU task {state}")
            time.sleep(self.poll_interval)

    def _download_and_normalize(self, zip_url: str, output_dir: Path) -> ConversionResult:
        response = requests.get(zip_url, timeout=120)
        response.raise_for_status()
        output_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            extracted_files = [Path(name) for name in archive.namelist() if not name.endswith("/")]
            archive.extractall(output_dir)

        markdown_files = sorted(output_dir.glob("**/*.md"))
        if not markdown_files:
            return ConversionResult(ok=False, error="MinerU ZIP did not contain Markdown")
        markdown_path = output_dir / "paper.md"
        if markdown_files[0] != markdown_path:
            shutil.move(str(markdown_files[0]), markdown_path)

        images_dir = output_dir / "images"
        image_dirs = [
            path for path in output_dir.glob("**/images") if path.is_dir() and path != images_dir
        ]
        if image_dirs and not images_dir.exists():
            shutil.move(str(image_dirs[0]), images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)
        self._move_raw_sidecars(output_dir, extracted_files)
        return ConversionResult(
            ok=True, markdown_path=markdown_path, images_dir=images_dir, raw={"zip_url": zip_url}
        )

    def _move_raw_sidecars(self, output_dir: Path, extracted_files: list[Path]) -> None:
        raw_dir = output_dir / "raw" / "mineru"
        for relative in extracted_files:
            source = output_dir / relative
            if not source.exists() or source == output_dir / "paper.md":
                continue
            if source.is_relative_to(output_dir / "images"):
                continue
            if "images" in source.relative_to(output_dir).parts:
                continue
            raw_dir.mkdir(parents=True, exist_ok=True)
            target = raw_dir / source.name
            if target.exists():
                target = raw_dir / "_".join(source.relative_to(output_dir).parts)
            shutil.move(str(source), str(target))
        for directory in sorted(
            output_dir.glob("**/*"), key=lambda path: len(path.parts), reverse=True
        ):
            if directory == raw_dir or raw_dir in directory.parents:
                continue
            if directory.is_dir() and directory != output_dir and not any(directory.iterdir()):
                directory.rmdir()
