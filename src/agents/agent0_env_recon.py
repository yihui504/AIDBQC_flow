import os
import subprocess
import yaml
import asyncio
import json
import hashlib
import secrets
import logging
import re
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.agents.agent_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate

from src.state import WorkflowState, DatabaseConfig
from src.config import ConfigLoader
from src.rate_limiter import global_llm_rate_limiter
from src.docs.local_docs_library import LocalDocsLibrary
from langchain_community.callbacks.manager import get_openai_callback
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit
from collections import deque
import time
from types import SimpleNamespace

logger = logging.getLogger(__name__)

class DocumentCache:
    """
    Document cache for avoiding repeated crawling of the same documentation.
    
    Features:
    - Hash-based change detection
    - TTL-based cache expiration
    - Incremental updates
    - Configurable storage location
    """
    
    def __init__(self, cache_path: str = ".trae/cache", ttl_days: int = 7):
        self.cache_path = Path(cache_path)
        self.ttl_days = ttl_days
        self.enabled = False
        self.config = None
        
        self.cache_dir = self.cache_path / "docs"
        self.metadata_file = self.cache_path / "metadata.json"
        
        self._ensure_cache_dirs()
    
    def _ensure_cache_dirs(self):
        """Create cache directories if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.metadata_file.exists():
            self._save_metadata({"version": "1.0", "caches": {}})
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.0", "caches": {}}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save cache metadata."""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()
    
    def _is_cache_expired(self, cache_info: Dict[str, Any]) -> bool:
        """Check if cache has expired based on TTL."""
        if "created_at" not in cache_info:
            return True
        
        try:
            created_at = datetime.fromisoformat(cache_info["created_at"])
            expires_at = created_at + timedelta(days=self.ttl_days)
            return datetime.now() > expires_at
        except (ValueError, KeyError):
            return True
    
    def load_docs(self, project_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Load documents from cache if available and valid.
        
        Args:
            project_name: Name of the project (e.g., "milvus")
            
        Returns:
            Tuple of (docs_content, cache_info) if cache hit, None otherwise
        """
        if not self.enabled:
            logger.debug("[DocumentCache] Cache disabled, skipping load")
            return None
        
        metadata = self._load_metadata()
        
        if project_name not in metadata["caches"]:
            logger.info(f"[DocumentCache] Cache MISS: {project_name} (not found in cache)")
            return None
        
        cache_info = metadata["caches"][project_name]
        
        if self._is_cache_expired(cache_info):
            created_at = cache_info.get("created_at", "unknown")
            logger.info(f"[DocumentCache] Cache MISS: {project_name} (expired, created_at={created_at}, TTL={self.ttl_days} days)")
            return None
        
        cache_file = self.cache_dir / project_name / "docs.json"
        if not cache_file.exists():
            logger.info(f"[DocumentCache] Cache MISS: {project_name} (cache file missing)")
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                docs_content = f.read()
            
            cache_size_kb = len(docs_content) / 1024
            pages_cached = cache_info.get("pages_crawled", 0)
            logger.info(f"[DocumentCache] Cache HIT: {project_name} (size={cache_size_kb:.1f}KB, pages={pages_cached}, TTL={self.ttl_days} days)")
            return docs_content, cache_info
        except Exception as e:
            logger.error(f"[DocumentCache] Error loading cache for {project_name}: {e}")
            return None
    
    def save_docs(self, project_name: str, docs_content: str, crawl_stats: Dict[str, Any]) -> bool:
        """
        Save documents to cache.
        
        Args:
            project_name: Name of the project
            docs_content: Content to cache
            crawl_stats: Crawling statistics
            
        Returns:
            True if save successful, False otherwise
        """
        if not self.enabled:
            logger.debug("[DocumentCache] Cache disabled, skipping save")
            return False
        
        try:
            project_dir = self.cache_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            
            cache_file = project_dir / "docs.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(docs_content)
            
            metadata = self._load_metadata()
            metadata["caches"][project_name] = {
                "created_at": datetime.now().isoformat(),
                "pages_crawled": crawl_stats.get("total_crawled", 0),
                "max_depth": crawl_stats.get("current_depth", 0),
                "duration_seconds": crawl_stats.get("duration_seconds", 0),
                "hash": self._calculate_hash(docs_content)
            }
            self._save_metadata(metadata)
            
            cache_size_kb = len(docs_content) / 1024
            pages_crawled = crawl_stats.get("total_crawled", 0)
            logger.info(f"[DocumentCache] Cache SAVED: {project_name} (size={cache_size_kb:.1f}KB, pages={pages_crawled}, TTL={self.ttl_days} days)")
            return True
        except Exception as e:
            logger.error(f"[DocumentCache] Error saving cache for {project_name}: {e}")
            return False
    
    def clear_cache(self, project_name: str):
        """Clear cache for a specific project."""
        project_dir = self.cache_dir / project_name
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
        
        metadata = self._load_metadata()
        if project_name in metadata["caches"]:
            del metadata["caches"][project_name]
            self._save_metadata(metadata)
        
        logger.info(f"[DocumentCache] Cache CLEARED: {project_name}")
    
    def is_cache_valid(self, project_name: str) -> bool:
        """Check if cache exists and is valid for a project."""
        if not self.enabled:
            return False
        
        metadata = self._load_metadata()
        
        if project_name not in metadata["caches"]:
            return False
        
        cache_info = metadata["caches"][project_name]
        return not self._is_cache_expired(cache_info)
    
    def get_outdated_urls(self, project_name: str, current_urls: List[str]) -> List[str]:
        """
        Get URLs that need to be updated based on hash comparison.
        
        Args:
            project_name: Name of the project
            current_urls: List of current URLs to check
            
        Returns:
            List of URLs that need to be updated
        """
        if not self.enabled:
            return current_urls
        
        metadata = self._load_metadata()
        
        if project_name not in metadata["caches"]:
            return current_urls
        
        cache_info = metadata["caches"][project_name]
        
        cache_file = self.cache_dir / project_name / "docs_index.json"
        if not cache_file.exists():
            return current_urls
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_docs = json.load(f)
            
            cached_urls = {doc["url"]: doc["hash"] for doc in cached_docs}
            outdated_urls = []
            
            for url in current_urls:
                if url not in cached_urls:
                    outdated_urls.append(url)
                else:
                    url_hash = self._calculate_hash(url)
                    if cached_urls[url] != url_hash:
                        outdated_urls.append(url)
            
            logger.info(f"[DocumentCache] Incremental update: {project_name} (outdated={len(outdated_urls)}/{len(current_urls)}, cached={len(cached_urls)})")
            return outdated_urls
        except Exception as e:
            logger.error(f"[DocumentCache] Error checking outdated URLs for {project_name}: {e}")
            return current_urls
    
    def set_config(self, config: ConfigLoader):
        """Set configuration loader and check if cache is enabled."""
        self.config = config
        self.enabled = config.get_bool("cache.enabled", default=False)
        if self.enabled:
            logger.info(f"[DocumentCache] Cache ENABLED (TTL={self.ttl_days} days, path={self.cache_path})")
        else:
            logger.info("[DocumentCache] Cache DISABLED")

class DeepCrawler:
    """
    深度递归爬取器，使用 Crawl4AI 的 BFSDeepCrawlStrategy 实现。
    支持深度控制、URL 去重、域名过滤等功能。
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        page_timeout: int = 30,
        total_timeout: int = 600,
        max_pages: int = 100
    ):
        self.max_depth = max_depth
        self.page_timeout = page_timeout
        self.total_timeout = total_timeout
        self.max_pages = max_pages
        self.visited_urls = set()
        self.crawl_stats = {
            "total_crawled": 0,
            "current_depth": 0,
            "failed_urls": []
        }
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 中提取域名"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _is_valid_link(self, url: str, base_domain: str) -> bool:
        """检查链接是否有效且属于同一域名"""
        if not url:
            return False
        
        url_lower = url.lower()
        static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.pdf', '.zip', '.tar', '.gz']
        if any(url_lower.endswith(ext) for ext in static_extensions):
            return False
        
        if url.startswith('#') or url.startswith('javascript:') or url.startswith('mailto:'):
            return False
        
        excluded_patterns = ['/login', '/register', '/signin', '/signup', '/auth', '/logout', '/api/', '/admin']
        if any(pattern in url_lower for pattern in excluded_patterns):
            return False
        
        link_domain = self._extract_domain(url)
        if link_domain != base_domain:
            return False
        
        return True
    
    def _get_official_docs_url(self, db_name: str) -> Optional[str]:
        """获取官方文档首页 URL"""
        docs_mapping = {
            "milvus": "https://milvus.io/docs/",
            "qdrant": "https://qdrant.tech/documentation/",
            "weaviate": "https://weaviate.io/developers/weaviate",
            "pinecone": "https://docs.pinecone.io/",
            "chroma": "https://docs.trychroma.com/",
            "elasticsearch": "https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html",
            "redis": "https://redis.io/docs/",
            "mongodb": "https://www.mongodb.com/docs/atlas/vector-search/",
            "clickhouse": "https://clickhouse.com/docs/en/"
        }
        return docs_mapping.get(db_name.lower())


    async def deep_crawl(self, start_url: str, db_name: str) -> Tuple[str, Dict[str, Any]]:
        """
        执行深度递归爬取
        
        Args:
            start_url: 起始 URL
            db_name: 数据库名称
            
        Returns:
            Tuple[markdown_content, crawl_stats]
        """
        import tempfile
        import os
        crawl_base_dir = tempfile.mkdtemp(prefix="crawl4ai_")
        user_data_dir = tempfile.mkdtemp(prefix="crawl4ai_browser_")
        
        # 设置环境变量以使用临时目录 (MUST BE SET BEFORE IMPORTING CRAWL4AI)
        os.environ["CRAWL4_AI_BASE_DIRECTORY"] = crawl_base_dir

        try:
            # Lazy import to avoid requiring Playwright/Crawl4AI in local_jsonl mode.
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig  # type: ignore
            from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DomainFilter, FilterChain  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Crawl4AI/Playwright is required for docs crawling but is not available. "
                "Either install the missing dependencies (e.g., playwright) or set "
                "docs.source=local_jsonl to bypass crawling."
            ) from e

        print(f"[DeepCrawler] Starting deep crawl from {start_url} (max_depth={self.max_depth})")
        
        base_domain = self._extract_domain(start_url)
        markdown_results = []
        self.crawl_stats["start_time"] = time.time()
        
        # 临时目录已在 import 前配置
        
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            verbose=False,
            user_data_dir=user_data_dir
        )
        
        domain_filter = DomainFilter(allowed_domains=[base_domain])
        filter_chain = FilterChain([domain_filter])
        
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=self.max_depth,
            filter_chain=filter_chain,
            max_pages=self.max_pages,
            include_external=False
        )
        
        run_config = CrawlerRunConfig(
            cache_mode="BYPASS",
            deep_crawl_strategy=deep_crawl_strategy,
            verbose=False
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                async def crawl_with_timeout():
                    result = await crawler.arun(url=start_url, config=run_config)
                    return result
                
                try:
                    result = await asyncio.wait_for(
                        crawl_with_timeout(),
                        timeout=self.total_timeout
                    )
                except asyncio.TimeoutError:
                    print(f"[DeepCrawler] Total crawl timeout ({self.total_timeout}s) reached")
                    raise
                
                # Crawl4AI v0.7.8+: 当 stream=False (默认) 时，结果直接是 List[CrawlResult]
                # 需要检查 result 是否是列表类型
                if isinstance(result, list):
                    # 深度爬取返回多个结果
                    for page_result in result:
                        if page_result.success:
                            url = page_result.url
                            title = page_result.metadata.get('title', 'No title') if page_result.metadata else 'No title'
                            depth = page_result.metadata.get('depth', 0) if page_result.metadata else 0
                            
                            markdown_results.append(
                                f"Source: {url}\nTitle: {title}\nDepth: {depth}\nContent:\n{page_result.markdown}\n"
                            )
                            self.crawl_stats["total_crawled"] += 1
                            self.visited_urls.add(url)
                            
                            if depth > self.crawl_stats["current_depth"]:
                                self.crawl_stats["current_depth"] = depth
                            
                            print(f"[DeepCrawler] Crawled (depth {depth}): {url}")
                        else:
                            self.crawl_stats["failed_urls"].append({
                                "url": page_result.url,
                                "error": page_result.error_message if hasattr(page_result, 'error_message') else "Unknown error"
                            })
                            print(f"[DeepCrawler] Failed: {page_result.url}")
                elif hasattr(result, 'success'):
                    # 单页面结果
                    if result.success:
                        title = result.metadata.get('title', 'No title') if result.metadata else 'No title'
                        markdown_results.append(
                            f"Source: {start_url}\nTitle: {title}\nDepth: 0\nContent:\n{result.markdown}\n"
                        )
                        self.crawl_stats["total_crawled"] = 1
                        print(f"[DeepCrawler] Single page crawled: {start_url}")
                    else:
                        error_msg = result.error_message if hasattr(result, 'error_message') else "Unknown error"
                        print(f"[DeepCrawler] Failed to crawl start URL: {error_msg}")
                        raise RuntimeError(f"Deep crawl failed: {error_msg}")
                else:
                    print(f"[DeepCrawler] Unexpected result type: {type(result)}")
                    raise RuntimeError(f"Unexpected crawl result type: {type(result)}")
                        
        except Exception as e:
            print(f"[DeepCrawler] Error during deep crawl: {e}")
            raise
        
        self.crawl_stats["end_time"] = time.time()
        self.crawl_stats["duration_seconds"] = self.crawl_stats["end_time"] - self.crawl_stats["start_time"]
        
        print(f"[DeepCrawler] Crawl completed: {self.crawl_stats['total_crawled']} pages in {self.crawl_stats['duration_seconds']:.1f}s")
        
        return "\n".join(markdown_results), self.crawl_stats


class LightweightOfficialDocsFetcher:
    """
    Lightweight fallback fetcher for official docs pages.

    Used when deep crawling fails (e.g. timeout). It fetches a small number of
    official URLs and builds the same docs_context schema expected downstream:
    "Source/Title/Depth/Content".
    """

    def __init__(self, request_timeout: float = 15.0, max_pages: int = 8):
        self.request_timeout = float(request_timeout)
        self.max_pages = int(max_pages)

    @staticmethod
    def _normalize_url(url: str) -> str:
        parts = urlsplit(url)
        # Keep scheme/netloc/path only; strip query+fragment for dedupe stability.
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

    @staticmethod
    def _seed_urls(db_name: str, official_docs_url: str) -> List[str]:
        db = (db_name or "").strip().lower()
        seeds = [official_docs_url]
        if db == "weaviate":
            seeds.extend(
                [
                    "https://weaviate.io/developers/weaviate/introduction",
                    "https://weaviate.io/developers/weaviate/manage-data",
                    "https://weaviate.io/developers/weaviate/search",
                    "https://weaviate.io/developers/weaviate/api",
                ]
            )
        return seeds

    def fetch(
        self,
        db_name: str,
        official_docs_url: str,
        *,
        is_official_url_checker,
    ) -> str:
        """
        Fetch a light subset of official docs pages and return formatted docs_context.
        """
        from bs4 import BeautifulSoup
        import httpx
        from src.parsers.html_cleaner import HTMLCleaner

        queue = deque(self._seed_urls(db_name, official_docs_url))
        queued = {self._normalize_url(u) for u in queue if u}
        visited = set()
        sections: List[str] = []

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Agent0DocsFallback/1.0; "
                "+https://weaviate.io/developers/weaviate)"
            )
        }
        with httpx.Client(timeout=self.request_timeout, follow_redirects=True, headers=headers) as client:
            while queue and len(sections) < self.max_pages:
                raw_url = queue.popleft()
                url = self._normalize_url(raw_url)
                if not url or url in visited:
                    continue
                visited.add(url)

                if not is_official_url_checker(url, db_name):
                    continue

                try:
                    resp = client.get(url)
                except Exception:
                    continue
                if not (200 <= resp.status_code < 300):
                    continue

                html = (resp.text or "").strip()
                if not html:
                    continue
                clean_text = HTMLCleaner.clean_html(html).strip()
                if len(clean_text) < 200:
                    continue

                title = HTMLCleaner.extract_title(html) or "No title"
                sections.append(
                    f"Source: {url}\nTitle: {title}\nDepth: 0\nContent:\n{clean_text}\n"
                )

                # Expand from official in-page links only.
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    for a in soup.find_all("a", href=True):
                        candidate = self._normalize_url(urljoin(url, a["href"]))
                        if not candidate or candidate in visited or candidate in queued:
                            continue
                        if is_official_url_checker(candidate, db_name):
                            queue.append(candidate)
                            queued.add(candidate)
                except Exception:
                    continue

        return "\n".join(sections)


class DBInfo(BaseModel):
    """Schema for extracting DB name and version."""
    db_name: str = Field(description="Name of the target vector database in lowercase (e.g., 'milvus', 'qdrant')")
    version: str = Field(description="Version of the target database (e.g., 'v2.3.6', 'latest')")

class EnvReconAgent:
    """
    Agent 0: Environment & Reconnaissance Agent
    Responsibilities:
    1. Parse the target DB and version using LLM.
    2. Search and scrape official documentation.
    3. Generate and execute Docker scripts to spin up the target DB.
    """
    
    def __init__(self):
        # Initialize configuration
        self.config = ConfigLoader()
        
        # Initialize LLM for parsing using centralized factory
        self.llm = get_llm(model_name="glm-4.7", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=DBInfo)
        
        # Define working directory for docker-compose files
        self.runs_dir = os.path.join(os.getcwd(), ".trae", "runs")
        os.makedirs(self.runs_dir, exist_ok=True)

        # Default Weaviate version used when user specifies "latest" (pin to a known-good image)
        self._weaviate_fallback_version = "1.36.9"

    def _resolve_docs_source(self) -> str:
        return str(self.config.get("docs.source", default="auto") or "auto").strip().lower()

    def _resolve_docs_jsonl_path(self, db_name: str) -> str:
        """
        Resolve docs JSONL path from .trae/config.yaml (docs.local_jsonl_path).

        Supports template variable: {db_name}
        """
        template = self.config.get(
            "docs.local_jsonl_path",
            default=".trae/cache/{db_name}_io_docs_depth3.jsonl",
        )
        try:
            template_str = str(template)
            db_lower = (db_name or "").strip().lower() or "unknown"

            # If template supports {db_name}, format it directly.
            if "{db_name}" in template_str:
                return template_str.format(db_name=db_lower)

            # Backward-compat / safety: if user configured a fixed filename (e.g. milvus_*.jsonl),
            # ensure we still generate a per-DB cache file to avoid cross-DB contamination.
            #
            # Example:
            #   docs.local_jsonl_path: .trae/cache/milvus_io_docs_depth3.jsonl
            # For qdrant, we rewrite to:
            #   .trae/cache/milvus_io_docs_depth3_qdrant.jsonl
            p = Path(template_str)
            if p.suffix.lower() in (".jsonl", ".json"):
                stem_lower = p.stem.lower()
                if db_lower not in stem_lower:
                    new_name = f"{p.stem}_{db_lower}{p.suffix}"
                    return str(p.with_name(new_name))

            # Otherwise, return template as-is.
            return template_str
        except Exception:
            # If template formatting fails, fall back to a safe default.
            return f".trae/cache/{db_name}_io_docs_depth3.jsonl"

    def _resolve_docs_cache_ttl_days(self) -> int:
        """
        Resolve docs cache TTL from .trae/config.yaml.

        Priority:
        1) docs.cache_ttl_days
        2) cache.ttl_days (backward-compatible)
        3) 7
        """
        ttl = self.config.get_int("docs.cache_ttl_days", default=0)
        if ttl and ttl > 0:
            return ttl
        ttl = self.config.get_int("cache.ttl_days", default=7)
        return ttl if ttl > 0 else 7

    def _basic_docs_validation(self, docs_context: str) -> dict:
        """Lightweight validation used for local_jsonl mode (no preprocess)."""
        total_docs = len(re.findall(r"^Source:", docs_context or "", re.MULTILINE))
        total_chars = len(docs_context or "")
        issues: List[str] = []
        if total_docs <= 0 or total_chars <= 0:
            issues.append("Local docs library produced empty context")
        return {
            "passed": len(issues) == 0,
            "total_docs": total_docs,
            "total_chars": total_chars,
            "issues": issues,
            "warnings": [],
        }

    def _normalize_version(self, db_name: str, version: Optional[str]) -> str:
        """
        Normalize version strings coming from LLM parsing.

        Goals:
        - Strip leading "v" for internal storage (e.g., "v1.36.9" -> "1.36.9")
        - Keep "latest" as-is for most DBs
        - Pin Weaviate "latest" to a stable fallback to avoid breaking changes
        """
        v = (version or "").strip()
        if not v:
            v = "latest"

        v_lower = v.lower()
        if v_lower == "latest":
            if (db_name or "").lower() == "weaviate":
                return self._weaviate_fallback_version
            return "latest"

        # Strip leading v/V only when it prefixes a numeric version
        v = re.sub(r"^[vV](?=\d)", "", v)
        return v

    def _docker_tag_for(self, db_name: str, normalized_version: str) -> str:
        """
        Convert normalized version to the concrete Docker tag expected by each image registry.
        """
        db = (db_name or "").lower()
        v = (normalized_version or "latest").strip()
        if v.lower() == "latest":
            return "latest"

        # Milvus and Qdrant images commonly tag releases with a leading 'v'
        if db in ("milvus", "qdrant"):
            return v if v.startswith("v") else f"v{v}"

        # Weaviate image tags are numeric (no leading 'v')
        if db == "weaviate":
            return re.sub(r"^[vV](?=\d)", "", v)

        return v

    @staticmethod
    def _is_port_allocation_error(error_text: str) -> bool:
        """
        Detect common Docker port-allocation conflict messages.
        """
        text = (error_text or "").lower()
        markers = (
            "port is already allocated",
            "address already in use",
            "bind for 0.0.0.0:",
            "bind: only one usage of each socket address",
        )
        return any(m in text for m in markers)

    def _cleanup_containers_publishing_port(self, host_port: int) -> int:
        """
        Best-effort cleanup for "from_scratch" runs: stop/remove previous hot sandboxes that
        are binding the target host port.
        """
        try:
            # NOTE: Avoid docker SDK here. Some environments fail to initialize docker-py due to
            # `http+docker://` transport issues. The Docker CLI is more robust/portable.
            #
            # `publish=<port>` filter returns containers that publish the given host port.
            ps = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"publish={host_port}", "--format", "{{.ID}}\t{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            logger.warning(f"[Agent 0] from_scratch cleanup skipped (docker CLI unavailable): {e}")
            return 0
        except Exception as e:
            logger.warning(f"[Agent 0] from_scratch cleanup skipped (docker invocation failed): {e}")
            return 0

        if ps.returncode != 0:
            msg = (ps.stderr or ps.stdout or "").strip()
            logger.warning(f"[Agent 0] from_scratch cleanup skipped (docker ps failed rc={ps.returncode}): {msg}")
            return 0

        # Lines look like: "<id>\t<name>"
        to_remove: list[tuple[str, str]] = []
        for raw in (ps.stdout or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            if "\t" in line:
                cid, name = line.split("\t", 1)
            else:
                # Defensive parsing (shouldn't happen with the chosen format)
                parts = line.split()
                cid, name = (parts[0], parts[1] if len(parts) > 1 else "")

            cid = cid.strip()
            name = name.strip()
            if not cid:
                continue
            to_remove.append((cid, name))

        removed = 0
        for cid, name in to_remove:
            try:
                rm = subprocess.run(
                    ["docker", "rm", "-f", cid],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if rm.returncode != 0:
                    msg = (rm.stderr or rm.stdout or "").strip()
                    logger.warning(
                        f"[Agent 0] from_scratch failed to remove container {name} ({cid}) rc={rm.returncode}: {msg}"
                    )
                    continue
                removed += 1
                logger.info(f"[Agent 0] from_scratch removed container: {name} ({cid}) (host_port={host_port})")
            except Exception as e:
                logger.warning(f"[Agent 0] from_scratch failed to remove container {name} ({cid}): {e}")

        if removed:
            # Re-check once to reduce flakiness where a container lingers briefly after rm -f.
            try:
                ps2 = subprocess.run(
                    ["docker", "ps", "-a", "--filter", f"publish={host_port}", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if ps2.returncode == 0:
                    remaining = [n.strip() for n in (ps2.stdout or "").splitlines() if n.strip()]
                    if remaining:
                        logger.warning(
                            f"[Agent 0] from_scratch cleanup incomplete: remaining={remaining} (host_port={host_port})"
                        )
            except Exception:
                pass

            logger.info(f"[Agent 0] from_scratch cleanup complete: removed={removed} (host_port={host_port})")
        return removed

    def _is_official_docs_url(self, url: str, db_name: str) -> bool:
        """Filter URLs to official documentation domains only."""
        db = (db_name or "").strip().lower()
        # IMPORTANT: patterns must be DB-specific; otherwise search fallback may
        # accidentally select Milvus docs when targeting qdrant/weaviate.
        per_db_patterns = {
            "milvus": [
                "milvus.io/docs",
                "zilliz.com",  # Milvus ecosystem docs
                "github.com/milvus-io",
            ],
            "qdrant": [
                "qdrant.tech/documentation",
                "github.com/qdrant",
            ],
            "weaviate": [
                "weaviate.io/developers/weaviate",
                "github.com/weaviate",
            ],
            "pinecone": ["docs.pinecone.io", "pinecone.io/docs", "github.com/pinecone-io"],
            "chroma": ["docs.trychroma.com", "chromadb.com", "github.com/chroma-core"],
            "elasticsearch": ["elastic.co/guide", "github.com/elastic"],
            "redis": ["redis.io/docs", "github.com/redis"],
            "mongodb": ["mongodb.com/docs/atlas/vector-search", "github.com/mongodb"],
            "clickhouse": ["clickhouse.com/docs", "github.com/clickhouse"],
        }
        official_patterns = per_db_patterns.get(db, [])
        # Generic fallbacks (still constrained to the DB name).
        if not official_patterns and db:
            official_patterns = [
                f"{db}.io/docs",
                f"{db}.org/docs",
                f"docs.{db}.io",
                f"github.com/{db}",
            ]
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in official_patterns)

    def _cached_docs_has_official_domain(self, docs_context: str, db_name: str) -> bool:
        """
        Validate that a cached docs blob contains at least one Source: URL that
        matches the target DB's official documentation domains/paths.

        This is a safety guard against cross-DB contamination when reusing
        previous runs' raw_docs.json snapshots.
        """
        if not (docs_context or "").strip():
            return False

        # Bound the scan to keep the check cheap.
        urls = re.findall(r"^Source:\s*(https?://\S+)", docs_context, flags=re.MULTILINE)
        for url in urls[:200]:
            try:
                if self._is_official_docs_url(url, db_name):
                    return True
            except Exception:
                continue
        return False

    def _fetch_official_docs_lightweight(
        self,
        db_name: str,
        official_docs_url: Optional[str],
        *,
        min_docs: int = 1,
        min_chars: int = 500,
    ) -> str:
        """
        Fallback path when deep crawling fails: fetch a small set of official docs pages
        and emit a compliant docs_context (Source/Title/Depth/Content).
        """
        if not (official_docs_url or "").strip():
            return ""

        _max_pages = 30 if (db_name or "").lower() == "weaviate" else 8
        fetcher = LightweightOfficialDocsFetcher(request_timeout=30.0, max_pages=_max_pages)
        docs_context = fetcher.fetch(
            db_name,
            official_docs_url,
            is_official_url_checker=self._is_official_docs_url,
        )

        if not (docs_context or "").strip():
            return ""

        # Reuse hard-gate to ensure downstream contract remains non-empty.
        self._ensure_docs_non_empty_or_abort(
            docs_context,
            db_name,
            where="fetch.lightweight_fallback",
            min_docs=min_docs,
            min_chars=min_chars,
        )
        return docs_context

    def _fetch_documentation(self, db_info: DBInfo) -> str:
        """Fetch actual documentation using Local Library or Deep Crawl4AI."""
        print(f"[Agent 0] Fetching real documentation for {db_info.db_name} {db_info.version}...")

        # Check if local JSONL documentation library is requested
        docs_source = self._resolve_docs_source()
        if docs_source == "local_jsonl":
            local_path = self._resolve_docs_jsonl_path(db_info.db_name)
            print(f"[Agent 0] Using local documentation library: {local_path}")
            print("[Agent 0] docs.source=local_jsonl: skip crawl/cache/preprocess; load JSONL directly per DB")
            
            library = LocalDocsLibrary(local_path, db_name=db_info.db_name)
            docs_context = library.load_docs_context()
            
            if not docs_context.strip():
                raise RuntimeError(f"Local documentation library is empty or all items were filtered out: {local_path}")
                
            return docs_context

        # Check for cached documentation from previous runs.
        # When docs.source='crawl', skip reuse: caller explicitly asked for a fresh crawl.
        import glob
        cache_files = []
        if docs_source != "crawl":
            cache_files = glob.glob(os.path.join(self.runs_dir, "*", "raw_docs.json"))
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if cached_data.get('db_name') == db_info.db_name and cached_data.get('version') == db_info.version:
                        cached_docs = cached_data.get('full_docs', '') or ''
                        if not self._cached_docs_has_official_domain(cached_docs, db_info.db_name):
                            print(
                                f"[Agent 0] Ignoring cached documentation from: {os.path.basename(os.path.dirname(cache_file))} "
                                f"(no official {db_info.db_name} docs domain detected)"
                            )
                            continue
                        print(f"[Agent 0] Using cached documentation from: {os.path.basename(os.path.dirname(cache_file))}")
                        return cached_docs
            except Exception as e:
                print(f"[Agent 0] Failed to read cache file {cache_file}: {e}")
                continue

        docs_context = ""
        official_docs_url = None
        try:
            _max_pages = 200 if (db_info.db_name or "").lower() == "weaviate" else 100
            _total_timeout = 1200 if (db_info.db_name or "").lower() == "weaviate" else 600
            deep_crawler = DeepCrawler(
                max_depth=3,
                page_timeout=30,
                total_timeout=_total_timeout,
                max_pages=_max_pages
            )
            
            official_docs_url = deep_crawler._get_official_docs_url(db_info.db_name)
            
            if not official_docs_url:
                print(f"[Agent 0] No official docs URL mapping for {db_info.db_name}, falling back to search...")
                from langchain_community.tools import DuckDuckGoSearchResults
                search_tool = DuckDuckGoSearchResults(max_results=10)
                query = f"{db_info.db_name} {db_info.version} official documentation"
                search_results = search_tool.invoke({"query": query})

                import re
                all_links = re.findall(r'link:\s*(https?://[^\s,\]]+)', search_results)

                if not all_links:
                    print("[Agent 0] Could not find relevant URLs via DuckDuckGo.")
                    return "Could not find official documentation URLs."

                filtered_links = [url for url in all_links if self._is_official_docs_url(url, db_info.db_name)]
                
                if filtered_links:
                    official_docs_url = filtered_links[0]
                    print(f"[Agent 0] Using search result as start URL: {official_docs_url}")
                else:
                    print(f"[Agent 0] WARNING: No official docs found in search results.")
                    return "Could not find official documentation URLs."

            print(f"[Agent 0] Starting deep crawl from: {official_docs_url}")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            docs_context, crawl_stats = loop.run_until_complete(
                deep_crawler.deep_crawl(official_docs_url, db_info.db_name)
            )
            
            print(f"[Agent 0] Deep crawl completed: {crawl_stats['total_crawled']} pages, max depth {crawl_stats['current_depth']}")
            
            if crawl_stats['failed_urls']:
                print(f"[Agent 0] Failed URLs: {len(crawl_stats['failed_urls'])}")
                for failed in crawl_stats['failed_urls'][:5]:
                    print(f"  - {failed['url']}: {failed['error']}")

            if not docs_context.strip():
                docs_context = "Failed to extract content from deep crawl."

        except Exception as e:
            print(f"[Agent 0] Deep crawl failed for {db_info.db_name}: {e}")
            try:
                fallback_docs = self._fetch_official_docs_lightweight(
                    db_info.db_name,
                    official_docs_url,
                    min_docs=1,
                    min_chars=500 if db_info.db_name.lower() == "weaviate" else 200,
                )
                if fallback_docs.strip():
                    print(
                        f"[Agent 0] Lightweight official docs fallback succeeded "
                        f"for {db_info.db_name} (chars={len(fallback_docs):,})"
                    )
                    docs_context = fallback_docs
                else:
                    raise RuntimeError("lightweight fallback returned empty docs")
            except Exception as fallback_error:
                print(f"[Agent 0] Failed to fetch real documentation: {e}; fallback failed: {fallback_error}")
                raise RuntimeError(
                    f"Documentation fetching failed: deep_crawl={e}; fallback={fallback_error}"
                ) from fallback_error

        return docs_context

    def _docs_preprocess_policy(self, db_name: str, docs_config) -> SimpleNamespace:
        """
        Build per-DB preprocessing/validation policy.

        Why:
        - Milvus docs live under /docs/ and are versioned (/docs/v2.6/...)
        - Qdrant docs live under /documentation/ (not /docs/)
        - Weaviate docs live under /developers/weaviate (not /docs/)

        We keep this policy intentionally conservative to avoid accidentally filtering
        out the whole corpus for non-Milvus DBs.
        """
        db = (db_name or "").strip().lower()

        # Defaults from global DocsConfig (historically tuned for Milvus).
        default_allowed_versions = list(getattr(docs_config, "allowed_versions", []) or [])
        default_min_chars = int(getattr(docs_config, "min_chars", 500) or 500)
        default_min_docs = int(getattr(docs_config, "min_docs", 50) or 50)
        default_required_docs = list(getattr(docs_config, "required_docs", []) or [])

        if db == "milvus":
            return SimpleNamespace(
                db_name=db,
                url_path_allow_substrings=["/docs"],
                allowed_versions=default_allowed_versions,
                min_chars=default_min_chars,
                min_docs=default_min_docs,
                required_docs=default_required_docs,
                # Hard minimums: used only to decide abort vs proceed.
                hard_min_docs=1,
                hard_min_chars=500,
            )

        if db == "qdrant":
            # Qdrant docs are not consistently versioned in URL; do not apply version gating.
            return SimpleNamespace(
                db_name=db,
                url_path_allow_substrings=["/documentation"],
                allowed_versions=[],
                min_chars=max(250, min(default_min_chars, 500)),
                min_docs=max(10, min(default_min_docs, 30)),
                required_docs=["collection", "point", "vector", "filter"],
                hard_min_docs=1,
                hard_min_chars=500,
            )

        if db == "weaviate":
            return SimpleNamespace(
                db_name=db,
                url_path_allow_substrings=["/developers/weaviate", "/docs.weaviate.io/weaviate", "/docs.weaviate.io/deploy", "/docs.weaviate.io/concepts"],
                allowed_versions=[],
                min_chars=max(250, min(default_min_chars, 200)),
                min_docs=3,
                required_docs=["schema"],
                hard_min_docs=1,
                hard_min_chars=200,
            )

        # Fallback for other DBs: allow any path under the start domain; do not apply version gating.
        return SimpleNamespace(
            db_name=db or "unknown",
            url_path_allow_substrings=[],
            allowed_versions=[],
            min_chars=max(200, min(default_min_chars, 500)),
            min_docs=max(5, min(default_min_docs, 20)),
            required_docs=[],
            hard_min_docs=1,
            hard_min_chars=500,
        )

    def _filter_docs(self, docs_content: str, policy: SimpleNamespace) -> tuple:
        """
        Filter crawled documents by version and quality.

        Args:
            docs_content: Raw markdown content from crawling
            policy: per-DB preprocessing policy

        Returns:
            (filtered_content, stats_dict)

        Filter rules:
        - Path: Keep only allowed doc paths for this DB (e.g. /documentation for qdrant)
        - Version match (Milvus only by default): Only keep URLs containing /docs/v{allowed_version}
        - Quality: Each document section should have at least min_chars characters
        """
        logger.info("[Preprocess] Starting document filtering...")

        allowed_versions = list(getattr(policy, "allowed_versions", []) or [])
        min_chars = int(getattr(policy, "min_chars", 500) or 500)
        allow_paths = [p.lower() for p in (getattr(policy, "url_path_allow_substrings", []) or []) if isinstance(p, str) and p.strip()]

        # Split content into document sections (each starts with "Source:")
        sections = re.split(r'(?=^Source:)', docs_content, flags=re.MULTILINE)
        filtered_sections = []
        stats = {
            "total_sections": len(sections),
            "filtered_in": 0,
            "filtered_out_version": 0,
            "filtered_out_quality": 0,
            "filtered_out_path": 0,
        }

        for section in sections:
            if not section.strip():
                continue

            # Extract URL from the Source: line
            url_match = re.search(r'Source:\s*(https?://\S+)', section)
            if not url_match:
                # No URL found, keep it (might be a header or metadata)
                filtered_sections.append(section)
                stats["filtered_in"] += 1
                continue

            url = url_match.group(1)

            # Rule 1: Path filter - keep only DB-specific doc paths (if configured).
            parsed_url = urlparse(url)
            path_lower = parsed_url.path.lower()
            if allow_paths:
                if not any(p in path_lower for p in allow_paths):
                    stats["filtered_out_path"] += 1
                    logger.debug(f"[Preprocess] Filtered out (path): {url}")
                    continue

            # Rule 2: Version filter - check for allowed version patterns
            if allowed_versions:
                version_match_found = False
                for ver in allowed_versions:
                    # Milvus-style versioning: /docs/v2.6/
                    pattern = f'/docs/v{re.escape(ver)}'
                    if pattern in path_lower:
                        version_match_found = True
                        break
                    # Also allow URLs that don't have an explicit version (root landing pages).
                    if path_lower.rstrip('/') in ('/docs', '/docs/', '/docs/zh', '/docs/zh/'):
                        version_match_found = True
                        break

                if not version_match_found:
                    stats["filtered_out_version"] += 1
                    logger.debug(f"[Preprocess] Filtered out (version): {url}")
                    continue

            # Rule 3: Quality filter - minimum character count per section
            content_match = re.search(r'Content:\n?(.*)', section, re.DOTALL)
            content_text = content_match.group(1) if content_match else section
            if len(content_text.strip()) < min_chars:
                stats["filtered_out_quality"] += 1
                logger.debug(f"[Preprocess] Filtered out (quality, {len(content_text.strip())} chars < {min_chars}): {url}")
                continue

            filtered_sections.append(section)
            stats["filtered_in"] += 1

        filtered_content = "\n".join(filtered_sections)
        logger.info(
            f"[Preprocess] Filter complete: {stats['filtered_in']}/{stats['total_sections']} sections kept "
            f"(version={stats['filtered_out_version']}, quality={stats['filtered_out_quality']}, path={stats['filtered_out_path']})"
        )

        return filtered_content, stats

    def _validate_docs(self, filtered_content: str, policy: SimpleNamespace) -> dict:
        """
        Validate document library quality.

        Args:
            filtered_content: Filtered document content
            policy: per-DB preprocessing policy

        Returns:
            {
                "passed": bool,
                "total_docs": int,
                "total_chars": int,
                "issues": list[str],
                "warnings": list[str]
            }

        Validation checks:
        - Total document count >= min_docs
        - Required keywords exist in content (if configured)
        - Total chars > 1M (for meaningful corpus)
        """
        logger.info("[Preprocess] Starting document validation...")

        min_docs = int(getattr(policy, "min_docs", 0) or 0)
        required_keywords = list(getattr(policy, "required_docs", []) or [])
        db_name = getattr(policy, "db_name", "unknown")

        issues = []
        warnings = []

        # Count documents (sections starting with "Source:")
        doc_count = len(re.findall(r'^Source:', filtered_content, re.MULTILINE))
        total_chars = len(filtered_content)

        # Check 1: Minimum document count
        if min_docs and doc_count < min_docs:
            issues.append(
                f"Document count ({doc_count}) below minimum threshold ({min_docs})"
            )
        else:
            logger.debug(f"[Preprocess] Doc count OK: {doc_count} >= {min_docs}")

        # Check 2: Required keywords presence (optional per DB)
        if required_keywords:
            missing_keywords = []
            haystack = filtered_content.lower()
            for keyword in required_keywords:
                if keyword.lower() not in haystack:
                    missing_keywords.append(keyword)

            if missing_keywords:
                issues.append(
                    f"Missing required keywords ({db_name}): {missing_keywords}"
                )
            else:
                logger.debug(f"[Preprocess] Required keywords OK: all {len(required_keywords)} found")

        # Check 3: Total character count (1M threshold for meaningful corpus)
        min_corpus_size = 1_000_000
        if total_chars < min_corpus_size:
            warnings.append(
                f"Total corpus size ({total_chars:,} chars) is below recommended minimum ({min_corpus_size:,} chars)"
            )
        else:
            logger.debug(f"[Preprocess] Corpus size OK: {total_chars:,} chars")

        passed = len(issues) == 0

        result = {
            "passed": passed,
            "total_docs": doc_count,
            "total_chars": total_chars,
            "issues": issues,
            "warnings": warnings,
        }

        status_label = "PASSED" if passed else "FAILED"
        logger.info(
            f"[Preprocess] Validation {status_label}: "
            f"docs={doc_count}, chars={total_chars:,}, issues={len(issues)}, warnings={len(warnings)}"
        )
        if issues:
            for issue in issues:
                logger.warning(f"[Preprocess] Issue: {issue}")
        if warnings:
            for warning in warnings:
                logger.warning(f"[Preprocess] Warning: {warning}")

        return result

    def _ensure_docs_non_empty_or_abort(
        self,
        docs_context: str,
        db_name: str,
        *,
        where: str,
        min_docs: int = 1,
        min_chars: int = 200,
    ) -> None:
        """
        Hard gate: if docs_context is empty (or effectively empty), abort early.

        This prevents downstream agents from operating without evidence, and avoids writing/using empty caches.
        """
        text = (docs_context or "").strip()
        doc_count = len(re.findall(r"^Source:", text, re.MULTILINE))
        total_chars = len(text)

        placeholder_markers = (
            "could not find official documentation urls",
            "failed to extract content from deep crawl",
            "documentation fetching failed",
        )
        looks_like_placeholder = any(m in text.lower() for m in placeholder_markers)

        # Minimal non-empty contract: at least `min_docs` Source sections and some content.
        if (not text) or doc_count < int(min_docs) or total_chars < int(min_chars) or looks_like_placeholder:
            raise RuntimeError(
                f"Official docs context is empty/invalid for db={db_name} (where={where}, docs={doc_count}, chars={total_chars}). "
                f"Abort to avoid running without documentation evidence."
            )

    def _save_docs_cache(self, content: str, cache_path: str) -> None:
        """
        Save documents to JSONL cache file.

        Args:
            content: Document content to save
            cache_path: Path to output JSONL file

        Format: Each line is a JSON object with url, markdown, metadata fields.
        If the raw content is not already structured as JSONL,
        wrap it in a single record format.
        """
        # Avoid writing empty cache files: treat empty/whitespace content as a no-op.
        if not (content or "").strip():
            logger.info(f"[Preprocess] Skip saving docs cache: empty content (path={cache_path})")
            return

        logger.info(f"[Preprocess] Saving docs cache to: {cache_path}")

        try:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Check if content looks like it's already structured with Source: markers
            # If so, split into individual records; otherwise wrap as single record
            sections = re.split(r'(?=^Source:)', content, flags=re.MULTILINE)

            records: List[dict] = []
            for i, section in enumerate(sections):
                if not section.strip():
                    continue

                # Extract metadata from each section
                url_match = re.search(r'Source:\s*(https?://\S+)', section)
                title_match = re.search(r'Title:\s*(.+)', section)
                depth_match = re.search(r'Depth:\s*(\d+)', section)
                content_match = re.search(r'Content:\n?(.*)', section, re.DOTALL)

                record = {
                    "url": url_match.group(1).strip() if url_match else f"section_{i}",
                    "markdown": content_match.group(1).strip() if content_match else section.strip(),
                    "metadata": {
                        "title": title_match.group(1).strip() if title_match else "",
                        "depth": int(depth_match.group(1)) if depth_match else 0,
                        "cached_at": datetime.now().isoformat(),
                    }
                }
                records.append(record)

            if not records:
                logger.info(f"[Preprocess] Skip saving docs cache: no non-empty records (path={cache_path})")
                return

            # Write to a temp file and atomically replace to avoid leaving a truncated cache on failure.
            tmp_path = cache_file.with_suffix(cache_file.suffix + ".tmp")
            with open(tmp_path, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            os.replace(tmp_path, cache_file)

            cache_size_kb = cache_file.stat().st_size / 1024
            logger.info(f"[Preprocess] Cache saved: {cache_path} ({cache_size_kb:.1f}KB, {len(records)} records)")

        except Exception as e:
            logger.error(f"[Preprocess] Failed to save docs cache: {e}")
            raise

    def _load_docs_cache(self, cache_path: str, ttl_days: int = 7) -> Optional[str]:
        """
        Load documents from cache if valid.

        Args:
            cache_path: Path to JSONL cache file
            ttl_days: Cache TTL in days

        Returns:
            Document content string if cache is valid, None otherwise

        Validation:
        - File exists
        - File age < ttl_days
        - File size > 100KB (not empty/corrupted)
        """
        logger.info(f"[Preprocess] Loading docs cache from: {cache_path} (TTL={ttl_days} days)")

        cache_file = Path(cache_path)

        # Check 1: File existence
        if not cache_file.exists():
            logger.info(f"[Preprocess] Cache MISS: file does not exist: {cache_path}")
            return None

        # Treat empty JSONL cache files as a miss (common failure mode when previous runs wrote nothing).
        try:
            if cache_file.stat().st_size == 0:
                logger.info(f"[Preprocess] Cache MISS: empty file: {cache_path}")
                return None
        except OSError as e:
            logger.error(f"[Preprocess] Error checking cache file size: {e}")
            return None

        # Check 2: File age vs TTL
        try:
            file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            file_age_days = (datetime.now() - file_mtime).days

            if file_age_days >= ttl_days:
                logger.info(
                    f"[Preprocess] Cache MISS: expired (age={file_age_days} days >= TTL={ttl_days} days)"
                )
                return None
        except OSError as e:
            logger.error(f"[Preprocess] Error checking cache file age: {e}")
            return None

        # Check 3: File size > 100KB
        min_size_kb = 100
        file_size_kb = cache_file.stat().st_size / 1024
        if file_size_kb < min_size_kb:
            logger.info(
                f"[Preprocess] Cache MISS: file too small ({file_size_kb:.1f}KB < {min_size_kb}KB), likely empty/corrupted"
            )
            return None

        # Load and reconstruct content
        try:
            records = []
            with open(cache_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[Preprocess] Skipping malformed JSONL line: {e}")
                        continue

            if not records:
                logger.info("[Preprocess] Cache MISS: no valid records found")
                return None

            # Reconstruct markdown content from records
            reconstructed_parts = []
            for record in records:
                url = record.get('url', '')
                title = record.get('metadata', {}).get('title', 'No title')
                depth = record.get('metadata', {}).get('depth', 0)
                markdown = record.get('markdown', '')

                reconstructed_parts.append(
                    f"Source: {url}\nTitle: {title}\nDepth: {depth}\nContent:\n{markdown}\n"
                )

            content = "\n".join(reconstructed_parts)
            logger.info(
                f"[Preprocess] Cache HIT: {cache_path} "
                f"(size={file_size_kb:.1f}KB, age={file_age_days} days, records={len(records)})"
            )
            return content

        except Exception as e:
            logger.error(f"[Preprocess] Error loading docs cache: {e}")
            return None

    def _preprocess_docs(self, raw_docs: str, state: WorkflowState, policy: SimpleNamespace, cache_path: str) -> str:
        """
        Main preprocessing pipeline: filter -> validate -> cache.

        Args:
            raw_docs: Raw crawled document content
            state: Current workflow state (contains config)

        Returns:
            Processed document content ready for use
        """
        logger.info("[Preprocess] === Starting Document Preprocessing Pipeline ===")

        # Step 1: Filter documents
        logger.info("[Preprocess] [Step 1/3] Filtering documents...")
        filtered_content, filter_stats = self._filter_docs(raw_docs, policy)

        # Step 2: Validate document library quality
        logger.info("[Preprocess] [Step 2/3] Validating document library...")
        validation_result = self._validate_docs(filtered_content, policy)

        # Store validation result on state for downstream consumers
        state.docs_validation = validation_result

        # Hard abort if filtering produced empty content (critical failure mode).
        # This is stricter than validation: we refuse to proceed without any official docs sections.
        try:
            self._ensure_docs_non_empty_or_abort(
                filtered_content,
                getattr(policy, "db_name", "unknown"),
                where="preprocess.filtered",
                min_docs=int(getattr(policy, "hard_min_docs", 1) or 1),
                min_chars=int(getattr(policy, "hard_min_chars", 200) or 200),
            )
        except Exception as e:
            logger.error(f"[Preprocess] Aborting due to empty/invalid filtered corpus: {e}")
            raise

        # Log warning if validation did not pass but still proceed
        if not validation_result["passed"]:
            logger.warning(
                f"[Preprocess] Validation FAILED but proceeding with available content. "
                f"Issues: {validation_result['issues']}"
            )

        # Step 3: Save to cache
        logger.info("[Preprocess] [Step 3/3] Saving to JSONL cache...")
        try:
            self._save_docs_cache(filtered_content, cache_path)
        except Exception as e:
            logger.error(f"[Preprocess] Cache save failed (non-fatal): {e}")

        logger.info(
            f"[Preprocess] === Pipeline Complete === "
            f"filtered={filter_stats['filtered_in']}/{filter_stats['total_sections']} sections, "
            f"validation={'PASS' if validation_result['passed'] else 'FAIL'}, "
            f"chars={validation_result['total_chars']:,}"
        )

        return filtered_content

    def _parse_input(self, user_input: str) -> DBInfo:
        """Use LLM to parse user input into structured DB name and version."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert DevOps assistant. Extracts target vector database name and version from user's input. Ensure that db_name is lowercase. If no version is specified, default to 'latest'.\n{format_instructions}"),
            ("human", "{input}")
        ])
        # Inject format instructions into the prompt
        formatted_prompt = prompt.partial(format_instructions=self.parser.get_format_instructions())
        chain = formatted_prompt | self.llm | self.parser
        res = chain.invoke({"input": user_input})
        # Ensure result is a DBInfo object or dict converted to DBInfo
        if isinstance(res, dict):
            return DBInfo(**res)
        return res

    def _generate_docker_compose(self, db_info: DBInfo, run_id: str) -> Tuple[str, str, Dict[str, str]]:
        """Generate docker-compose.yml content based on the target DB."""
        run_dir = os.path.join(self.runs_dir, run_id)
        os.makedirs(run_dir, exist_ok=True)
        compose_file_path = os.path.join(run_dir, "docker-compose.yml")
        
        endpoint = ""
        credentials = {}
        compose_content = {}
        
        if db_info.db_name == "milvus":
            # Basic Milvus standalone template
            milvus_tag = self._docker_tag_for(db_info.db_name, db_info.version)
            minio_access_key = os.getenv("MILVUS_MINIO_ACCESS_KEY", f"ak_{secrets.token_hex(8)}")
            minio_secret_key = os.getenv("MILVUS_MINIO_SECRET_KEY", secrets.token_urlsafe(24))
            compose_content = {
                "version": "3.5",
                "services": {
                    "etcd": {
                        "container_name": f"milvus-etcd-{run_id}",
                        "image": "quay.io/coreos/etcd:v3.5.5",
                        "environment": [
                            "ETCD_AUTO_COMPACTION_MODE=revision",
                            "ETCD_AUTO_COMPACTION_RETENTION=1000",
                            "ETCD_QUOTA_BACKEND_BYTES=4294967296",
                            "ETCD_SNAPSHOT_COUNT=50000"
                        ],
                        "command": "etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd"
                    },
                    "minio": {
                        "container_name": f"milvus-minio-{run_id}",
                        "image": "minio/minio:RELEASE.2023-03-20T20-16-18Z",
                        "environment": [
                            f"MINIO_ACCESS_KEY={minio_access_key}",
                            f"MINIO_SECRET_KEY={minio_secret_key}"
                        ],
                        "command": "minio server /minio_data",
                        "healthcheck": {
                            "test": ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
                            "interval": "30s",
                            "timeout": "20s",
                            "retries": 3
                        }
                    },
                    "standalone": {
                        "container_name": f"milvus-standalone-{run_id}",
                        "image": f"milvusdb/milvus:{milvus_tag}",
                        "command": ["milvus", "run", "standalone"],
                        "environment": [
                            "ETCD_ENDPOINTS=etcd:2379",
                            "MINIO_ADDRESS=minio:9000",
                            f"MINIO_ACCESS_KEY={minio_access_key}",
                            f"MINIO_SECRET_KEY={minio_secret_key}"
                        ],
                        "ports": ["19530:19530", "9091:9091"],
                        "depends_on": ["etcd", "minio"]
                    }
                }
            }
            endpoint = "localhost:19530"
            credentials = {
                "minio_access_key": minio_access_key,
                "minio_secret_key": minio_secret_key,
            }
            
        elif db_info.db_name == "qdrant":
            # Qdrant standalone template
            qdrant_tag = self._docker_tag_for(db_info.db_name, db_info.version)
            compose_content = {
                "version": "3",
                "services": {
                    "qdrant": {
                        "container_name": f"qdrant-{run_id}",
                        "image": f"qdrant/qdrant:{qdrant_tag}",
                        "ports": ["6333:6333", "6334:6334"]
                    }
                }
            }
            endpoint = "localhost:6333"
            credentials = {"api_key": ""}

        elif db_info.db_name == "weaviate":
            # Weaviate template
            weaviate_version = self._docker_tag_for(db_info.db_name, db_info.version) or self._weaviate_fallback_version
            compose_content = {
                "version": "3.8",
                "services": {
                    "weaviate": {
                        "container_name": f"weaviate-{run_id}",
                        "image": f"cr.weaviate.io/semitechnologies/weaviate:{weaviate_version}",
                        "ports": ["8081:8080", "50051:50051"],
                        "environment": [
                            "QUERY_DEFAULTS_LIMIT=25",
                            "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true",
                            "PERSISTENCE_DATA_PATH=/var/lib/weaviate",
                            "DEFAULT_VECTORIZER_MODULE=none"
                        ],
                        "volumes": [f"weaviate_data_{run_id}:/var/lib/weaviate"]
                    }
                },
                "volumes": {f"weaviate_data_{run_id}": None}
            }
            endpoint = "localhost:8081"
            credentials = {}

        else:
            raise ValueError(f"Unsupported database: {db_info.db_name}")

        # Write to file
        with open(compose_file_path, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False)
            
        return compose_file_path, endpoint, credentials

    def _spin_up_sandbox(self, db_info: DBInfo, compose_file: str, endpoint: str, from_scratch: bool = False) -> bool:
        """
        Check if a hot sandbox is already running to avoid cold start overhead.
        If not, spin up a new Docker environment.
        """
        import socket
        
        host, port = endpoint.split(':')
        port = int(port)
        
        # Simple port check to see if the sandbox is already "hot"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex((host, port))
            if result == 0 and not from_scratch:
                print(f"[Agent 0] Hot sandbox detected on {endpoint}. Reusing environment.")
                return True
            if result == 0 and from_scratch:
                print(f"[Agent 0] from_scratch=true, tearing down prior hot sandbox on {endpoint} (best-effort).")
                self._cleanup_containers_publishing_port(port)
                
        # If not hot, cold start
        run_dir = os.path.dirname(compose_file)
        print(f"[Agent 0] No hot sandbox found. Cold starting Docker environment in {run_dir}...")
        try:
            # Use docker compose v2 (preferred) and disable ANSI to keep logs parseable in CI/sandboxes.
            # Explicitly pass -f docker-compose.yml to avoid picking up other compose files accidentally.
            subprocess.run(
                ["docker", "compose", "--ansi", "never", "-f", "docker-compose.yml", "up", "-d"],
                cwd=run_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            # Add a small delay to let services initialize
            import time
            time.sleep(5)
            return True
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            combined_output = "\n".join([p for p in (stderr, stdout) if p]).strip()

            # from_scratch mode: if compose fails due to host-port conflict, auto-clean and retry once.
            if from_scratch and self._is_port_allocation_error(combined_output):
                print(
                    f"[Agent 0] from_scratch detected port allocation conflict on {endpoint}. "
                    f"Attempting auto-cleanup and one retry."
                )
                removed = self._cleanup_containers_publishing_port(port)
                if removed > 0:
                    try:
                        subprocess.run(
                            ["docker", "compose", "--ansi", "never", "-f", "docker-compose.yml", "up", "-d"],
                            cwd=run_dir,
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                        import time
                        time.sleep(5)
                        return True
                    except subprocess.CalledProcessError as retry_e:
                        retry_stderr = (retry_e.stderr or "").strip()
                        retry_stdout = (retry_e.stdout or "").strip()
                        detail = " | ".join(
                            [
                                f"cmd={getattr(retry_e, 'cmd', None)}",
                                f"returncode={getattr(retry_e, 'returncode', None)}",
                                f"stderr={retry_stderr}" if retry_stderr else "",
                                f"stdout={retry_stdout}" if retry_stdout else "",
                            ]
                        ).strip(" |")
                        raise RuntimeError(
                            f"Failed to spin up Docker environment after port-conflict cleanup: {detail}"
                        ) from retry_e

            detail_parts = [
                f"cmd={getattr(e, 'cmd', None)}",
                f"returncode={getattr(e, 'returncode', None)}",
            ]
            if stderr:
                detail_parts.append(f"stderr={stderr}")
            if stdout:
                detail_parts.append(f"stdout={stdout}")
            detail = " | ".join(detail_parts)
            print(f"[Agent 0] Error: docker compose failed: {detail}")
            raise RuntimeError(f"Failed to spin up Docker environment: {detail}") from e
        except FileNotFoundError as e:
            print(f"[Agent 0] Error: docker CLI not found: {e}")
            raise RuntimeError(f"Failed to spin up Docker environment: docker CLI not found ({e})") from e
        except Exception as e:
            print(f"[Agent 0] Error: Docker compose failed or docker not running: {e}.")
            raise RuntimeError(f"Failed to spin up Docker environment: {e}") from e

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Main execution flow for Agent 0."""
        print(f"[Agent 0] Starting environment initialization for: {state.target_db_input}")
        
        # Step 1: Parse Input using LLM
        import tenacity
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            with get_openai_callback() as cb:
                res = self._parse_input(state.target_db_input)
                return res, cb.total_tokens

        db_info, tokens_used = _invoke_with_retry()
        state.total_tokens_used += tokens_used
        db_info.version = self._normalize_version(db_info.db_name, db_info.version)
        print(f"[Agent 0] Parsed target DB: {db_info.db_name}, Version: {db_info.version} (Tokens: {tokens_used})")
        
        # Step 2: Fetch Real Documentation
        docs_context = ""
        cache_hit = False

        docs_source = self._resolve_docs_source()
        if docs_source == "local_jsonl":
            # Local JSONL mode: treat the JSONL as the source of truth; do not apply cache TTL or preprocess.
            local_path = self._resolve_docs_jsonl_path(db_info.db_name)
            logger.info(f"[Agent 0] docs.source=local_jsonl, loading per-db JSONL: {local_path}")
            library = LocalDocsLibrary(local_path, db_name=db_info.db_name)
            docs_context = library.load_docs_context()
            state.docs_validation = self._basic_docs_validation(docs_context)
        else:
            # Cache-first strategy (JSONL cache) + preprocess on miss
            cache_path = self._resolve_docs_jsonl_path(db_info.db_name)
            ttl_days = self._resolve_docs_cache_ttl_days()

            # Use AppConfig docs settings only for filtering/validation knobs (NOT for cache path/TTL).
            from src.config import get_config as _get_app_config
            docs_config = _get_app_config().docs
            policy = self._docs_preprocess_policy(db_info.db_name, docs_config)

            cached_content = self._load_docs_cache(cache_path, ttl_days=ttl_days)
            if cached_content is not None:
                logger.info("[Agent 0] Cache HIT - using cached documents, skipping crawl")
                docs_context = cached_content
                cache_hit = True

                # Run validation on cached content to populate docs_validation on state
                validation_result = self._validate_docs(docs_context, policy)
                state.docs_validation = validation_result
                logger.info(
                    f"[Agent 0] Cached docs validation: "
                    f"{'PASS' if validation_result['passed'] else 'FAIL'} "
                    f"(docs={validation_result['total_docs']}, chars={validation_result['total_chars']:,})"
                )
            else:
                logger.info("[Agent 0] Cache MISS - performing full documentation fetch")
                raw_docs = self._fetch_documentation(db_info)
                docs_context = self._preprocess_docs(raw_docs, state, policy, cache_path=cache_path)

        mode_label = "local_jsonl" if docs_source == "local_jsonl" else ("cache=HIT" if cache_hit else "cache=MISS")
        print(f"[Agent 0] Fetched real documentation for {db_info.db_name} ({mode_label})")

        # Hard gate: docs_context must be non-empty/valid regardless of source (local_jsonl/cache/crawl).
        hard_min_docs = 1
        hard_min_chars = 200
        if docs_source != "local_jsonl":
            hard_min_docs = int(getattr(policy, "hard_min_docs", 1) or 1)
            hard_min_chars = int(getattr(policy, "hard_min_chars", 200) or 200)
        self._ensure_docs_non_empty_or_abort(
            docs_context,
            db_info.db_name,
            where=f"execute.{mode_label}",
            min_docs=hard_min_docs,
            min_chars=hard_min_chars,
        )
        
        # Step 3: Spin up Environment
        try:
            compose_file, endpoint, credentials = self._generate_docker_compose(db_info, state.run_id)
            print(f"[Agent 0] Generated compose file at: {compose_file}")
            
            # Use the new sandbox pool method
            success = self._spin_up_sandbox(db_info, compose_file, endpoint, from_scratch=bool(getattr(state, "from_scratch", False)))
            if success:
                print(f"[Agent 0] Successfully prepared {db_info.db_name} container on {endpoint}")
            
        except Exception as e:
            print(f"[Agent 0] Failed to spin up environment: {e}")
            raise e
        
        # Update State
        state.db_config = DatabaseConfig(
            db_name=db_info.db_name,
            version=db_info.version,
            endpoint=endpoint,
            credentials=credentials,
            docs_context=docs_context
        )
        
        # WBS 2.0: Full Evidence Preservation - Atomic Documentation Snapshotting
        try:
            import json
            run_dir = os.path.join(self.runs_dir, state.run_id)
            os.makedirs(run_dir, exist_ok=True)
            doc_path = os.path.join(run_dir, "raw_docs.json")
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump({
                    "db_name": db_info.db_name,
                    "version": db_info.version,
                    "full_docs": docs_context,
                    "cache_hit": cache_hit,
                    "docs_validation": state.docs_validation,
                    "timestamp": os.path.getmtime(compose_file) if os.path.exists(compose_file) else 0
                }, f, indent=2)
            print(f"[Agent 0] Atomic documentation snapshot saved to {doc_path}")
        except Exception as e:
            print(f"[Agent 0] Warning: Failed to save raw_docs.json: {e}")
        
        return state

def agent0_environment_recon(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = EnvReconAgent()
    return agent.execute(state)
