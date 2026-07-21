import argparse
import json
import os
from pathlib import Path

from . import __version__
from .ai.extract_summary import (
    DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
    DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
    DEFAULT_EXTRACT_SUMMARY_RETRIES,
    DEFAULT_EXTRACT_SUMMARY_WORKERS,
)
from .ai.memory_state import mark_bundles_stale
from .config import init_library, load_config
from .convert import convert_pending
from .converters.local_zip import LocalFixtureConverter
from .converters.mineru_jobs import resolve_local_jobs
from .doctor import doctor_diagnostics, library_status, run_doctor
from .importer import import_path
from .indexes import find_paper_dirs
from .models import read_paper
from .papers import inspect_paper, paper_row, resolve_one_paper


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper",
        description="Manage local paper libraries as agent-readable bundles.",
    )
    parser.add_argument("--library", default=".", help="paper library directory (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit stable JSON to stdout")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize a paper library")
    init_parser.add_argument("library_dir", help="directory to create or reuse as a library")
    add_json_flag(init_parser)

    import_parser = subparsers.add_parser("import", help="import local PDFs")
    import_parser.add_argument("input_path", help="PDF file or folder containing PDFs")
    destination = import_parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--collection", help="collection path under collections/")
    destination.add_argument("--inbox", action="store_true", help="import into inbox/")
    add_json_flag(import_parser)

    convert_parser = subparsers.add_parser("convert", help="convert pending papers")
    convert_parser.add_argument("--pending", action="store_true", help="convert pending/failed bundles")
    convert_parser.add_argument(
        "--converter",
        choices=("mineru-api", "mineru-api-batch", "mineru-local", "local-fixture"),
        default=None,
        help="conversion backend (default: mineru-api-batch, or local-fixture with --fixture-output)",
    )
    convert_parser.add_argument("--batch-size", type=int, default=20, help="papers per batch")
    convert_parser.add_argument("--jobs", type=int, default=None, help="backend concurrency override")
    convert_parser.add_argument(
        "--max-pages-per-part",
        type=int,
        default=None,
        help="split long MinerU API PDFs into parts with at most this many pages",
    )
    convert_parser.add_argument("--local-backend", help="MinerU local backend passed as -b")
    convert_parser.add_argument("--fixture-output", help="fixture MinerU output for tests/dry runs")
    convert_parser.add_argument("--dry-run", action="store_true", help="plan conversion without writes")
    add_json_flag(convert_parser)

    list_parser = subparsers.add_parser("list", help="list papers")
    add_json_flag(list_parser)
    resolve_parser = subparsers.add_parser("resolve", help="resolve a paper query to one bundle")
    resolve_parser.add_argument("query", help="paper ID/prefix, name, title, or bundle path")
    add_json_flag(resolve_parser)
    get_parser = subparsers.add_parser("get", help="read one paper metadata record")
    get_parser.add_argument("paper", help="paper ID/prefix, name, title, or bundle path")
    add_json_flag(get_parser)
    inspect_parser = subparsers.add_parser("inspect", help="inspect one paper bundle and artifacts")
    inspect_parser.add_argument("paper", help="paper ID/prefix, name, title, or bundle path")
    add_json_flag(inspect_parser)
    status_parser = subparsers.add_parser("status", help="show library status")
    add_json_flag(status_parser)
    doctor_parser = subparsers.add_parser("doctor", help="validate library and report setup")
    doctor_parser.add_argument("--strict", action="store_true", help="include conversion/job checks")
    add_json_flag(doctor_parser)
    repair_parser = subparsers.add_parser("repair", help="repair converted bundles with AI")
    repair_parser.add_argument(
        "--target",
        choices=("metadata", "markdown", "all"),
        default="all",
    )
    repair_parser.add_argument("--paper", help="limit repair scope by paper id/name/title/path")
    repair_parser.add_argument("--collection", help="limit repair scope by collection path")
    repair_parser.add_argument("--limit", type=int, help="maximum number of bundles to repair")
    repair_parser.add_argument("--dry-run", action="store_true", help="plan repairs without writing files")
    add_json_flag(repair_parser)
    memory_parser = subparsers.add_parser("memory", help="build hierarchical agent memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")
    memory_build_parser = memory_subparsers.add_parser("build", help="build collection and library memory")
    memory_build_parser.add_argument("--collection", help="limit to one collection path")
    memory_build_parser.add_argument("--limit", type=int, help="maximum papers to process")
    memory_build_parser.add_argument("--force", action="store_true", help="regenerate existing outputs")
    memory_build_parser.add_argument("--dry-run", action="store_true", help="plan memory build without writes")
    add_json_flag(memory_build_parser)
    extract_parser = subparsers.add_parser("extract", help="extract structured paper information")
    extract_subparsers = extract_parser.add_subparsers(dest="extract_command")
    summary_parser = extract_subparsers.add_parser("summary", help="extract AI article skeletons")
    summary_parser.add_argument("--paper", help="paper ID/prefix, name, title, or bundle path")
    summary_parser.add_argument("--collection", help="limit to one collection path")
    summary_parser.add_argument("--limit", type=int, help="maximum papers to process")
    summary_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_EXTRACT_SUMMARY_WORKERS,
        help="per-paper block worker count",
    )
    summary_parser.add_argument(
        "--paper-workers",
        type=int,
        default=DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
        help="paper-level worker count",
    )
    summary_parser.add_argument(
        "--max-requests",
        type=int,
        default=DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
        help="global provider request concurrency cap",
    )
    summary_parser.add_argument(
        "--retries", type=int, default=DEFAULT_EXTRACT_SUMMARY_RETRIES, help="provider retries"
    )
    summary_parser.add_argument("--force", action="store_true", help="regenerate existing outputs")
    summary_parser.add_argument("--dry-run", action="store_true", help="plan extraction without writes")
    add_json_flag(summary_parser)

    validate_parser = subparsers.add_parser("validate", help="run local validation workflows")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    qed_parser = validate_subparsers.add_parser("qed", help="run QED corpus validation")
    qed_parser.add_argument("--source", required=True, help="source QED PDF directory")
    qed_parser.add_argument("--library-root", required=True, help="parent directory for test library")
    qed_parser.add_argument("--count", type=int, default=30, help="sample size")
    qed_parser.add_argument("--seed", type=int, default=20260525, help="deterministic sample seed")
    qed_parser.add_argument("--name", help="test library name")
    qed_parser.add_argument(
        "--converter",
        choices=("mineru-api", "mineru-api-batch", "mineru-local", "local-fixture"),
        default="mineru-local",
    )
    qed_parser.add_argument("--local-backend")
    qed_parser.add_argument("--batch-size", type=int, default=1)
    qed_parser.add_argument("--jobs", type=int)
    qed_parser.add_argument("--max-pages-per-part", type=int)
    qed_parser.add_argument("--fixture-output")
    qed_parser.add_argument("--no-convert", action="store_true")
    qed_parser.add_argument("--replace", action="store_true")
    add_json_flag(qed_parser)

    return parser


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"paper-cli {__version__}")
        return 0
    if args.command == "init":
        init_library(Path(args.library_dir))
        _emit({"ok": True, "library": str(Path(args.library_dir))}, args.json)
        return 0
    if args.command == "import":
        imported = import_path(
            Path(args.library),
            Path(args.input_path),
            collection=args.collection,
            inbox=args.inbox,
        )
        mark_bundles_stale(Path(args.library), imported, reason="import")
        _emit({"ok": True, "imported": [str(path) for path in imported]}, args.json)
        return 0
    if args.command == "convert":
        if not args.pending:
            parser.error("convert currently requires --pending")
        converter_name = args.converter or (
            "local-fixture" if args.fixture_output else "mineru-api-batch"
        )
        if args.dry_run:
            payload = _conversion_plan(
                Path(args.library),
                converter_name=converter_name,
                batch_size=args.batch_size,
                cli_jobs=args.jobs,
                local_backend=args.local_backend,
                fixture_output=args.fixture_output,
            )
            if args.json:
                _emit(payload, True)
            else:
                print(f"converter: {payload['converter']}")
                print(f"pending: {payload['pending_count']}")
                print(f"jobs: {payload['jobs']}")
            return 0
        if converter_name == "local-fixture":
            if not args.fixture_output:
                parser.error("--converter local-fixture requires --fixture-output")
            converter = LocalFixtureConverter(Path(args.fixture_output))
        elif converter_name == "mineru-api":
            from .converters.mineru import MinerUConverter

            converter = MinerUConverter()
        elif converter_name == "mineru-api-batch":
            from .converters.mineru_api_batch import MinerUApiBatchConverter

            converter = MinerUApiBatchConverter(
                batch_size=args.batch_size,
                max_pages_per_part=args.max_pages_per_part,
            )
        else:
            from .converters.mineru_local import MinerULocalConverter

            config = load_config(Path(args.library))
            converter = MinerULocalConverter(
                executable=None,
                local_backend=args.local_backend,
                config=config,
            )
        if converter_name == "mineru-local":
            pending_count = _pending_count(Path(args.library))
            jobs = resolve_local_jobs(
                load_config(Path(args.library)),
                cli_jobs=args.jobs,
                pending_count=pending_count,
            )
        else:
            jobs = args.jobs if args.jobs is not None else 4
        converted = convert_pending(
            Path(args.library),
            converter,
            batch_size=args.batch_size,
            jobs=jobs,
        )
        mark_bundles_stale(Path(args.library), converted, reason="convert")
        _emit({"ok": True, "converted": [str(path) for path in converted]}, args.json)
        return 0
    if args.command == "list":
        rows = []
        for bundle_dir in find_paper_dirs(Path(args.library)):
            rows.append(paper_row(Path(args.library), bundle_dir))
        if args.json:
            _emit({"papers": rows}, True)
        else:
            for row in rows:
                print(f"{row['id'][:18]}  {row['status'].get('conversion')}  {row['name']}")
        return 0
    if args.command == "resolve":
        match, matches = resolve_one_paper(Path(args.library), args.query)
        if match is None:
            payload = {
                "ok": False,
                "query": args.query,
                "error": "not found" if not matches else "ambiguous",
                "matches": [
                    {**paper_row(Path(args.library), item.bundle_dir, item.record), "reasons": item.reasons}
                    for item in matches
                ],
            }
            _emit(payload, args.json)
            if not args.json:
                print(f"{payload['error']}: {args.query}")
            return 1
        payload = {
            "ok": True,
            "query": args.query,
            "paper": paper_row(Path(args.library), match.bundle_dir, match.record),
            "reasons": match.reasons,
        }
        if args.json:
            _emit(payload, True)
        else:
            row = payload["paper"]
            print(f"{row['id']}  {row['relative_path']}")
        return 0
    if args.command == "get":
        match, matches = resolve_one_paper(Path(args.library), args.paper)
        if match is None:
            return _emit_resolution_error(args.paper, matches, args.json, Path(args.library))
        payload = {
            "ok": True,
            "paper": {
                **paper_row(Path(args.library), match.bundle_dir, match.record),
                "metadata": match.record.metadata,
                "metadata_sources": match.record.metadata_sources,
                "metadata_confidence": match.record.metadata_confidence,
                "source": match.record.source,
                "naming": match.record.naming,
                "name_locked": match.record.name_locked,
                "previous_names": match.record.previous_names,
                "schema_version": match.record.schema_version,
            },
        }
        if args.json:
            _emit(payload, True)
        else:
            row = payload["paper"]
            print(f"{row['id']}  {row['name']}")
        return 0
    if args.command == "inspect":
        match, matches = resolve_one_paper(Path(args.library), args.paper)
        if match is None:
            return _emit_resolution_error(args.paper, matches, args.json, Path(args.library))
        payload = {"ok": True, **inspect_paper(Path(args.library), match.bundle_dir, match.record)}
        if args.json:
            _emit(payload, True)
        else:
            print(f"{payload['paper']['id']}  {payload['paper']['relative_path']}")
            for key, artifact in payload["artifacts"].items():
                print(f"{key}: {artifact['exists']}")
        return 0
    if args.command == "status":
        status = library_status(Path(args.library))
        if args.json:
            _emit(status, True)
        else:
            for key, value in status.items():
                print(f"{key}: {value}")
        return 0
    if args.command == "doctor":
        issues = run_doctor(Path(args.library), strict=args.strict)
        if args.json:
            _emit(
                {
                    "ok": not issues,
                    "issues": [issue.to_dict() for issue in issues],
                    "diagnostics": doctor_diagnostics(Path(args.library), strict=args.strict),
                },
                True,
            )
        else:
            for issue in issues:
                print(f"{issue.code}: {issue.path} - {issue.message}")
        return 1 if issues else 0
    if args.command == "repair":
        from .ai.providers import (
            OpenAICompatibleProvider,
            ProviderConfigError,
            load_provider_config,
        )
        from .ai.repair import repair_library

        try:
            provider = OpenAICompatibleProvider(load_provider_config(Path(args.library)))
        except ProviderConfigError as exc:
            payload = {"ok": False, "error": str(exc), "repaired": [], "failed": []}
            if args.json:
                _emit(payload, True)
            else:
                print(str(exc))
            return 1
        payload = repair_library(
            Path(args.library),
            provider,
            target=args.target,
            dry_run=args.dry_run,
            paper=args.paper,
            collection=args.collection,
            limit=args.limit,
        )
        if not args.dry_run:
            changed_paths = [
                Path(row["path"])
                for row in payload["repaired"]
                if row.get("metadata_changed") or row.get("markdown_changed")
            ]
            mark_bundles_stale(Path(args.library), changed_paths, reason="repair")
        if args.json:
            _emit(payload, True)
        else:
            for row in payload["repaired"]:
                print(
                    f"{row['path']} metadata={row['metadata_changed']} "
                    f"markdown={row['markdown_changed']}"
                )
            for row in payload["failed"]:
                print(f"failed: {row['path']} - {row['error']}")
        return 0 if payload["ok"] else 1
    if args.command == "memory":
        if args.memory_command != "build":
            parser.error("memory currently requires a subcommand such as build")
        from .ai.memory_build import build_memory_library

        provider = None
        if not args.dry_run:
            from .ai.providers import (
                OpenAICompatibleProvider,
                ProviderConfigError,
                load_provider_config,
            )

            try:
                provider = OpenAICompatibleProvider(load_provider_config(Path(args.library)))
            except ProviderConfigError as exc:
                payload = {
                    "ok": False,
                    "error": str(exc),
                    "planned": [],
                    "written": [],
                    "skipped": [],
                    "failed": [],
                    "warnings": [],
                }
                if args.json:
                    _emit(payload, True)
                else:
                    print(str(exc))
                return 1
        payload = build_memory_library(
            Path(args.library),
            provider,
            collection=args.collection,
            limit=args.limit,
            force=args.force,
            dry_run=args.dry_run,
        )
        if args.json:
            _emit(payload, True)
        else:
            for row in payload["planned"]:
                print(f"planned: {row['kind']} {row['path']}")
            for row in payload["written"]:
                print(f"written: {row['kind']} {row['path']}")
            for row in payload["skipped"]:
                print(f"skipped: {row['kind']} {row['path']} - {row['reason']}")
            for row in payload["failed"]:
                print(f"failed: {row['kind']} {row['path']} - {row['error']}")
        return 0 if payload["ok"] else 1
    if args.command == "extract":
        if args.extract_command != "summary":
            parser.error("extract currently requires a subcommand such as summary")
        from .ai.extract_summary import extract_summary_library
        from .ai.memory_build import refresh_memory_for_bundles

        provider = None
        if not args.dry_run:
            from .ai.providers import (
                OpenAICompatibleProvider,
                ProviderConfigError,
                load_provider_config,
            )

            try:
                provider = OpenAICompatibleProvider(load_provider_config(Path(args.library)))
            except ProviderConfigError as exc:
                payload = {"ok": False, "error": str(exc), "extracted": [], "failed": []}
                if args.json:
                    _emit(payload, True)
                else:
                    print(str(exc))
                return 1
        payload = extract_summary_library(
            Path(args.library),
            provider,
            paper=args.paper,
            collection=args.collection,
            limit=args.limit,
            workers=args.workers,
            paper_workers=args.paper_workers,
            max_requests=args.max_requests,
            retries=args.retries,
            force=args.force,
            dry_run=args.dry_run,
        )
        if not args.dry_run and provider is not None:
            extracted_paths = [Path(row["path"]) for row in payload["extracted"]]
            if extracted_paths:
                payload["memory_refresh"] = refresh_memory_for_bundles(
                    Path(args.library),
                    provider,
                    extracted_paths,
                )
                if not payload["memory_refresh"]["ok"]:
                    payload.setdefault("warnings", []).append(
                        "memory refresh failed after extract summary; summaries were still written"
                    )
        if args.json:
            _emit(payload, True)
        else:
            for row in payload["planned"]:
                print(
                    f"planned: {row['path']} blocks={row['summarizable_blocks']} "
                    f"batches={row['batches']}"
                )
            for row in payload["extracted"]:
                print(f"extracted: {row['path']} blocks={row['blocks_summarized']}")
            for row in payload["skipped"]:
                print(f"skipped: {row['path']} - {row['reason']}")
            for row in payload["failed"]:
                print(f"failed: {row['path']} - {row['error']}")
            if payload.get("memory_refresh"):
                refresh = payload["memory_refresh"]
                print(
                    f"memory-refresh: written={len(refresh['written'])} failed={len(refresh['failed'])}"
                )
        return 0 if payload["ok"] else 1
    if args.command == "validate":
        if args.validate_command != "qed":
            parser.error("validate currently requires a subcommand such as qed")
        from .validation.qed import run_qed_validation

        payload = run_qed_validation(
            source=Path(args.source),
            library_root=Path(args.library_root),
            count=args.count,
            seed=args.seed,
            name=args.name,
            converter_name=args.converter,
            local_backend=args.local_backend,
            batch_size=args.batch_size,
            jobs=args.jobs,
            max_pages_per_part=args.max_pages_per_part,
            fixture_output=Path(args.fixture_output) if args.fixture_output else None,
            no_convert=args.no_convert,
            replace=args.replace,
        )
        if args.json:
            _emit(payload, True)
        else:
            print(f"library: {payload['library']}")
            print(f"report: {payload['report']}")
            print(f"ok: {payload['ok']}")
        return 0 if payload["ok"] else 1
    return 0


def _pending_count(library_dir: Path) -> int:
    count = 0
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            count += 1
    return count


def _pending_rows(library_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for bundle_dir in find_paper_dirs(library_dir):
        record = read_paper(bundle_dir)
        if record.status.get("conversion") != "done":
            rows.append(paper_row(library_dir, bundle_dir, record))
    return rows


def _conversion_plan(
    library_dir: Path,
    *,
    converter_name: str,
    batch_size: int,
    cli_jobs: int | None,
    local_backend: str | None,
    fixture_output: str | None,
) -> dict:
    pending = _pending_rows(library_dir)
    diagnostics: dict = {}
    if converter_name == "mineru-local":
        try:
            config = load_config(library_dir)
            jobs = resolve_local_jobs(config, cli_jobs=cli_jobs, pending_count=len(pending))
            local_backend = local_backend or config.get("mineru", {}).get("local_backend")
            diagnostics["configured_executable"] = config.get("mineru", {}).get("executable")
        except Exception as exc:
            jobs = cli_jobs if cli_jobs is not None else 1
            diagnostics["config_error"] = str(exc)
    else:
        jobs = cli_jobs if cli_jobs is not None else 4
    if converter_name in {"mineru-api", "mineru-api-batch"}:
        diagnostics["mineru_api_key_available"] = bool(os.environ.get("MINERU_API_KEY"))
    if converter_name == "local-fixture":
        diagnostics["fixture_output"] = fixture_output
        diagnostics["fixture_output_exists"] = bool(fixture_output and Path(fixture_output).exists())
    return {
        "ok": True,
        "dry_run": True,
        "converter": converter_name,
        "batch_size": batch_size,
        "jobs": jobs,
        "local_backend": local_backend,
        "pending_count": len(pending),
        "pending": pending,
        "diagnostics": diagnostics,
        "planned_writes": [
            "paper.md",
            "images/",
            "raw/mineru/",
            "conversion.json",
            "indexes/papers.jsonl",
            "indexes/jobs.jsonl",
        ],
    }


def _emit_resolution_error(query: str, matches: list, as_json: bool, library_dir: Path) -> int:
    payload = {
        "ok": False,
        "query": query,
        "error": "not found" if not matches else "ambiguous",
        "matches": [
            {**paper_row(library_dir, item.bundle_dir, item.record), "reasons": item.reasons}
            for item in matches
        ],
    }
    if as_json:
        _emit(payload, True)
    else:
        print(f"{payload['error']}: {query}")
        for match in payload["matches"]:
            print(f"{match['id']}  {match['relative_path']}")
    return 1
