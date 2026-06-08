from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path
from typing import Any

from paper_cli.config import init_library, load_config
from paper_cli.convert import convert_pending
from paper_cli.converters.local_zip import LocalFixtureConverter
from paper_cli.converters.mineru_jobs import resolve_local_jobs
from paper_cli.doctor import library_status, run_doctor
from paper_cli.importer import import_path
from paper_cli.indexes import find_paper_dirs
from paper_cli.models import read_paper


def run_qed_validation(
    *,
    source: Path,
    library_root: Path,
    count: int = 30,
    seed: int = 20260525,
    name: str | None = None,
    converter_name: str = "mineru-local",
    local_backend: str | None = None,
    batch_size: int = 1,
    jobs: int | None = None,
    max_pages_per_part: int | None = None,
    fixture_output: Path | None = None,
    no_convert: bool = False,
    replace: bool = False,
) -> dict[str, Any]:
    source = source.expanduser()
    library_root = library_root.expanduser()
    run_name = name or f"paper-cli-qed-validation-{seed}-{count}"
    library_dir = library_root / run_name
    sample_input = library_root / f"{run_name}-sample-input"
    sample_list = library_root / f"{run_name}-sample-list.txt"
    report_path = library_root / f"{run_name}-test-report.md"

    _prepare_output_path(library_dir, replace=replace)
    _prepare_output_path(sample_input, replace=replace)
    if sample_list.exists() and replace:
        sample_list.unlink()
    if report_path.exists() and replace:
        report_path.unlink()

    sample = select_qed_sample(source, count=count, seed=seed)
    sample_input.mkdir(parents=True, exist_ok=False)
    with sample_list.open("w", encoding="utf-8") as handle:
        for index, pdf in enumerate(sample, 1):
            target = sample_input / f"{index:02d}-{pdf.name}"
            os.symlink(pdf, target)
            handle.write(str(pdf) + "\n")

    init_library(library_dir)
    imported = import_path(library_dir, sample_input, collection=f"QED/random-{count}")
    duplicate_imported = import_path(library_dir, sample_input, collection=f"QED/random-{count}")
    pre_status = library_status(library_dir)
    pre_doctor = run_doctor(library_dir)

    converted: list[Path] = []
    if not no_convert:
        converter = _build_converter(
            converter_name,
            library_dir=library_dir,
            local_backend=local_backend,
            batch_size=batch_size,
            max_pages_per_part=max_pages_per_part,
            fixture_output=fixture_output,
        )
        effective_jobs = jobs
        if converter_name == "mineru-local":
            effective_jobs = resolve_local_jobs(
                load_config(library_dir),
                cli_jobs=jobs,
                pending_count=_pending_count(library_dir),
            )
        elif effective_jobs is None:
            effective_jobs = 4
        converted = convert_pending(
            library_dir,
            converter,
            batch_size=batch_size,
            jobs=effective_jobs,
        )

    final_status = library_status(library_dir)
    strict_issues = run_doctor(library_dir, strict=True)
    counts = artifact_counts(library_dir)
    payload = {
        "ok": not pre_doctor and (no_convert or not strict_issues),
        "library": str(library_dir),
        "sample_input": str(sample_input),
        "sample_list": str(sample_list),
        "report": str(report_path),
        "sampled": len(sample),
        "imported": len(imported),
        "duplicate_imported": len(duplicate_imported),
        "converted": len(converted),
        "pre_status": pre_status,
        "final_status": final_status,
        "pre_doctor": [issue.to_dict() for issue in pre_doctor],
        "strict_doctor": [issue.to_dict() for issue in strict_issues],
        "artifact_counts": counts,
        "no_convert": no_convert,
        "converter": None if no_convert else converter_name,
    }
    write_report(report_path, payload)
    return payload


def select_qed_sample(source: Path, *, count: int, seed: int) -> list[Path]:
    pdfs = sorted(source.rglob("*.pdf"))
    if count > len(pdfs):
        raise ValueError(f"Requested {count} PDFs but only found {len(pdfs)} in {source}")
    rng = random.Random(seed)
    return rng.sample(pdfs, count)


def artifact_counts(library_dir: Path) -> dict[str, int]:
    return {
        "bundles": len(find_paper_dirs(library_dir)),
        "paper_md": _count(library_dir, "paper.md"),
        "images": len([path for path in library_dir.rglob("images") if path.is_dir()]),
        "raw_mineru": len(
            [path for path in library_dir.rglob("raw/mineru") if path.is_dir()]
        ),
        "conversion_json": _count(library_dir, "conversion.json"),
        "summary_json": _count(library_dir, "summary.json"),
        "repair_json": _count(library_dir, "repair.json"),
    }


def write_report(report_path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# paper-cli QED validation report",
        "",
        f"- Library: `{payload['library']}`",
        f"- Sample input: `{payload['sample_input']}`",
        f"- Sample list: `{payload['sample_list']}`",
        f"- Sampled: {payload['sampled']}",
        f"- Imported: {payload['imported']}",
        f"- Duplicate imported: {payload['duplicate_imported']}",
        f"- Converted: {payload['converted']}",
        f"- Converter: {payload['converter']}",
        f"- No convert: {payload['no_convert']}",
        "",
        "## Final Status",
        "",
        "```json",
        json.dumps(payload["final_status"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Artifact Counts",
        "",
        "```json",
        json.dumps(payload["artifact_counts"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Strict Doctor",
        "",
        "```json",
        json.dumps(payload["strict_doctor"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _build_converter(
    converter_name: str,
    *,
    library_dir: Path,
    local_backend: str | None,
    batch_size: int,
    max_pages_per_part: int | None,
    fixture_output: Path | None,
):
    if converter_name == "local-fixture":
        if fixture_output is None:
            raise ValueError("local-fixture validation requires fixture_output")
        return LocalFixtureConverter(fixture_output)
    if converter_name == "mineru-api":
        from paper_cli.converters.mineru import MinerUConverter

        return MinerUConverter()
    if converter_name == "mineru-api-batch":
        from paper_cli.converters.mineru_api_batch import MinerUApiBatchConverter

        return MinerUApiBatchConverter(
            batch_size=batch_size,
            max_pages_per_part=max_pages_per_part,
        )
    if converter_name == "mineru-local":
        from paper_cli.converters.mineru_local import MinerULocalConverter

        return MinerULocalConverter(
            executable=None,
            local_backend=local_backend,
            config=load_config(library_dir),
        )
    raise ValueError(f"Unknown converter: {converter_name}")


def _prepare_output_path(path: Path, *, replace: bool) -> None:
    if not path.exists():
        return
    if not replace:
        raise FileExistsError(f"Refusing to overwrite existing validation path: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _pending_count(library_dir: Path) -> int:
    count = 0
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            count += 1
    return count


def _count(root: Path, name: str) -> int:
    return len(list(root.rglob(name)))
