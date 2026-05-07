from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pathlib import Path


DB_SDK_MAP = {
    "milvus": "pymilvus",
    "qdrant": "qdrant-client",
    "weaviate": "weaviate-client",
    "pgvector": "asyncpg+pgvector",
}


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    pro_model: str = "deepseek-v4-pro"
    flash_model: str = "deepseek-v4-flash"
    api_key: str = ""
    max_retries: int = 3
    timeout: int = 120
    thinking_mode: bool = True
    reasoning_effort: str = "high"


class DBInstanceConfig(BaseModel):
    type: Literal["milvus", "qdrant", "weaviate", "pgvector"]
    host: str = "localhost"
    port: int = 19530
    alias: str = ""
    extra: dict = Field(default_factory=dict)

class MultiDBConfig(BaseModel):
    instances: list[DBInstanceConfig] = []
    default: str = "milvus"
    target_version: str = "2.6.12"


class HarnessConfig(BaseModel):
    max_rounds: int = 4
    max_token_budget: int = 2000000
    max_consecutive_failures: int = 5
    safety_level: str = "cautious"
    mre_clean_env: bool = True
    mre_timeout: int = 60


class DocsConfig(BaseModel):
    source: str = "local_jsonl"
    local_jsonl_path: str = ""
    crawl_max_depth: int = 3
    crawl_max_pages: int = 100


class SourceAnalysisConfig(BaseModel):
    repo_url: str = ""
    branch: str = "master"
    target_dir: str = ".trae/source"
    focus_dirs: list[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    issues_dir: str = ".trae/issues"
    state_dir: str = ".trae/runs"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    telemetry_path: str = ".trae/runs/telemetry.jsonl"


class _EnvSettings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class AppConfig(BaseModel):
    model_config = {"extra": "ignore"}

    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: MultiDBConfig = Field(default_factory=MultiDBConfig)
    harness: HarnessConfig = Field(default_factory=HarnessConfig)
    docs: DocsConfig = Field(default_factory=DocsConfig)
    source_analysis: SourceAnalysisConfig = Field(default_factory=SourceAnalysisConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        p = Path(path)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = cls(**data)
        config._resolve_env()
        return config

    def _resolve_env(self) -> None:
        env = _EnvSettings()
        if env.deepseek_api_key and not self.llm.api_key:
            self.llm.api_key = env.deepseek_api_key
        if env.deepseek_base_url and self.llm.base_url == "https://api.deepseek.com":
            self.llm.base_url = env.deepseek_base_url
        if env.milvus_host != "localhost" or env.milvus_port != 19530:
            for inst in self.database.instances:
                if inst.type == "milvus":
                    if env.milvus_host != "localhost":
                        inst.host = env.milvus_host
                    if env.milvus_port != 19530:
                        inst.port = env.milvus_port
                    break

    def get_pro_model_id(self) -> str:
        return self.llm.pro_model

    def get_flash_model_id(self) -> str:
        return self.llm.flash_model
