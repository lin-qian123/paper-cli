import argparse
import json
from pathlib import Path

from . import __version__
from .ai.extract_summary import (
    DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
    DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
    DEFAULT_EXTRACT_SUMMARY_RETRIES,
    DEFAULT_EXTRACT_SUMMARY_WORKERS,
)
from .config import init_library, load_config
from .convert import convert_pending
from .converters.local_zip import LocalFixtureConverter
from .converters.mineru_jobs import resolve_local_jobs
from .doctor import library_status, run_doctor
from .importer import import_path
from .indexes import find_paper_dirs
from .models import read_paper


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-cli")
    parser.add_argument("--library", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize a paper-cli library")
    init_parser.add_argument("library_dir")
    add_json_flag(init_parser)

    import_parser = subparsers.add_parser("import", help="import local PDFs")
    import_parser.add_argument("input_path")
    destination = import_parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--collection")
    destination.add_argument("--inbox", action="store_true")
    add_json_flag(import_parser)

    convert_parser = subparsers.add_parser("convert", help="convert pending papers")
    convert_parser.add_argument("--pending", action="store_true")
    convert_parser.add_argument(
        "--converter",
        choices=("mineru-api", "mineru-api-batch", "mineru-local", "local-fixture"),
        default=None,
    )
    convert_parser.add_argument("--batch-size", type=int, default=20)
    convert_parser.add_argument("--jobs", type=int, default=None)
    convert_parser.add_argument("--local-backend")
    convert_parser.add_argument("--fixture-output")
    add_json_flag(convert_parser)

    list_parser = subparsers.add_parser("list", help="list papers")
    add_json_flag(list_parser)
    status_parser = subparsers.add_parser("status", help="show library status")
    add_json_flag(status_parser)
    doctor_parser = subparsers.add_parser("doctor", help="validate library")
    doctor_parser.add_argument("--strict", action="store_true")
    add_json_flag(doctor_parser)
    repair_parser = subparsers.add_parser("repair", help="repair converted bundles with AI")
    repair_parser.add_argument(
        "--target",
        choices=("metadata", "markdown", "all"),
        default="all",
    )
    repair_parser.add_argument("--dry-run", action="store_true")
    add_json_flag(repair_parser)
    extract_parser = subparsers.add_parser("extract", help="extract structured paper information")
    extract_subparsers = extract_parser.add_subparsers(dest="extract_command")
    summary_parser = extract_subparsers.add_parser("summary", help="extract AI article skeletons")
    summary_parser.add_argument("--paper")
    summary_parser.add_argument("--collection")
    summary_parser.add_argument("--limit", type=int)
    summary_parser.add_argument("--workers", type=int, default=DEFAULT_EXTRACT_SUMMARY_WORKERS)
    summary_parser.add_argument(
        "--paper-workers",
        type=int,
        default=DEFAULT_EXTRACT_SUMMARY_PAPER_WORKERS,
    )
    summary_parser.add_argument(
        "--max-requests",
        type=int,
        default=DEFAULT_EXTRACT_SUMMARY_MAX_REQUESTS,
    )
    summary_parser.add_argument("--retries", type=int, default=DEFAULT_EXTRACT_SUMMARY_RETRIES)
    summary_parser.add_argument("--force", action="store_true")
    summary_parser.add_argument("--dry-run", action="store_true")
    add_json_flag(summary_parser)

    validate_parser = subparsers.add_parser("validate", help="run local validation workflows")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    qed_parser = validate_subparsers.add_parser("qed", help="run QED corpus validation")
    qed_parser.add_argument("--source", required=True)
    qed_parser.add_argument("--library-root", required=True)
    qed_parser.add_argument("--count", type=int, default=30)
    qed_parser.add_argument("--seed", type=int, default=20260525)
    qed_parser.add_argument("--name")
    qed_parser.add_argument(
        "--converter",
        choices=("mineru-api", "mineru-api-batch", "mineru-local", "local-fixture"),
        default="mineru-local",
    )
    qed_parser.add_argument("--local-backend")
    qed_parser.add_argument("--batch-size", type=int, default=1)
    qed_parser.add_argument("--jobs", type=int)
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
        _emit({"ok": True, "imported": [str(path) for path in imported]}, args.json)
        return 0
    if args.command == "convert":
        if not args.pending:
            parser.error("convert currently requires --pending")
        converter_name = args.converter or ("local-fixture" if args.fixture_output else "mineru-api")
        if converter_name == "local-fixture":
            if not args.fixture_output:
                parser.error("--converter local-fixture requires --fixture-output")
            converter = LocalFixtureConverter(Path(args.fixture_output))
        elif converter_name == "mineru-api":
            from .converters.mineru import MinerUConverter

            converter = MinerUConverter()
        elif converter_name == "mineru-api-batch":
            from .converters.mineru_api_batch import MinerUApiBatchConverter

            converter = MinerUApiBatchConverter(batch_size=args.batch_size)
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
        _emit({"ok": True, "converted": [str(path) for path in converted]}, args.json)
        return 0
    if args.command == "list":
        rows = []
        for bundle_dir in find_paper_dirs(Path(args.library)):
            record = read_paper(bundle_dir)
            rows.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "collection": record.collection,
                    "status": record.status,
                    "path": str(bundle_dir),
                }
            )
        if args.json:
            _emit({"papers": rows}, True)
        else:
            for row in rows:
                print(f"{row['id'][:18]}  {row['status'].get('conversion')}  {row['name']}")
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
            _emit({"ok": not issues, "issues": [issue.to_dict() for issue in issues]}, True)
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
        )
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
    if args.command == "extract":
        if args.extract_command != "summary":
            parser.error("extract currently requires a subcommand such as summary")
        from .ai.extract_summary import extract_summary_library

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
