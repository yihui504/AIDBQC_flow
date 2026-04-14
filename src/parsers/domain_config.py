from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


@dataclass
class DomainConfig:
    """
    领域爬取配置（轻量实现，兼容旧接口）。
    """

    allowed_domains: Set[str] = field(default_factory=set)
    blocked_domains: Set[str] = field(default_factory=set)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 15.0
    max_retries: int = 2
    user_agent: str = "AI-DB-QC-Bot/1.0"

    @classmethod
    def from_url(cls, url: str) -> "DomainConfig":
        host = (urlparse(url).hostname or "").lower()
        return cls(allowed_domains={host} if host else set())

    def is_domain_allowed(self, url_or_domain: str) -> bool:
        target = self._normalize_domain(url_or_domain)
        if not target:
            return False
        if target in self.blocked_domains:
            return False
        if not self.allowed_domains:
            return True
        return target in self.allowed_domains

    def merge_allowed(self, domains: Optional[List[str]]) -> None:
        if not domains:
            return
        for d in domains:
            normalized = self._normalize_domain(d)
            if normalized:
                self.allowed_domains.add(normalized)

    @staticmethod
    def _normalize_domain(url_or_domain: str) -> str:
        candidate = (url_or_domain or "").strip().lower()
        if "://" in candidate:
            candidate = (urlparse(candidate).hostname or "").lower()
        if candidate.startswith("www."):
            candidate = candidate[4:]
        return candidate
