from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

from .base import BatchConversionItem, BatchConversionResult
from .mineru_normalize import normalize_mineru_zip


@dataclass(frozen=True)
class _SplitPart:
    original: BatchConversionItem
    item: BatchConversionItem
    index: int
    page_start: int
    page_end: int
    page_count: int


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
        max_pages_per_part: int | None = None,
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
        self.max_pages_per_part = int(
            max_pages_per_part
            if max_pages_per_part is not None
            else os.environ.get("MINERU_MAX_PAGES_PER_PART", 195)
        )

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
            split_tmp = Path(tempfile.mkdtemp(prefix="paper-cli-mineru-split-"))
            try:
                submitted_chunk, split_parts = self._prepare_submission_items(chunk, split_tmp)
                deadline = time.monotonic() + self.max_wait_seconds
                resume = None if split_parts else self._resume_batch(submitted_chunk)
                if resume:
                    batch_id, submitted_items = resume
                else:
                    batch_id, submitted_items = self._submit_and_upload(
                        submitted_chunk, jobs=jobs, deadline=deadline
                    )
                submitted_results = self._poll_and_download(batch_id, submitted_items, deadline)
                results.extend(self._merge_split_results(chunk, submitted_results, split_parts))
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
            finally:
                shutil.rmtree(split_tmp, ignore_errors=True)
        return results

    def _prepare_submission_items(
        self, items: list[BatchConversionItem], split_tmp: Path
    ) -> tuple[list[BatchConversionItem], dict[Path, list[_SplitPart]]]:
        submitted: list[BatchConversionItem] = []
        split_parts: dict[Path, list[_SplitPart]] = {}
        for item in items:
            try:
                page_count = self._pdf_page_count(item.source_pdf)
            except Exception:
                submitted.append(item)
                continue
            if self.max_pages_per_part <= 0 or page_count <= self.max_pages_per_part:
                submitted.append(item)
                continue
            parts: list[_SplitPart] = []
            for index, page_start in enumerate(range(1, page_count + 1, self.max_pages_per_part), 1):
                page_end = min(page_start + self.max_pages_per_part - 1, page_count)
                part_dir = split_tmp / item.paper_id.replace(":", "_") / f"part-{index:03d}"
                part_pdf = part_dir / "original.pdf"
                part_dir.mkdir(parents=True, exist_ok=True)
                self._extract_pdf_pages(item.source_pdf, page_start, page_end, part_pdf)
                part_item = BatchConversionItem(
                    bundle_dir=part_dir,
                    source_pdf=part_pdf,
                    output_dir=part_dir,
                    paper_id=f"{item.paper_id}:part:{index:03d}",
                    attempt=item.attempt,
                    submitted_at=item.submitted_at,
                )
                submitted.append(part_item)
                parts.append(
                    _SplitPart(
                        original=item,
                        item=part_item,
                        index=index,
                        page_start=page_start,
                        page_end=page_end,
                        page_count=page_count,
                    )
                )
            split_parts[item.bundle_dir] = parts
        return submitted, split_parts

    def _pdf_page_count(self, source_pdf: Path) -> int:
        return len(PdfReader(str(source_pdf)).pages)

    def _extract_pdf_pages(
        self, source_pdf: Path, start_page: int, end_page: int, target_pdf: Path
    ) -> None:
        reader = PdfReader(str(source_pdf))
        writer = PdfWriter()
        for page_index in range(start_page - 1, end_page):
            writer.add_page(reader.pages[page_index])
        target_pdf.parent.mkdir(parents=True, exist_ok=True)
        with target_pdf.open("wb") as handle:
            writer.write(handle)

    def _merge_split_results(
        self,
        originals: list[BatchConversionItem],
        submitted_results: list[BatchConversionResult],
        split_parts: dict[Path, list[_SplitPart]],
    ) -> list[BatchConversionResult]:
        by_bundle = {result.bundle_dir: result for result in submitted_results}
        merged: list[BatchConversionResult] = []
        for original in originals:
            parts = split_parts.get(original.bundle_dir)
            if not parts:
                merged.append(by_bundle[original.bundle_dir])
                continue
            part_results = [by_bundle[part.item.bundle_dir] for part in parts]
            failed = next((part for part, result in zip(parts, part_results) if not result.ok), None)
            if failed:
                failed_result = by_bundle[failed.item.bundle_dir]
                error = failed_result.error or "MinerU split part failed"
                merged.append(
                    BatchConversionResult(
                        bundle_dir=original.bundle_dir,
                        ok=False,
                        error=f"split part {failed.index} failed: {error}",
                        raw=self._split_raw(parts, part_results),
                        data_id=original.paper_id,
                        remote_state="failed",
                    )
                )
                continue
            merged.append(self._merge_successful_split_parts(original, parts, part_results))
        return merged

    def _merge_successful_split_parts(
        self,
        original: BatchConversionItem,
        parts: list[_SplitPart],
        part_results: list[BatchConversionResult],
    ) -> BatchConversionResult:
        bundle_dir = original.bundle_dir
        markdown_path = bundle_dir / "paper.md"
        images_dir = bundle_dir / "images"
        raw_dir = bundle_dir / "raw" / "mineru"
        if images_dir.exists():
            shutil.rmtree(images_dir)
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        images_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        markdown_parts: list[str] = []
        for part, result in zip(parts, part_results):
            namespace = f"part-{part.index:03d}"
            part_markdown = (result.markdown_path or (part.item.output_dir / "paper.md")).read_text(
                encoding="utf-8"
            )
            part_markdown = self._rewrite_part_image_paths(part_markdown, namespace)
            markdown_parts.extend(
                [
                    f"<!-- paper-cli split part {part.index} pages {part.page_start}-{part.page_end} -->",
                    part_markdown.strip(),
                    "",
                ]
            )
            source_images = result.images_dir or (part.item.output_dir / "images")
            if source_images.exists():
                shutil.copytree(source_images, images_dir / namespace)
            else:
                (images_dir / namespace).mkdir(parents=True, exist_ok=True)
            source_raw = part.item.output_dir / "raw" / "mineru"
            if source_raw.exists():
                shutil.copytree(source_raw, raw_dir / namespace)

        markdown_path.write_text("\n".join(markdown_parts).rstrip() + "\n", encoding="utf-8")
        return BatchConversionResult(
            bundle_dir=bundle_dir,
            ok=True,
            markdown_path=markdown_path,
            images_dir=images_dir,
            raw=self._split_raw(parts, part_results),
            data_id=original.paper_id,
            remote_state="done",
        )

    def _rewrite_part_image_paths(self, markdown: str, namespace: str) -> str:
        return re.sub(
            r"(\]\(|[\"'])\.?/?images/",
            rf"\1images/{namespace}/",
            markdown,
        )

    def _split_raw(
        self, parts: list[_SplitPart], part_results: list[BatchConversionResult]
    ) -> dict:
        return {
            "split": True,
            "max_pages_per_part": self.max_pages_per_part,
            "page_count": parts[0].page_count if parts else 0,
            "split_parts": [
                {
                    "part": part.index,
                    "page_start": part.page_start,
                    "page_end": part.page_end,
                    "data_id": part.item.paper_id,
                    "batch_id": result.batch_id,
                    "remote_state": result.remote_state,
                    "ok": result.ok,
                    "error": result.error,
                    "zip_url": result.raw.get("zip_url"),
                }
                for part, result in zip(parts, part_results)
            ],
        }

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
