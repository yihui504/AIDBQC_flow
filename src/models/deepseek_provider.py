from __future__ import annotations

from pydantic_ai import ModelSettings

from src.config import AppConfig


def build_model_settings(config: AppConfig) -> ModelSettings:
    settings: ModelSettings = {"timeout": config.llm.timeout}
    if config.llm.thinking_mode:
        settings["thinking"] = config.llm.reasoning_effort
    return settings
