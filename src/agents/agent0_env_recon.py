import os
import subprocess
import yaml
import asyncio
import json
import hashlib
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
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DomainFilter, FilterChain
from urllib.parse import urlparse
import time

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
        print(f"[DeepCrawler] Starting deep crawl from {start_url} (max_depth={self.max_depth})")
        
        base_domain = self._extract_domain(start_url)
        markdown_results = []
        self.crawl_stats["start_time"] = time.time()
        
        # 设置用户数据目录和数据库目录以避免权限问题
        import tempfile
        crawl_base_dir = tempfile.mkdtemp(prefix="crawl4ai_")
        user_data_dir = tempfile.mkdtemp(prefix="crawl4ai_browser_")
        
        # 设置环境变量以使用临时目录
        import os
        os.environ["CRAWL4_AI_BASE_DIRECTORY"] = crawl_base_dir
        
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

    def _is_official_docs_url(self, url: str, db_name: str) -> bool:
        """Filter URLs to official documentation domains only."""
        official_patterns = [
            f"{db_name}.io/docs",
            f"{db_name}.org/docs",
            f"docs.{db_name}.io",
            f"github.com/{db_name}",
            f"milvus.io/docs",  # Specific known domains
            f"qdrant.tech/documentation",
            f"weaviate.io/developers",
            f"zilliz.com",
            f"pinecone.io/docs",
            f"mongodb.com/docs/atlas/vector-search",
            f"redis.io/docs",
            f"elastic.co/guide",
            f"clickhouse.com/docs",
            f"chromadb.com",
            f"docs.trychroma.com",
        ]
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in official_patterns)

    def _fetch_documentation(self, db_info: DBInfo) -> str:
        """Fetch actual documentation using Local Library or Deep Crawl4AI."""
        print(f"[Agent 0] Fetching real documentation for {db_info.db_name} {db_info.version}...")

        # Check if local JSONL documentation library is requested
        docs_source = self.config.get("docs.source", default="auto")
        if docs_source == "local_jsonl":
            local_path = self.config.get("docs.local_jsonl_path", default=".trae/cache/milvus_io_docs_depth3.jsonl")
            print(f"[Agent 0] Using local documentation library: {local_path}")
            print(f"[Agent 0] AUTO-CRAWL and DOCUMENT-CACHE DISABLED")
            
            library = LocalDocsLibrary(local_path)
            docs_context = library.load_docs_context()
            
            if not docs_context.strip():
                raise RuntimeError(f"Local documentation library is empty or all items were filtered out: {local_path}")
                
            return docs_context

        # Check for cached documentation from previous runs
        import glob
        cache_files = glob.glob(os.path.join(self.runs_dir, "*", "raw_docs.json"))
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if cached_data.get('db_name') == db_info.db_name and cached_data.get('version') == db_info.version:
                        print(f"[Agent 0] Using cached documentation from: {os.path.basename(os.path.dirname(cache_file))}")
                        return cached_data.get('full_docs', '')
            except Exception as e:
                print(f"[Agent 0] Failed to read cache file {cache_file}: {e}")
                continue

        docs_context = ""
        try:
            deep_crawler = DeepCrawler(
                max_depth=3,
                page_timeout=30,
                total_timeout=600,
                max_pages=100
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
            print(f"[Agent 0] Failed to fetch real documentation: {e}")
            raise RuntimeError(f"Documentation fetching failed: {e}")

        return docs_context

    def _filter_docs(self, docs_content: str, config) -> tuple:
        """
        Filter crawled documents by version and quality.

        Args:
            docs_content: Raw markdown content from crawling
            config: DocsConfig with filter settings

        Returns:
            (filtered_content, stats_dict)

        Filter rules:
        - Version match: Only keep URLs containing /docs/v{allowed_version}
        - Quality: Each document section should have at least min_chars characters
        - Path: Only keep /docs or /docs/zh paths
        """
        logger.info("[Preprocess] Starting document filtering...")

        # Extract filter settings from config
        allowed_versions = getattr(config, 'allowed_versions', ['2.6'])
        min_chars = getattr(config, 'min_chars', 500)

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

            # Rule 1: Path filter - only keep /docs or /docs/zh paths
            parsed_url = urlparse(url)
            path_lower = parsed_url.path.lower()
            if '/docs/' not in path_lower and path_lower != '/docs':
                stats["filtered_out_path"] += 1
                logger.debug(f"[Preprocess] Filtered out (path): {url}")
                continue

            # Rule 2: Version filter - check for allowed version patterns
            version_match_found = False
            for ver in allowed_versions:
                # Match patterns like /docs/v2.6/ or /docs/v2.4.x/
                pattern = f'/docs/v{re.escape(ver)}'
                if pattern in path_lower:
                    version_match_found = True
                    break
                # Also allow URLs that don't have an explicit version (e.g., /docs/ root)
                if path_lower.rstrip('/') in ('/docs', '/docs/', '/docs/zh', '/docs/zh/'):
                    version_match_found = True
                    break

            if not version_match_found and allowed_versions:
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

    def _validate_docs(self, filtered_content: str, config) -> dict:
        """
        Validate document library quality.

        Args:
            filtered_content: Filtered document content
            config: DocsConfig with validation settings

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
        - Required keywords exist in content
        - Total chars > 1M (for meaningful corpus)
        """
        logger.info("[Preprocess] Starting document validation...")

        # Extract validation settings from config
        min_docs = getattr(config, 'min_docs', 50)
        required_keywords = getattr(config, 'required_docs', ['index-explained', 'single-vector-search', 'multi-vector-search'])

        issues = []
        warnings = []

        # Count documents (sections starting with "Source:")
        doc_count = len(re.findall(r'^Source:', filtered_content, re.MULTILINE))
        total_chars = len(filtered_content)

        # Check 1: Minimum document count
        if doc_count < min_docs:
            issues.append(
                f"Document count ({doc_count}) below minimum threshold ({min_docs})"
            )
        else:
            logger.debug(f"[Preprocess] Doc count OK: {doc_count} >= {min_docs}")

        # Check 2: Required keywords presence
        missing_keywords = []
        for keyword in required_keywords:
            if keyword.lower() not in filtered_content.lower():
                missing_keywords.append(keyword)

        if missing_keywords:
            issues.append(
                f"Missing required keywords: {missing_keywords}"
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
        logger.info(f"[Preprocess] Saving docs cache to: {cache_path}")

        try:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Check if content looks like it's already structured with Source: markers
            # If so, split into individual records; otherwise wrap as single record
            sections = re.split(r'(?=^Source:)', content, flags=re.MULTILINE)

            with open(cache_file, 'w', encoding='utf-8') as f:
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

                    f.write(json.dumps(record, ensure_ascii=False) + '\n')

            cache_size_kb = cache_file.stat().st_size / 1024
            logger.info(f"[Preprocess] Cache saved: {cache_path} ({cache_size_kb:.1f}KB, {len([s for s in sections if s.strip()])} records)")

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

    def _preprocess_docs(self, raw_docs: str, state: WorkflowState) -> str:
        """
        Main preprocessing pipeline: filter -> validate -> cache.

        Args:
            raw_docs: Raw crawled document content
            state: Current workflow state (contains config)

        Returns:
            Processed document content ready for use
        """
        logger.info("[Preprocess] === Starting Document Preprocessing Pipeline ===")

        # Load DocsConfig from AppConfig
        from src.config import get_config
        app_config = get_config()
        docs_config = app_config.docs

        # Step 1: Filter documents
        logger.info("[Preprocess] [Step 1/3] Filtering documents...")
        filtered_content, filter_stats = self._filter_docs(raw_docs, docs_config)

        # Step 2: Validate document library quality
        logger.info("[Preprocess] [Step 2/3] Validating document library...")
        validation_result = self._validate_docs(filtered_content, docs_config)

        # Store validation result on state for downstream consumers
        state.docs_validation = validation_result

        # Log warning if validation did not pass but still proceed
        if not validation_result["passed"]:
            logger.warning(
                f"[Preprocess] Validation FAILED but proceeding with available content. "
                f"Issues: {validation_result['issues']}"
            )

        # Step 3: Save to cache
        logger.info("[Preprocess] [Step 3/3] Saving to JSONL cache...")
        cache_path = docs_config.local_jsonl_path
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
                            "MINIO_ACCESS_KEY=minioadmin",
                            "MINIO_SECRET_KEY=minioadmin"
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
                        "image": f"milvusdb/milvus:{db_info.version}",
                        "command": ["milvus", "run", "standalone"],
                        "environment": [
                            "ETCD_ENDPOINTS=etcd:2379",
                            "MINIO_ADDRESS=minio:9000"
                        ],
                        "ports": ["19530:19530", "9091:9091"],
                        "depends_on": ["etcd", "minio"]
                    }
                }
            }
            endpoint = "localhost:19530"
            credentials = {"user": "root", "password": ""}
            
        elif db_info.db_name == "qdrant":
            # Qdrant standalone template
            compose_content = {
                "version": "3",
                "services": {
                    "qdrant": {
                        "container_name": f"qdrant-{run_id}",
                        "image": f"qdrant/qdrant:{db_info.version}",
                        "ports": ["6333:6333", "6334:6334"]
                    }
                }
            }
            endpoint = "localhost:6333"
            credentials = {"api_key": ""}
            
        else:
            raise ValueError(f"Unsupported database: {db_info.db_name}")

        # Write to file
        with open(compose_file_path, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False)
            
        return compose_file_path, endpoint, credentials

    def _spin_up_sandbox(self, db_info: DBInfo, compose_file: str, endpoint: str) -> bool:
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
            if result == 0:
                print(f"[Agent 0] Hot sandbox detected on {endpoint}. Reusing environment.")
                return True
                
        # If not hot, cold start
        run_dir = os.path.dirname(compose_file)
        print(f"[Agent 0] No hot sandbox found. Cold starting Docker environment in {run_dir}...")
        try:
            subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=run_dir,
                check=True,
                capture_output=True
            )
            # Add a small delay to let services initialize
            import time
            time.sleep(5)
            return True
        except Exception as e:
            print(f"[Agent 0] Error: Docker compose failed or docker not running: {e}.")
            raise RuntimeError(f"Failed to spin up Docker environment: {e}")

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
        print(f"[Agent 0] Parsed target DB: {db_info.db_name}, Version: {db_info.version} (Tokens: {tokens_used})")
        
        # Step 2: Fetch Real Documentation (with cache-first strategy + preprocessing pipeline)
        docs_context = ""
        cache_hit = False

        # 2a: Try loading from JSONL cache first
        from src.config import get_config as _get_app_config
        app_config = _get_app_config()
        docs_config = app_config.docs
        cache_path = docs_config.local_jsonl_path
        ttl_days = getattr(docs_config, 'cache_ttl_days', 7)

        cached_content = self._load_docs_cache(cache_path, ttl_days=ttl_days)
        if cached_content is not None:
            logger.info("[Agent 0] Cache HIT - using cached documents, skipping crawl")
            docs_context = cached_content
            cache_hit = True

            # Run validation on cached content to populate docs_validation on state
            validation_result = self._validate_docs(docs_context, docs_config)
            state.docs_validation = validation_result
            logger.info(
                f"[Agent 0] Cached docs validation: "
                f"{'PASS' if validation_result['passed'] else 'FAIL'} "
                f"(docs={validation_result['total_docs']}, chars={validation_result['total_chars']:,})"
            )
        else:
            # 2b: Cache miss - perform full fetch then preprocess
            logger.info("[Agent 0] Cache MISS - performing full documentation fetch")
            raw_docs = self._fetch_documentation(db_info)
            
            # Run preprocessing pipeline: filter -> validate -> cache
            docs_context = self._preprocess_docs(raw_docs, state)
        
        print(f"[Agent 0] Fetched real documentation for {db_info.db_name} (cache={'HIT' if cache_hit else 'MISS'})")
        
        # Step 3: Spin up Environment
        try:
            compose_file, endpoint, credentials = self._generate_docker_compose(db_info, state.run_id)
            print(f"[Agent 0] Generated compose file at: {compose_file}")
            
            # Use the new sandbox pool method
            success = self._spin_up_sandbox(db_info, compose_file, endpoint)
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
