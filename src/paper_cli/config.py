from pathlib import Path
from typing import Any

import yaml

DEFAULT_NAMING_TEMPLATE = """{{if language == "zh"}}
{{ firstCreator suffix=" - " }}
{{elseif language == "zh-CN"}}
{{ firstCreator suffix=" - " }}
{{else}}
{{creators max="1" suffix=" et al. - "}}
{{ endif }}
{{ year suffix=" - " }}
{{ title truncate="100" }}"""


def default_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "naming": {
            "template": DEFAULT_NAMING_TEMPLATE,
            "duplicate_strategy": "append-counter",
            "sanitize": {
                "max_length": 180,
                "ascii_slug": False,
            },
        },
        "metadata": {
            "default_mode": "fast",
            "language_detection": "auto",
        },
        "mineru": {
            "executable": "mineru",
            "local_backend": None,
            "local_jobs": "auto",
            "max_wait_seconds": None,
        },
        "output": {
            "json": False,
        },
    }


def write_default_config(library_dir: Path) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)
    config_path = library_dir / "paper-cli.yaml"
    if not config_path.exists():
        config_path.write_text(
            yaml.safe_dump(default_config(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def load_config(library_dir: Path) -> dict[str, Any]:
    config_path = library_dir / "paper-cli.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config file: {config_path}")
    return _deep_merge(default_config(), data)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def init_library(library_dir: Path) -> None:
    write_default_config(library_dir)
    (library_dir / "collections").mkdir(parents=True, exist_ok=True)
    (library_dir / "inbox").mkdir(parents=True, exist_ok=True)
    indexes_dir = library_dir / "indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)
    for index_name in ("papers.jsonl", "jobs.jsonl"):
        index_path = indexes_dir / index_name
        if not index_path.exists():
            index_path.write_text("", encoding="utf-8")
