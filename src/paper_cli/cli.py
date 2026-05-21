import argparse
import json
from pathlib import Path

from . import __version__
from .config import init_library
from .convert import convert_pending
from .converters.local_zip import LocalFixtureConverter
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
    convert_parser.add_argument("--fixture-output")
    add_json_flag(convert_parser)

    list_parser = subparsers.add_parser("list", help="list papers")
    add_json_flag(list_parser)
    status_parser = subparsers.add_parser("status", help="show library status")
    add_json_flag(status_parser)
    doctor_parser = subparsers.add_parser("doctor", help="validate library")
    add_json_flag(doctor_parser)
    repair_parser = subparsers.add_parser("repair", help="repair converted bundles with AI")
    repair_parser.add_argument(
        "--target",
        choices=("metadata", "markdown", "all"),
        default="all",
    )
    repair_parser.add_argument("--dry-run", action="store_true")
    add_json_flag(repair_parser)

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
        if args.fixture_output:
            converter = LocalFixtureConverter(Path(args.fixture_output))
        else:
            from .converters.mineru import MinerUConverter

            converter = MinerUConverter()
        converted = convert_pending(Path(args.library), converter)
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
        issues = run_doctor(Path(args.library))
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
    return 0
