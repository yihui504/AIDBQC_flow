from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from src.config import AppConfig

logger = logging.getLogger(__name__)


class DocSearchResult(BaseModel):
    query: str
    results: list[dict] = []
    total: int = 0
    source: str = "local"


class DocAnalyzer:
    def __init__(self, config: AppConfig):
        self.config = config
        self._docs_cache: Optional[list[dict]] = None

    def _load_local_docs(self) -> list[dict]:
        if self._docs_cache is not None:
            return self._docs_cache

        docs_path = Path(self.config.docs.local_jsonl_path)
        if not docs_path.exists():
            logger.warning(f"Local docs not found: {docs_path}")
            return []

        docs = []
        with open(docs_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                        docs.append(doc)
                    except json.JSONDecodeError:
                        continue

        self._docs_cache = docs
        logger.info(f"Loaded {len(docs)} documents from {docs_path}")
        return docs

    def search_docs(self, query: str, max_results: int = 10) -> DocSearchResult:
        docs = self._load_local_docs()
        if not docs:
            return DocSearchResult(query=query, source="local")

        query_lower = query.lower()
        query_terms = query_lower.split()

        scored = []
        for doc in docs:
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            url = doc.get("url", "")

            score = 0.0
            for term in query_terms:
                if term in title:
                    score += 3.0
                if term in content:
                    score += 1.0
                    idx = content.find(term)
                    proximity_bonus = max(0, 1.0 - idx / max(len(content), 1))
                    score += proximity_bonus * 0.5

            if score > 0:
                scored.append({
                    "title": doc.get("title", ""),
                    "url": url,
                    "content_snippet": doc.get("content", "")[:500],
                    "score": round(score, 2),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:max_results]

        return DocSearchResult(query=query, results=top, total=len(scored), source="local")

    def get_doc_by_url(self, url: str) -> Optional[dict]:
        docs = self._load_local_docs()
        for doc in docs:
            if doc.get("url", "") == url:
                return doc
        return None

    def validate_reference(self, url: str, claim: str) -> dict:
        doc = self.get_doc_by_url(url)
        if doc is None:
            return {"valid": False, "reason": "URL not found in document cache", "url": url}

        content = doc.get("content", "").lower()
        claim_terms = claim.lower().split()
        matched = sum(1 for term in claim_terms if term in content)
        relevance = matched / max(len(claim_terms), 1)

        return {
            "valid": relevance > 0.3,
            "relevance_score": round(relevance, 2),
            "url": url,
            "title": doc.get("title", ""),
            "matched_terms": matched,
            "total_terms": len(claim_terms),
        }

    def extract_api_names(self) -> list[str]:
        docs = self._load_local_docs()
        api_names = set()
        for doc in docs:
            content = doc.get("content", "")
            title = doc.get("title", "")
            if "api" in title.lower() or "method" in title.lower():
                api_names.add(title.strip())
        return sorted(api_names)
