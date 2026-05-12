import argparse
import json
from pathlib import Path

from . import __version__
from .config import init_library
from .importer import import_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-cli")
    parser.add_argument("--library", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize a paper-cli library")
    init_parser.add_argument("library_dir")

    import_parser = subparsers.add_parser("import", help="import local PDFs")
    import_parser.add_argument("input_path")
    destination = import_parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--collection")
    destination.add_argument("--inbox", action="store_true")

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
    return 0
