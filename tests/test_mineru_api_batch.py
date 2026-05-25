import io
import json
import zipfile

from paper_cli.converters.base import BatchConversionItem
from paper_cli.converters.mineru_api_batch import MinerUApiBatchConverter


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def make_item(tmp_path, name, paper_id=None):
    bundle = tmp_path / name
    bundle.mkdir()
    pdf = bundle / "original.pdf"
    pdf.write_bytes(f"%PDF-1.4\n{name}\n".encode())
    return BatchConversionItem(
        bundle_dir=bundle,
        source_pdf=pdf,
        output_dir=bundle,
        paper_id=paper_id or f"sha256:{name}",
        attempt=1,
        submitted_at="2026-05-23T00:00:00+00:00",
    )


def zip_bytes(markdown="# Converted\n"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("result/full.md", markdown)
        archive.writestr("result/images/fig.png", b"png")
    return buffer.getvalue()


def test_mineru_api_batch_caps_requests_at_50_and_uploads_with_stable_data_id(
    tmp_path, monkeypatch
):
    items = [make_item(tmp_path, f"paper-{index}") for index in range(51)]
    post_file_counts = []
    posted_data_ids = []
    upload_calls = {"count": 0}

    def fake_post(url, json=None, **kwargs):
        post_file_counts.append(len(json["files"]))
        posted_data_ids.extend(file["data_id"] for file in json["files"])
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "batch_id": f"batch-{len(post_file_counts)}",
                    "file_urls": [f"https://upload.example/{i}" for i in range(len(json["files"]))],
                },
            }
        )

    def fake_put(*args, **kwargs):
        upload_calls["count"] += 1
        return FakeResponse({})

    def fake_get(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {"data_id": item.paper_id, "state": "failed", "err_msg": "queued failure"}
                        for item in items
                    ]
                },
            }
        )

    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.get", fake_get)

    results = MinerUApiBatchConverter(api_key="test-key", batch_size=100, poll_interval=0).convert_batch(
        items, tmp_path, jobs=4
    )

    assert post_file_counts == [50, 1]
    assert posted_data_ids == [item.paper_id for item in items]
    assert upload_calls["count"] == 51
    assert len(results) == 51


def test_mineru_api_batch_downloads_done_items_and_reports_failed_items(tmp_path, monkeypatch):
    ok_item = make_item(tmp_path, "ok")
    failed_item = make_item(tmp_path, "failed")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example/ok", "https://upload.example/failed"],
                },
            }
        )

    def fake_put(*args, **kwargs):
        return FakeResponse({})

    def fake_get(url, *args, **kwargs):
        if "extract-results" in url:
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {
                                "data_id": ok_item.paper_id,
                                "state": "done",
                                "full_zip_url": "https://download.example/ok.zip",
                            },
                            {
                                "data_id": failed_item.paper_id,
                                "state": "failed",
                                "err_msg": "parse failed",
                            },
                        ]
                    },
                }
            )
        return FakeResponse(content=zip_bytes("# Batch Converted\n"))

    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.get", fake_get)

    results = MinerUApiBatchConverter(api_key="test-key", poll_interval=0).convert_batch(
        [ok_item, failed_item], tmp_path, jobs=2
    )

    by_bundle = {result.bundle_dir.name: result for result in results}
    assert by_bundle["ok"].ok is True
    assert (ok_item.bundle_dir / "paper.md").read_text(encoding="utf-8") == "# Batch Converted\n"
    assert (ok_item.bundle_dir / "images" / "fig.png").exists()
    assert by_bundle["ok"].batch_id == "batch-1"
    assert by_bundle["failed"].ok is False
    assert by_bundle["failed"].error == "parse failed"


def test_mineru_api_batch_resumes_existing_running_batch_without_resubmitting(
    tmp_path, monkeypatch
):
    item = make_item(tmp_path, "resume")
    (item.bundle_dir / "conversion.json").write_text(
        json.dumps(
            {
                "state": "running",
                "converter": "mineru-api-batch",
                "batch_id": "existing-batch",
                "data_id": item.paper_id,
            }
        ),
        encoding="utf-8",
    )
    post_calls = {"count": 0}
    put_calls = {"count": 0}

    def fake_post(*args, **kwargs):
        post_calls["count"] += 1
        return FakeResponse({})

    def fake_put(*args, **kwargs):
        put_calls["count"] += 1
        return FakeResponse({})

    def fake_get(url, *args, **kwargs):
        if "extract-results" in url:
            assert url.endswith("/existing-batch")
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {
                                "data_id": item.paper_id,
                                "state": "done",
                                "full_zip_url": "https://download.example/resume.zip",
                            }
                        ]
                    },
                }
            )
        return FakeResponse(content=zip_bytes("# Resumed\n"))

    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.get", fake_get)

    result = MinerUApiBatchConverter(api_key="test-key", poll_interval=0).convert_batch(
        [item], tmp_path, jobs=1
    )[0]

    assert result.ok is True
    assert post_calls["count"] == 0
    assert put_calls["count"] == 0
    assert (item.bundle_dir / "paper.md").read_text(encoding="utf-8") == "# Resumed\n"


def test_mineru_api_batch_writes_running_state_before_upload_failure(tmp_path, monkeypatch):
    item = make_item(tmp_path, "upload-failure")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {"batch_id": "batch-before-upload", "file_urls": ["https://upload.example"]},
            }
        )

    def fake_put(*args, **kwargs):
        raise TimeoutError("upload timeout")

    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.put", fake_put)

    result = MinerUApiBatchConverter(
        api_key="test-key",
        poll_interval=0,
        retry_wait=0,
    ).convert_batch([item], tmp_path, jobs=1)[0]

    payload = json.loads((item.bundle_dir / "conversion.json").read_text(encoding="utf-8"))
    assert result.ok is False
    assert payload["state"] == "running"
    assert payload["batch_id"] == "batch-before-upload"
    assert payload["data_id"] == item.paper_id


def test_mineru_api_batch_bounds_upload_timeout_by_remaining_batch_wait(tmp_path, monkeypatch):
    item = make_item(tmp_path, "bounded-timeout")
    upload_timeouts = []

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {"batch_id": "batch-timeout", "file_urls": ["https://upload.example"]},
            }
        )

    def fake_put(*args, **kwargs):
        upload_timeouts.append(kwargs["timeout"])
        return FakeResponse({})

    def fake_get(*args, **kwargs):
        return FakeResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {"data_id": item.paper_id, "state": "failed", "err_msg": "done"}
                    ]
                },
            }
        )

    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.post", fake_post)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.put", fake_put)
    monkeypatch.setattr("paper_cli.converters.mineru_api_batch.requests.get", fake_get)

    MinerUApiBatchConverter(
        api_key="test-key",
        max_wait_seconds=5,
        poll_interval=0,
    ).convert_batch([item], tmp_path, jobs=1)

    assert upload_timeouts
    assert max(upload_timeouts) <= 5
