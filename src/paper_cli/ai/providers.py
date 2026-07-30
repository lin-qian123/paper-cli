from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, replace
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
    timeout_seconds: float = 60


class ProviderConfigError(ValueError):
    pass


class ProviderRequestTimeout(TimeoutError):
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
    timeout_seconds = float(
        _env_or_config("PAPER_AI_TIMEOUT_SECONDS", config, "timeout_seconds", 60)
    )
    if timeout_seconds <= 0:
        raise ProviderConfigError("AI request timeout_seconds must be greater than zero")

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

    def with_timeout(self, timeout_seconds: float) -> "OpenAICompatibleProvider":
        if timeout_seconds <= 0:
            raise ValueError("AI request timeout must be greater than zero")
        return OpenAICompatibleProvider(
            replace(self.config, timeout_seconds=max(0.001, timeout_seconds))
        )

    def _run_with_wall_clock(self, call, *, schema_name: str):
        result: dict[str, Any] = {}
        done = threading.Event()

        def run() -> None:
            try:
                result["value"] = call()
            except BaseException as exc:
                result["error"] = exc
            finally:
                done.set()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        if not done.wait(timeout=self.config.timeout_seconds):
            raise ProviderRequestTimeout(
                f"AI request for {schema_name} exceeded the {self.config.timeout_seconds}s wall-clock limit"
            )
        if "error" in result:
            raise result["error"]
        return result["value"]

    def complete_json(self, messages: list[dict[str, str]], *, schema_name: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }
        response = self._run_with_wall_clock(
            lambda: requests.post(
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.config.timeout_seconds,
            ),
            schema_name=schema_name,
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


def check_provider_health(config: ProviderConfig) -> dict[str, Any]:
    """Perform an authenticated, content-free OpenAI-compatible health check."""

    provider = OpenAICompatibleProvider(config)
    response = provider._run_with_wall_clock(
        lambda: requests.get(
            f"{config.base_url}/models",
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout_seconds,
        ),
        schema_name="provider-health-check",
    )
    response.raise_for_status()
    return {
        "ok": True,
        "provider": provider.name,
        "base_url": config.base_url,
        "model": config.model,
        "request_timeout_seconds": config.timeout_seconds,
        "check": "GET /models",
    }
