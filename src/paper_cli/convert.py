from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .config import load_config
from .converters.base import BatchConversionItem, BatchConversionResult, ConversionResult, Converter
from .converters.mineru_metadata import extract_mineru_metadata
from .indexes import append_job, find_paper_dirs, rebuild_papers_index
from .models import PaperRecord, read_paper, utc_now_iso, write_paper
from .naming import render_name, resolve_duplicate_name, sanitize_name


def extract_metadata_from_markdown(markdown: str) -> dict:
    return extract_metadata_details_from_markdown(markdown)[0]


def extract_metadata_details_from_markdown(
    markdown: str,
) -> tuple[dict, dict[str, str], dict[str, str]]:
    return extract_mineru_metadata(markdown)


def _normalize_title_for_match(value: str) -> str:
    value = re.sub(r"[\u2010-\u2015\u2212]", "-", value)
    return " ".join(value.split())


def infer_creator_from_title_prefix(
    previous_title: str | None, converted_title: str | None
) -> str | None:
    if not previous_title or not converted_title:
        return None
    previous = _normalize_title_for_match(previous_title)
    converted = _normalize_title_for_match(converted_title)
    if previous == converted or not previous.endswith(converted):
        return None
    prefix = previous[: -len(converted)].strip()
    prefix = re.sub(r"[-:：|丨]+$", "", prefix).strip()
    if not prefix or len(prefix) > 80:
        return None
    if re.search(r"\d", prefix):
        return None
    return prefix


CONFIDENCE_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _confidence_rank(value: str | None) -> int:
    return CONFIDENCE_RANK.get(value or "", 0)


def _should_update(existing_confidence: str | None, update_confidence: str | None) -> bool:
    return _confidence_rank(update_confidence) >= _confidence_rank(existing_confidence)


def bad_converted_title(existing_title: str | None, converted_title: str | None) -> bool:
    if not converted_title:
        return False
    title = converted_title.strip()
    if title.endswith(("\\", "/", "|")) or "\ufffd" in title:
        return True
    letters = [ch for ch in title if ch.isalpha()]
    if existing_title and len(letters) >= 20 and title.upper() == title:
        return True
    if re.search(r"[a-z][A-Z]", title):
        return True
    return False


def _merge_metadata(
    existing: dict,
    existing_sources: dict[str, str],
    existing_confidence: dict[str, str],
    update: dict,
    update_sources: dict[str, str],
    update_confidence: dict[str, str],
) -> tuple[dict, dict[str, str], dict[str, str]]:
    merged = dict(existing)
    merged_sources = dict(existing_sources)
    merged_confidence = dict(existing_confidence)
    inferred_creator = infer_creator_from_title_prefix(
        str(existing.get("title") or ""),
        str(update.get("title") or ""),
    )
    if inferred_creator and not update.get("creators"):
        update = dict(update)
        update["creators"] = [{"name": inferred_creator, "role": "author"}]
        update_sources = dict(update_sources)
        update_sources["creators"] = "filename-title-prefix"
        update_confidence = dict(update_confidence)
        update_confidence["creators"] = "medium"

    for key, value in update.items():
        if value in (None, "", []):
            continue
        if key == "title" and bad_converted_title(
            str(existing.get("title") or ""),
            str(value),
        ):
            continue
        if _should_update(merged_confidence.get(key), update_confidence.get(key)):
            merged[key] = value
            if key in update_sources:
                merged_sources[key] = update_sources[key]
            if key in update_confidence:
                merged_confidence[key] = update_confidence[key]
    return merged, merged_sources, merged_confidence


def maybe_rename_bundle(library_dir: Path, bundle_dir: Path, record: PaperRecord) -> Path:
    if record.name_locked or record.status.get("naming") == "review":
        record.status["naming"] = "review"
        write_paper(bundle_dir, record)
        return bundle_dir

    config = load_config(library_dir)
    template = config.get("naming", {}).get("template", "")
    rendered = sanitize_name(render_name(template, record.metadata) or record.name)
    if rendered == bundle_dir.name:
        record.name = rendered
        write_paper(bundle_dir, record)
        return bundle_dir

    target = bundle_dir.parent / resolve_duplicate_name(
        rendered,
        {p.name for p in bundle_dir.parent.iterdir() if p.is_dir() and p != bundle_dir},
    )
    previous = record.name
    record.name = target.name
    if previous and previous not in record.previous_names:
        record.previous_names.append(previous)
    record.naming["last_renamed_at"] = utc_now_iso()
    write_paper(bundle_dir, record)
    shutil.move(str(bundle_dir), str(target))
    return target


def _read_previous_attempt(bundle_dir: Path) -> int:
    path = bundle_dir / "conversion.json"
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    return int(payload.get("attempt") or 0)


def _converter_name(converter: Converter) -> str:
    return getattr(converter, "name", converter.__class__.__name__)


def _relative_output_path(bundle_dir: Path, path: Path | None, fallback: str) -> str | None:
    if path is None:
        return fallback
    try:
        return str(path.relative_to(bundle_dir))
    except ValueError:
        return str(path)


def _write_conversion_json(
    bundle_dir: Path,
    *,
    converter_name: str,
    attempt: int,
    submitted_at: str,
    ok: bool,
    state: str,
    error: str | None = None,
    markdown_path: Path | None = None,
    images_dir: Path | None = None,
    raw_output_dir: str | None = None,
    batch_id: str | None = None,
    data_id: str | None = None,
    remote_state: str | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "converter": converter_name,
        "ok": ok,
        "state": state,
        "attempt": attempt,
        "submitted_at": submitted_at,
        "converted_at": utc_now_iso(),
        "error": error,
        "raw_output_dir": raw_output_dir,
        "markdown": _relative_output_path(bundle_dir, markdown_path, "paper.md"),
        "images": _relative_output_path(bundle_dir, images_dir, "images"),
    }
    if batch_id:
        payload["batch_id"] = batch_id
    if data_id:
        payload["data_id"] = data_id
    if remote_state:
        payload["remote_state"] = remote_state
    (bundle_dir / "conversion.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _bundle_relative(library_dir: Path, bundle_dir: Path) -> str:
    try:
        return str(bundle_dir.relative_to(library_dir))
    except ValueError:
        return str(bundle_dir)


def _append_conversion_job(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    *,
    event: str,
    converter_name: str,
    attempt: int,
    state: str,
    ok: bool | None = None,
    error: str | None = None,
    batch_id: str | None = None,
    data_id: str | None = None,
    remote_state: str | None = None,
) -> None:
    payload = {
        "event": event,
        "at": utc_now_iso(),
        "paper_id": record.id,
        "bundle_path": _bundle_relative(library_dir, bundle_dir),
        "converter": converter_name,
        "attempt": attempt,
        "state": state,
    }
    if ok is not None:
        payload["ok"] = ok
    if error:
        payload["error"] = error
    if batch_id:
        payload["batch_id"] = batch_id
    if data_id:
        payload["data_id"] = data_id
    if remote_state:
        payload["remote_state"] = remote_state
    append_job(library_dir, payload)


def _raw_output_dir_for_converter(converter_name: str) -> str | None:
    if converter_name in {"mineru", "mineru-api-batch", "mineru-local"}:
        return "raw/mineru"
    return None


def _finish_conversion_result(
    library_dir: Path,
    bundle_dir: Path,
    record: PaperRecord,
    *,
    converter_name: str,
    attempt: int,
    submitted_at: str,
    result: ConversionResult | BatchConversionResult,
) -> Path | None:
    if not result.ok:
        record.status["conversion"] = "failed"
        write_paper(bundle_dir, record)
        _write_conversion_json(
            bundle_dir,
            converter_name=converter_name,
            attempt=attempt,
            submitted_at=submitted_at,
            ok=False,
            state="failed",
            error=result.error,
            markdown_path=result.markdown_path,
            images_dir=result.images_dir,
            batch_id=getattr(result, "batch_id", None),
            data_id=getattr(result, "data_id", None),
            remote_state=getattr(result, "remote_state", None),
        )
        _append_conversion_job(
            library_dir,
            bundle_dir,
            record,
            event="conversion-finished",
            converter_name=converter_name,
            attempt=attempt,
            state="failed",
            ok=False,
            error=result.error,
            batch_id=getattr(result, "batch_id", None),
            data_id=getattr(result, "data_id", None),
            remote_state=getattr(result, "remote_state", None),
        )
        return None

    markdown_path = result.markdown_path or (bundle_dir / "paper.md")
    metadata_update, update_sources, update_confidence = extract_mineru_metadata(
        markdown_path.read_text(encoding="utf-8"),
        existing=record.metadata,
    )
    bad_title = bad_converted_title(
        str(record.metadata.get("title") or ""),
        str(metadata_update.get("title") or ""),
    )
    if bad_title:
        metadata_update = dict(metadata_update)
        update_sources = dict(update_sources)
        update_confidence = dict(update_confidence)
        metadata_update.pop("title", None)
        update_sources.pop("title", None)
        update_confidence.pop("title", None)
    (
        record.metadata,
        record.metadata_sources,
        record.metadata_confidence,
    ) = _merge_metadata(
        record.metadata,
        record.metadata_sources,
        record.metadata_confidence,
        metadata_update,
        update_sources,
        update_confidence,
    )
    record.status["conversion"] = "done"
    record.status["metadata"] = "complete" if record.metadata.get("title") else "partial"
    record.status["naming"] = "review" if bad_title else "metadata"
    write_paper(bundle_dir, record)
    _write_conversion_json(
        bundle_dir,
        converter_name=converter_name,
        attempt=attempt,
        submitted_at=submitted_at,
        ok=True,
        state="done",
        markdown_path=markdown_path,
        images_dir=result.images_dir or (bundle_dir / "images"),
        raw_output_dir=_raw_output_dir_for_converter(converter_name),
        batch_id=getattr(result, "batch_id", None),
        data_id=getattr(result, "data_id", None),
        remote_state=getattr(result, "remote_state", None),
    )
    renamed_bundle = maybe_rename_bundle(library_dir, bundle_dir, record)
    _append_conversion_job(
        library_dir,
        renamed_bundle,
        record,
        event="conversion-finished",
        converter_name=converter_name,
        attempt=attempt,
        state="done",
        ok=True,
        batch_id=getattr(result, "batch_id", None),
        data_id=getattr(result, "data_id", None),
        remote_state=getattr(result, "remote_state", None),
    )
    return renamed_bundle


def _convert_pending_batch(
    library_dir: Path,
    converter,
    *,
    batch_size: int,
    jobs: int,
) -> list[Path]:
    converted: list[Path] = []
    converter_name = _converter_name(converter)
    pending: list[BatchConversionItem] = []
    records: dict[Path, PaperRecord] = {}
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") == "done":
            continue
        attempt = _read_previous_attempt(bundle_dir) + 1
        submitted_at = utc_now_iso()
        records[bundle_dir] = record
        pending.append(
            BatchConversionItem(
                bundle_dir=bundle_dir,
                source_pdf=bundle_dir / "original.pdf",
                output_dir=bundle_dir,
                paper_id=record.id,
                attempt=attempt,
                submitted_at=submitted_at,
            )
        )

    for start in range(0, len(pending), batch_size):
        chunk = pending[start : start + batch_size]
        for item in chunk:
            _append_conversion_job(
                library_dir,
                item.bundle_dir,
                records[item.bundle_dir],
                event="conversion-started",
                converter_name=converter_name,
                attempt=item.attempt,
                state="running",
            )
        try:
            results = converter.convert_batch(chunk, library_dir, jobs=jobs)
        except (KeyboardInterrupt, SystemExit) as exc:
            error = exc.__class__.__name__
            for item in chunk:
                record = records[item.bundle_dir]
                record.status["conversion"] = "failed"
                write_paper(item.bundle_dir, record)
                _write_conversion_json(
                    item.bundle_dir,
                    converter_name=converter_name,
                    attempt=item.attempt,
                    submitted_at=item.submitted_at,
                    ok=False,
                    state="interrupted",
                    error=error,
                )
                _append_conversion_job(
                    library_dir,
                    item.bundle_dir,
                    record,
                    event="conversion-finished",
                    converter_name=converter_name,
                    attempt=item.attempt,
                    state="interrupted",
                    ok=False,
                    error=error,
                )
            rebuild_papers_index(library_dir)
            raise
        for result in results:
            item = next(item for item in chunk if item.bundle_dir == result.bundle_dir)
            renamed_bundle = _finish_conversion_result(
                library_dir,
                result.bundle_dir,
                records[result.bundle_dir],
                converter_name=converter_name,
                attempt=item.attempt,
                submitted_at=item.submitted_at,
                result=result,
            )
            if renamed_bundle is not None:
                converted.append(renamed_bundle)
    rebuild_papers_index(library_dir)
    return converted


def convert_pending(
    library_dir: Path,
    converter: Converter,
    *,
    batch_size: int = 20,
    jobs: int = 1,
) -> list[Path]:
    if hasattr(converter, "convert_batch"):
        return _convert_pending_batch(library_dir, converter, batch_size=batch_size, jobs=jobs)

    converted: list[Path] = []
    converter_name = _converter_name(converter)
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") == "done":
            continue
        attempt = _read_previous_attempt(bundle_dir) + 1
        submitted_at = utc_now_iso()
        _append_conversion_job(
            library_dir,
            bundle_dir,
            record,
            event="conversion-started",
            converter_name=converter_name,
            attempt=attempt,
            state="running",
        )
        try:
            result = converter.convert(bundle_dir / "original.pdf", bundle_dir)
        except (KeyboardInterrupt, SystemExit) as exc:
            record.status["conversion"] = "failed"
            write_paper(bundle_dir, record)
            error = exc.__class__.__name__
            _write_conversion_json(
                bundle_dir,
                converter_name=converter_name,
                attempt=attempt,
                submitted_at=submitted_at,
                ok=False,
                state="interrupted",
                error=error,
            )
            _append_conversion_job(
                library_dir,
                bundle_dir,
                record,
                event="conversion-finished",
                converter_name=converter_name,
                attempt=attempt,
                state="interrupted",
                ok=False,
                error=error,
            )
            rebuild_papers_index(library_dir)
            raise
        renamed_bundle = _finish_conversion_result(
            library_dir,
            bundle_dir,
            record,
            converter_name=converter_name,
            attempt=attempt,
            submitted_at=submitted_at,
            result=result,
        )
        if renamed_bundle is not None:
            converted.append(renamed_bundle)
    rebuild_papers_index(library_dir)
    return converted
