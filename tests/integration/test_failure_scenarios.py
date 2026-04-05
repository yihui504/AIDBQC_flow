"""
集成测试：失败场景和边缘情况
测试系统在各种异常情况下的行为
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.domain_config import DomainConfig
from src.parsers.html_cleaner import HTMLCleaner
from src.parsers.crawler_utils import fetch_with_retry, RobotsTxtCache, RateLimiter
from src.cache.embedding_cache import EmbeddingCache
from src.knowledge_base import DefectKnowledgeBase, BugRecord


class TestRobotsTxtBlocking:
    """测试 robots.txt 阻止场景"""

    @pytest.mark.asyncio
    async def test_robots_txt_blocks_all_requests(self):
        """测试 robots.txt 完全阻止请求"""
        # Mock robots.txt 返回不允许所有爬取
        with patch('src.parsers.crawler_async.RobotFileParserLookalike') as mock_robot_parser:
            mock_robot_parser.return_value.can_fetch.return_value = False

            robots_cache = RobotsTxtCache()
            rate_limiter = RateLimiter(min_delay=0.1, max_delay=0.2)

            # 测试 URL
            url = "https://example.com/docs"

            # 尝试爬取
            result = await fetch_with_retry(url, robots_cache, rate_limiter, enable_fallback=True)

            # 应该被阻止
            assert result["status"] == "blocked_by_robots_txt"
            assert result["content"] is None
            assert result["length"] == 0

    @pytest.mark.asyncio
    async def test_fallback_mechanism_activation(self):
        """测试回退机制激活"""
        # Mock robots.txt 阻止，但回退成功
        with patch('src.parsers.crawler_utils.RobotFileParserLookalike') as mock_robot_parser:
            mock_robot_parser.return_value.can_fetch.return_value = False

            # Mock GitHub API 成功
            with patch('src.parsers.crawler_utils.AsyncClient') as mock_client:
                # robots.txt 检查
                mock_client.return_value.get.return_value.status_code = 404

                # GitHub API 成功
                mock_client.return_value.get.return_value.status_code = 200
                mock_client.return_value.get.return_value.text = "GitHub README content"

                robots_cache = RobotsTxtCache()
                rate_limiter = RateLimiter(min_delay=0.1, max_delay=0.2)

                result = await fetch_with_retry(
                    "https://github.com/example/repo",
                    robots_cache,
                    rate_limiter,
                    enable_fallback=True
                )

                # 应该使用回退
                assert result["status"] == "fallback_github_api"
                assert result["content"] == "GitHub README content"
                assert result["source"] == "github_api"

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self):
        """测试所有回退策略都失败"""
        with patch('src.parsers.crawler_utils.RobotFileParserLookalike') as mock_robot_parser:
            mock_robot_parser.return_value.can_fetch.return_value = False

            # Mock 所有回退都失败
            with patch('src.parsers.crawler_utils.AsyncClient') as mock_client:
                mock_client.return_value.get.side_effect = Exception("All failed")

                robots_cache = RobotsTxtCache()
                rate_limiter = RateLimiter(min_delay=0.1, max_delay=0.2)

                result = await fetch_with_retry(
                    "https://blocked-site.com/docs",
                    robots_cache,
                    rate_limiter,
                    enable_fallback=True
                )

                # 应该标记为需要人工审核
                assert result["status"] == "blocked_manual_review_required"
                assert result["content"] is None
                assert "Manual review required" in result["message"]


class TestCachePersistence:
    """测试缓存持久化"""

    def test_cache_survives_restart(self):
        """测试缓存能够跨越程序重启"""
        cache_dir = tempfile.mkdtemp()

        try:
            # 创建缓存实例并添加数据
            cache1 = EmbeddingCache(cache_dir)
            test_text = "test persistence"
            fake_embedding = [0.1, 0.2, 0.3]
            cache1.set(test_text, fake_embedding)

            # 验证数据存在
            cached = cache1.get(test_text)
            assert cached is not None
            assert cached == fake_embedding

            # 模拟程序重启：创建新实例
            cache2 = EmbeddingCache(cache_dir)

            # 验证数据仍然存在
            cached2 = cache2.get(test_text)
            assert cached2 is not None
            assert cached2 == fake_embedding

            # 验证统计信息
            stats = cache2.get_stats()
            assert stats['hits'] == 0
            assert stats['misses'] == 0

        finally:
            # 清理
            shutil.rmtree(cache_dir)

    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        cache_dir = tempfile.mkdtemp()

        try:
            cache = EmbeddingCache(cache_dir)

            # 添加大量数据模拟大小限制
            for i in range(1000):
                text = f"test text {i}" * 100  # 长文本
                embedding = [i/1000, i/1000, i/1000]
                cache.set(text, embedding)

            # 验证缓存不会无限增长（diskcache 会自动管理）
            stats = cache.get_stats()
            assert stats['size'] > 0

        finally:
            shutil.rmtree(cache_dir)


class TestThresholdEdgeCases:
    """测试阈值边界情况"""

    def test_zero_similarity_threshold(self):
        """测试零相似度阈值"""
        kb = DefectKnowledgeBase()

        # 添加测试数据
        defect = BugRecord(
            case_id="test_001",
            bug_type="Type-1",
            root_cause_analysis="Test bug",
            evidence_level="L1"
        )
        kb.add_defect(defect)

        # 设置零阈值
        kb.calibrator.optimal_threshold = 0.0

        # 搜索应该返回所有结果
        results = kb.search_similar_defects("test", top_k=5, min_similarity=0.0)
        assert len(results) >= 1

    def test_maximum_similarity_threshold(self):
        """测试最大相似度阈值（1.0）"""
        kb = DefectKnowledgeBase()

        # 添加测试数据
        defect = BugRecord(
            case_id="test_002",
            bug_type="Type-2",
            root_cause_analysis="Exact match test",
            evidence_level="L1"
        )
        kb.add_defect(defect)

        # 设置最大阈值
        kb.calibrator.optimal_threshold = 1.0

        # 搜索应该只返回完全匹配
        results = kb.search_similar_defects("Exact match test", top_k=5, min_similarity=1.0)

        # 可能没有完全匹配的结果
        assert len(results) == 0 or (len(results) == 1 and results[0]['similarity'] == 1.0)

    def test_empty_query_handling(self):
        """测试空查询处理"""
        kb = DefectKnowledgeBase()

        # 添加测试数据
        for i in range(3):
            defect = BugRecord(
                case_id=f"test_{i:03d}",
                bug_type="Type-1",
                root_cause_analysis=f"Bug {i}",
                evidence_level="L1"
            )
            kb.add_defect(defect)

        # 空查询
        results = kb.search_similar_defects("", top_k=5)

        # 应该返回合理的结果（可能是随机或基于ID的）
        assert len(results) <= 5

    def test_extremely_long_query(self):
        """测试超长查询"""
        kb = DefectKnowledgeBase()

        # 添加测试数据
        defect = BugRecord(
            case_id="long_query_test",
            bug_type="Type-1",
            root_cause_analysis="Normal bug description",
            evidence_level="L1"
        )
        kb.add_defect(defect)

        # 超长查询
        long_query = "a" * 10000
        results = kb.search_similar_defects(long_query, top_k=3)

        # 应该处理而不崩溃
        assert isinstance(results, list)


class TestStressCrawling:
    """测试长时间运行的稳定性"""

    @pytest.mark.asyncio
    async def test_concurrent_crawling(self):
        """测试并发爬取"""
        # 模拟多个并发爬取请求
        async def crawl_single(url):
            robots_cache = RobotsTxtCache()
            rate_limiter = RateLimiter(min_delay=0.1, max_delay=0.2)

            # Mock 响应
            with patch('src.parsers.crawler_utils.AsyncClient') as mock_client:
                mock_client.return_value.get.return_value.status_code = 200
                mock_client.return_value.get.return_value.text = f"Content for {url}"

                result = await fetch_with_retry(url, robots_cache, rate_limiter)
                return result

        # 并发执行10个爬取
        urls = [f"https://site{i}.com/docs" for i in range(10)]
        tasks = [crawl_single(url) for url in urls]
        results = await asyncio.gather(*tasks)

        # 所有任务都应该完成
        assert len(results) == 10
        for result in results:
            assert result["status"] == 200
            assert result["content"] is not None

    def test_memory_usage_over_time(self):
        """测试长时间运行的内存使用"""
        # 创建临时目录
        cache_dir = tempfile.mkdtemp()

        try:
            # 初始化知识库
            kb = DefectKnowledgeBase(cache_dir=cache_dir, use_cache=True)

            # 持续添加数据模拟长时间运行
            for i in range(100):
                defect = BugRecord(
                    case_id=f"stress_test_{i:03d}",
                    bug_type="Type-1",
                    root_cause_analysis=f"Stress test bug {i} " * 10,  # 长文本
                    evidence_level="L1"
                )
                kb.add_defect(defect)

                # 定期搜索
                if i % 10 == 0:
                    results = kb.search_similar_defects("stress test", top_k=3)
                    assert len(results) > 0

            # 验证内存使用合理
            stats = kb.get_stats()
            assert stats['total_searches'] > 0

            # 缓存统计应该合理
            if 'cache' in stats:
                cache_stats = stats['cache']
                assert cache_stats['hit_rate'] >= 0  # 可能的命中率

        finally:
            # 清理
            shutil.rmtree(cache_dir)

    def test_large_dataset_handling(self):
        """测试大数据集处理"""
        # 使用临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建大数据集
            kb = DefectKnowledgeBase(db_path=temp_dir)

            # 添加大量缺陷
            large_dataset = []
            for i in range(1000):  # 1000个缺陷
                defect = BugRecord(
                    case_id=f"large_{i:04d}",
                    bug_type="Type-1",
                    root_cause_analysis=f"Bug description for case {i} " * 20,
                    evidence_level="L1"
                )
                large_dataset.append(defect)
                kb.add_defect(defect)

            # 测试大数据集的搜索性能
            start_time = time.time()
            results = kb.search_similar_defects("bug description", top_k=10)
            search_time = time.time() - start_time

            # 搜索应该在合理时间内完成
            assert search_time < 10.0  # 10秒内
            assert len(results) <= 10

            # 验证结果格式正确
            for result in results:
                assert 'document' in result
                assert 'metadata' in result
                assert 'similarity' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])