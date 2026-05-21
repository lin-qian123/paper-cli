from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import requests

from paper_cli.config import load_config


class AIProvider(Protocol):
    name: str
    model: str

    def complete_json(self, messages: list[dict[str, str]], *, schema_name: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0
    timeout_seconds: int = 60


class ProviderConfigError(ValueError):
    pass


def _env_or_config(env_name: str, config: dict[str, Any], key: str, default: Any = None) -> Any:
    value = os.environ.get(env_name)
    if value not in (None, ""):
        return value
    return config.get(key, default)


def load_provider_config(library_dir: Path) -> ProviderConfig:
    config = load_config(library_dir).get("ai", {})
    if config and config.get("provider", "openai-compatible") != "openai-compatible":
        raise ProviderConfigError("Only openai-compatible AI provider is supported")

    api_key_env = str(config.get("api_key_env") or "PAPER_AI_API_KEY")
    api_key = os.environ.get(api_key_env) or os.environ.get("PAPER_AI_API_KEY") or ""
    base_url = _env_or_config(
        "PAPER_AI_BASE_URL",
        config,
        "base_url",
        "https://api.openai.com/v1",
    )
    model = _env_or_config("PAPER_AI_MODEL", config, "model", "")
    temperature = float(_env_or_config("PAPER_AI_TEMPERATURE", config, "temperature", 0))
    timeout_seconds = int(
        _env_or_config("PAPER_AI_TIMEOUT_SECONDS", config, "timeout_seconds", 60)
    )

    missing = []
    if not api_key:
        missing.append(api_key_env)
    if not model:
        missing.append("PAPER_AI_MODEL or ai.model")
    if missing:
        raise ProviderConfigError("Missing AI provider configuration: " + ", ".join(missing))

    return ProviderConfig(
        base_url=str(base_url).rstrip("/"),
        api_key=api_key,
        model=str(model),
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.model = config.model

    def complete_json(self, messages: list[dict[str, str]], *, schema_name: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }
        response = requests.post(
            f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"AI response for {schema_name} did not contain message content") from exc
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"AI response for {schema_name} was not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"AI response for {schema_name} must be a JSON object")
        return parsed
