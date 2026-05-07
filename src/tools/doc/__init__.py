from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
from pydantic_ai import RunContext

from src.config import AppConfig
from src.models.state import FocusMode, UnifiedState, tool_meta

logger = logging.getLogger(__name__)

_config: AppConfig | None = None
_docs_cache: list[dict] | None = None
_docs_cache_path: str | None = None
_http_client: httpx.AsyncClient | None = None


def set_config(config: AppConfig) -> None:
    global _config, _docs_cache, _docs_cache_path, _http_client
    _config = config
    _docs_cache = None
    _docs_cache_path = None
    if _http_client is not None and not _http_client.is_closed:
        old_client = _http_client
        _http_client = None
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.create_task(old_client.aclose())
        except RuntimeError:
            pass


async def close() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def _get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_yaml("config.yaml")
    return _config


def _load_docs(jsonl_path: Path) -> list[dict]:
    global _docs_cache, _docs_cache_path
    path_str = str(jsonl_path)
    if _docs_cache is not None and _docs_cache_path == path_str:
        return _docs_cache

    docs = []
    if jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        docs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    _docs_cache = docs
    _docs_cache_path = path_str
    return docs


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="read", compress="summary")
async def doc_search(
    ctx: RunContext[UnifiedState],
    query: str,
    top_k: int = 5,
) -> str:
    config = _get_config()
    jsonl_path = Path(config.docs.local_jsonl_path)
    if not jsonl_path.exists():
        return json.dumps({"success": False, "results": [], "total": 0, "error": f"JSONL file not found: {jsonl_path}"})

    docs = _load_docs(jsonl_path)

    query_lower = query.lower()
    terms = query_lower.split()

    scored = []
    for doc in docs:
        content = doc.get("content", "").lower()
        title = doc.get("title", "").lower()
        score = 0.0
        for term in terms:
            if term in title:
                score += 3.0
            if term in content:
                score += 1.0
        if score > 0:
            scored.append({
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "snippet": doc.get("content", "")[:500],
                "score": round(score, 2),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]
    for r in top:
        r.pop("score", None)

    return json.dumps({"success": True, "results": top, "total": len(scored)})


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING, FocusMode.VERIFICATION], permission="read", compress="minimal")
async def doc_validate_reference(
    ctx: RunContext[UnifiedState],
    url: str,
) -> str:
    global _http_client
    try:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(timeout=10, follow_redirects=True)
        resp = await _http_client.head(url)
        return json.dumps({"success": True, "valid": 200 <= resp.status_code < 400, "status_code": resp.status_code})
    except Exception as e:
        return json.dumps({"success": True, "valid": False, "status_code": 0, "error": str(e)})
