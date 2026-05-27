from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .base import BatchConversionItem, BatchConversionResult
from .mineru_normalize import normalize_mineru_zip


class MinerUApiBatchConverter:
    name = "mineru-api-batch"
    max_api_batch_size = 50

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        batch_size: int = 20,
        poll_interval: float = 3.0,
        max_wait_seconds: float | None = None,
        max_network_attempts: int = 3,
        retry_wait: float = 5.0,
    ):
        self.api_key = api_key or os.environ.get("MINERU_API_KEY")
        self.api_base = (
            api_base or os.environ.get("MINERU_API_BASE") or "https://mineru.net/api/v4"
        ).rstrip("/")
        self.batch_size = max(1, min(int(batch_size), self.max_api_batch_size))
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

    def convert_batch(
        self,
        items: list[BatchConversionItem],
        output_dir: Path,
        *,
        jobs: int = 1,
    ) -> list[BatchConversionResult]:
        if not self.api_key:
            return [
                BatchConversionResult(
                    bundle_dir=item.bundle_dir,
                    ok=False,
                    error="MINERU_API_KEY is not set",
                    data_id=item.paper_id,
                )
                for item in items
            ]

        results: list[BatchConversionResult] = []
        for chunk in self._chunks(items, self.batch_size):
            try:
                deadline = time.monotonic() + self.max_wait_seconds
                resume = self._resume_batch(chunk)
                if resume:
                    batch_id, submitted_items = resume
                else:
                    batch_id, submitted_items = self._submit_and_upload(
                        chunk, jobs=jobs, deadline=deadline
                    )
                results.extend(self._poll_and_download(batch_id, submitted_items, deadline))
            except Exception as exc:
                results.extend(
                    BatchConversionResult(
                        bundle_dir=item.bundle_dir,
                        ok=False,
                        error=str(exc),
                        data_id=item.paper_id,
                        remote_state="failed",
                    )
                    for item in chunk
                )
        return results

    def _chunks(
        self, items: list[BatchConversionItem], size: int
    ) -> list[list[BatchConversionItem]]:
        return [items[start : start + size] for start in range(0, len(items), size)]

    def _resume_batch(
        self, items: list[BatchConversionItem]
    ) -> tuple[str, list[BatchConversionItem]] | None:
        batch_id: str | None = None
        resumable: list[BatchConversionItem] = []
        for item in items:
            state = self._read_running_state(item.bundle_dir)
            if not state:
                return None
            if batch_id is None:
                batch_id = state["batch_id"]
            elif state["batch_id"] != batch_id:
                return None
            resumable.append(item)
        if batch_id and resumable:
            return batch_id, resumable
        return None

    def _read_running_state(self, bundle_dir: Path) -> dict | None:
        path = bundle_dir / "conversion.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if (
            payload.get("converter") == self.name
            and payload.get("state") == "running"
            and payload.get("batch_id")
            and payload.get("data_id")
        ):
            return payload
        return None

    def _submit_and_upload(
        self, items: list[BatchConversionItem], *, jobs: int, deadline: float
    ) -> tuple[str, list[BatchConversionItem]]:
        files = [
            {
                "name": item.source_pdf.name,
                "size": item.source_pdf.stat().st_size,
                "data_id": item.paper_id,
            }
            for item in items
        ]
        response = self._network_call(
            lambda: requests.post(
                f"{self.api_base}/file-urls/batch",
                json={"files": files},
                headers=self.headers,
                timeout=self._network_timeout(30, deadline),
            )
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or "MinerU batch upload URL request failed")
        batch_id = payload["data"]["batch_id"]
        upload_urls = payload["data"]["file_urls"]
        if len(upload_urls) != len(items):
            raise RuntimeError("MinerU returned an unexpected number of upload URLs")

        for item in items:
            self._write_running_conversion(item, batch_id)

        workers = max(1, min(int(jobs), len(items)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    self._upload_one,
                    item.source_pdf,
                    self._upload_url(upload_url),
                    deadline,
                )
                for item, upload_url in zip(items, upload_urls, strict=True)
            ]
            for future in futures:
                future.result()

        return batch_id, items

    def _upload_url(self, upload_url: str | dict) -> str:
        if isinstance(upload_url, dict):
            return upload_url.get("url") or upload_url.get("upload_url") or upload_url["file_url"]
        return upload_url

    def _upload_one(self, source_pdf: Path, upload_url: str, deadline: float) -> None:
        with source_pdf.open("rb") as handle:
            def upload_call() -> requests.Response:
                handle.seek(0)
                return requests.put(
                    upload_url,
                    data=handle,
                    timeout=self._network_timeout(120, deadline),
                )

            response = self._network_call(upload_call)
        response.raise_for_status()

    def _write_running_conversion(self, item: BatchConversionItem, batch_id: str) -> None:
        payload = {
            "schema_version": 1,
            "converter": self.name,
            "ok": False,
            "state": "running",
            "attempt": item.attempt,
            "submitted_at": item.submitted_at,
            "converted_at": None,
            "batch_id": batch_id,
            "data_id": item.paper_id,
            "remote_state": "running",
            "error": None,
            "raw_output_dir": "raw/mineru",
            "markdown": "paper.md",
            "images": "images",
        }
        (item.bundle_dir / "conversion.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _poll_and_download(
        self, batch_id: str, items: list[BatchConversionItem], deadline: float
    ) -> list[BatchConversionResult]:
        by_data_id = {item.paper_id: item for item in items}
        terminal: dict[str, dict] = {}
        polling_url = f"{self.api_base}/extract-results/batch/{batch_id}"
        while True:
            poll = self._network_call(
                lambda: requests.get(
                    polling_url,
                    headers=self.headers,
                    timeout=self._network_timeout(30, deadline),
                )
            )
            poll.raise_for_status()
            payload = poll.json()
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("msg") or "MinerU batch polling failed")
            for status in payload.get("data", {}).get("extract_result", []):
                data_id = status.get("data_id")
                if data_id not in by_data_id:
                    continue
                state = status.get("state")
                if state in {"done", "failed", "error", "cancelled"}:
                    terminal[data_id] = status
            if len(terminal) == len(by_data_id):
                break
            self._raise_if_deadline_expired(deadline)
            time.sleep(self.poll_interval)

        results: list[BatchConversionResult] = []
        for item in items:
            status = terminal[item.paper_id]
            state = status.get("state")
            if state == "done":
                results.append(self._download_done_item(item, batch_id, status, deadline))
            else:
                results.append(
                    BatchConversionResult(
                        bundle_dir=item.bundle_dir,
                        ok=False,
                        error=status.get("err_msg") or f"MinerU batch item {state}",
                        batch_id=batch_id,
                        data_id=item.paper_id,
                        remote_state=state,
                    )
                )
        return results

    def _download_done_item(
        self, item: BatchConversionItem, batch_id: str, status: dict, deadline: float
    ) -> BatchConversionResult:
        zip_url = status.get("full_zip_url")
        if not zip_url:
            return BatchConversionResult(
                bundle_dir=item.bundle_dir,
                ok=False,
                error="MinerU batch item finished without ZIP URL",
                batch_id=batch_id,
                data_id=item.paper_id,
                remote_state="done",
            )
        response = self._network_call(
            lambda: requests.get(zip_url, timeout=self._network_timeout(120, deadline))
        )
        response.raise_for_status()
        normalize = self._normalize_zip(response.content, item.output_dir)
        if not normalize.ok:
            normalize.batch_id = batch_id
            normalize.data_id = item.paper_id
            normalize.remote_state = "done"
            return normalize
        normalize.batch_id = batch_id
        normalize.data_id = item.paper_id
        normalize.remote_state = "done"
        normalize.raw["zip_url"] = zip_url
        return normalize

    def _normalize_zip(self, content: bytes, output_dir: Path) -> BatchConversionResult:
        try:
            normalized = normalize_mineru_zip(content, output_dir)
        except ValueError:
            return BatchConversionResult(
                bundle_dir=output_dir,
                ok=False,
                error="MinerU ZIP did not contain Markdown",
            )
        return BatchConversionResult(
            bundle_dir=output_dir,
            ok=True,
            markdown_path=normalized.markdown_path,
            images_dir=normalized.images_dir,
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

    def _network_timeout(self, default: float, deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"MinerU batch timed out after {self.max_wait_seconds:g} seconds")
        return max(1.0, min(float(default), remaining))

    def _raise_if_deadline_expired(self, deadline: float) -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"MinerU batch timed out after {self.max_wait_seconds:g} seconds")
