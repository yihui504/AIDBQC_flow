from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WebSearchResult(BaseModel):
    query: str
    results: list[dict] = []
    total: int = 0


class WebSearcher:
    def search_web(self, query: str, max_results: int = 5) -> WebSearchResult:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                formatted = []
                for r in results:
                    formatted.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")[:300],
                    })
                return WebSearchResult(query=query, results=formatted, total=len(formatted))
        except ImportError:
            logger.warning("duckduckgo-search not installed")
            return WebSearchResult(query=query)
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return WebSearchResult(query=query)

    async def crawl_url(self, url: str) -> Optional[str]:
        try:
            from crawl4ai import AsyncWebCrawler
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                return result.markdown if result else None
        except ImportError:
            logger.warning("crawl4ai not installed")
            return None
        except Exception as e:
            logger.warning(f"Crawl failed for {url}: {e}")
            return None

    def crawl_url_sync(self, url: str) -> Optional[str]:
        try:
            import asyncio
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.crawl_url(url))
                    return future.result(timeout=120)
            else:
                return asyncio.run(self.crawl_url(url))
        except Exception as e:
            logger.warning(f"Sync crawl failed for {url}: {e}")
            return None
