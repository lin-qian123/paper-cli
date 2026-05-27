from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

import requests

from .base import ConversionResult
from .mineru_normalize import normalize_mineru_zip


class MinerUConverter:
    name = "mineru"

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        poll_interval: float = 3.0,
        max_wait_seconds: float | None = None,
        max_network_attempts: int = 3,
        retry_wait: float = 5.0,
    ):
        self.api_key = api_key or os.environ.get("MINERU_API_KEY")
        self.api_base = (
            api_base or os.environ.get("MINERU_API_BASE") or "https://mineru.net/api/v4"
        ).rstrip("/")
        self.poll_interval = poll_interval
        self.max_wait_seconds = float(
            max_wait_seconds
            if max_wait_seconds is not None
            else os.environ.get("MINERU_MAX_WAIT_SECONDS", 30 * 60)
        )
        self.max_network_attempts = max(1, int(max_network_attempts))
        self.retry_wait = retry_wait

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
        response = self._network_call(
            lambda: requests.post(
                f"{self.api_base}/file-urls/batch",
                json={"files": [file_info]},
                headers=self.headers,
                timeout=30,
            )
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or "MinerU upload URL request failed")
        batch_id = payload["data"]["batch_id"]
        upload_url = payload["data"]["file_urls"][0]

        with source_pdf.open("rb") as handle:
            def upload_call() -> requests.Response:
                handle.seek(0)
                return requests.put(upload_url, data=handle, timeout=120)

            upload = self._network_call(upload_call)
        upload.raise_for_status()

        polling_url = f"{self.api_base}/extract-results/batch/{batch_id}"
        started_at = time.monotonic()
        while True:
            if time.monotonic() - started_at >= self.max_wait_seconds:
                raise TimeoutError(
                    f"MinerU task timed out after {self.max_wait_seconds:g} seconds"
                )
            poll = self._network_call(
                lambda: requests.get(polling_url, headers=self.headers, timeout=30)
            )
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
        response = self._network_call(lambda: requests.get(zip_url, timeout=120))
        response.raise_for_status()
        try:
            normalized = normalize_mineru_zip(response.content, output_dir)
        except ValueError:
            return ConversionResult(ok=False, error="MinerU ZIP did not contain Markdown")
        return ConversionResult(
            ok=True,
            markdown_path=normalized.markdown_path,
            images_dir=normalized.images_dir,
            raw={"zip_url": zip_url},
        )

    def _network_call(self, call: Callable[[], requests.Response]) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.max_network_attempts + 1):
            try:
                return call()
            except Exception as exc:
                last_error = exc
                if attempt == self.max_network_attempts:
                    break
                if self.retry_wait > 0:
                    time.sleep(self.retry_wait)
        raise RuntimeError(
            f"MinerU network request failed after {self.max_network_attempts} attempts: "
            f"{last_error}"
        ) from last_error
