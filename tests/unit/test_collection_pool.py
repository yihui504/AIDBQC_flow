"""
Unit Tests for PersistentCollectionPool

Test coverage goals:
- PooledCollection dataclass: 100%
- CollectionPoolConfig: 100%
- PersistentCollectionPool core methods: 90%+
- Concurrent operations: 100%
- Edge cases: 80%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.pools.collection_pool import (
    PooledCollection,
    CollectionStatus,
    CollectionPoolConfig,
    PersistentCollectionPool,
    create_pool,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_adapter():
    """Mock vector database adapter."""
    adapter = MagicMock()
    adapter.initialize_collection = MagicMock(return_value=True)
    adapter.teardown_harness = MagicMock(return_value=True)
    return adapter


@pytest.fixture
def pool_config():
    """Test pool configuration."""
    return CollectionPoolConfig(
        min_pool_size=2,
        max_pool_size=5,
        collection_ttl_seconds=60,
        max_idle_seconds=30,
        cleanup_interval_seconds=1,
        enable_auto_cleanup=False,  # Disable for most tests
        max_init_retries=3,
    )


@pytest_asyncio.fixture
async def pool(mock_adapter, pool_config):
    """Create and initialize a test pool."""
    pool = PersistentCollectionPool(mock_adapter, pool_config)
    await pool.initialize()
    yield pool
    await pool.shutdown()


# ============================================================================
# PooledCollection Tests
# ============================================================================

class TestPooledCollection:
    """Tests for PooledCollection dataclass."""

    def test_initialization(self):
        """Test collection initialization with default values."""
        collection = PooledCollection(
            name="test_col",
            dimension=128,
            metric_type="L2"
        )

        assert collection.name == "test_col"
        assert collection.dimension == 128
        assert collection.metric_type == "L2"
        assert collection.status == CollectionStatus.INITIALIZING
        assert collection.usage_count == 0
        assert collection.is_deleted is False

    def test_age_seconds(self):
        """Test age calculation."""
        # Create collection with specific creation time
        past_time = datetime.now() - timedelta(seconds=100)
        collection = PooledCollection(
            name="test_col",
            dimension=128,
            created_at=past_time
        )

        # Age should be approximately 100 seconds
        assert 99 <= collection.age_seconds <= 101

    def test_idle_seconds(self):
        """Test idle time calculation."""
        collection = PooledCollection(name="test_col", dimension=128)

        # Simulate usage 50 seconds ago
        past_time = datetime.now() - timedelta(seconds=50)
        collection.last_used_at = past_time

        assert 49 <= collection.idle_seconds <= 51

    def test_mark_in_use(self):
        """Test marking collection as in use."""
        collection = PooledCollection(name="test_col", dimension=128)
        initial_count = collection.usage_count

        collection.mark_in_use()

        assert collection.status == CollectionStatus.IN_USE
        assert collection.usage_count == initial_count + 1

    def test_mark_available(self):
        """Test marking collection as available."""
        collection = PooledCollection(
            name="test_col",
            dimension=128,
            status=CollectionStatus.IN_USE
        )

        collection.mark_available()

        assert collection.status == CollectionStatus.AVAILABLE

    def test_mark_for_deletion(self):
        """Test marking collection for deletion."""
        collection = PooledCollection(name="test_col", dimension=128)

        collection.mark_for_deletion()

        assert collection.is_deleted is True
        assert collection.status == CollectionStatus.MARKED_FOR_DELETION

    def test_is_expired(self):
        """Test expiration check."""
        collection = PooledCollection(
            name="test_col",
            dimension=128,
            status=CollectionStatus.AVAILABLE  # Must be AVAILABLE for is_expired check
        )

        # Not expired when fresh
        assert collection.is_expired(max_idle_seconds=30) is False

        # Expired when idle too long
        collection.last_used_at = datetime.now() - timedelta(seconds=31)
        assert collection.is_expired(max_idle_seconds=30) is True

        # Not expired if in use (change status back to IN_USE)
        collection.status = CollectionStatus.IN_USE
        assert collection.is_expired(max_idle_seconds=30) is False


# ============================================================================
# CollectionPoolConfig Tests
# ============================================================================

class TestCollectionPoolConfig:
    """Tests for CollectionPoolConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CollectionPoolConfig()

        assert config.min_pool_size == 3
        assert config.max_pool_size == 10
        assert config.collection_ttl_seconds == 3600
        assert config.max_idle_seconds == 1800
        assert config.cleanup_interval_seconds == 300
        assert config.enable_auto_cleanup is True
        assert config.max_init_retries == 3
        assert config.name_prefix == "pool_"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CollectionPoolConfig(
            min_pool_size=5,
            max_pool_size=20,
            enable_auto_cleanup=False
        )

        assert config.min_pool_size == 5
        assert config.max_pool_size == 20
        assert config.enable_auto_cleanup is False


# ============================================================================
# PersistentCollectionPool Tests
# ============================================================================

class TestPersistentCollectionPool:
    """Tests for PersistentCollectionPool."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_adapter, pool_config):
        """Test pool initialization creates minimum collections."""
        pool = PersistentCollectionPool(mock_adapter, pool_config)
        await pool.initialize()

        # Should have created min_pool_size collections for dimension 128
        assert len(pool._all_collections) == pool_config.min_pool_size
        assert 128 in pool._dimensions_in_pool
        assert pool._is_initialized is True

        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_double_initialization(self, pool):
        """Test that double initialization is safe."""
        initial_count = len(pool._all_collections)
        await pool.initialize()

        # Should not create duplicate collections
        assert len(pool._all_collections) == initial_count

    @pytest.mark.asyncio
    async def test_acquire_available_collection(self, pool):
        """Test acquiring an available collection."""
        collection = await pool.acquire(dimension=128)

        assert collection is not None
        assert collection.dimension == 128
        assert collection.status == CollectionStatus.IN_USE
        assert collection.usage_count == 1

    @pytest.mark.asyncio
    async def test_acquire_creates_new_pool(self, mock_adapter, pool_config):
        """Test acquiring for new dimension creates pool."""
        pool = PersistentCollectionPool(mock_adapter, pool_config)
        await pool.initialize()

        # Clear the initial pool to test new dimension
        pool._pools.clear()
        pool._dimensions_in_pool.clear()

        # Acquire for dimension 256 (not in pool)
        collection = await pool.acquire(dimension=256)

        assert collection is not None
        assert collection.dimension == 256
        assert 256 in pool._dimensions_in_pool

        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_acquire_timeout(self, pool):
        """Test acquire timeout when no collections available."""
        # Mark all collections as in use
        for collection in pool._all_collections.values():
            collection.status = CollectionStatus.IN_USE

        with pytest.raises(asyncio.TimeoutError):
            await pool.acquire(dimension=128, timeout_seconds=0.5)

    @pytest.mark.asyncio
    async def test_release_collection(self, pool):
        """Test releasing a collection back to pool."""
        collection = await pool.acquire(dimension=128)
        collection_name = collection.name

        await pool.release(collection_name)

        # Collection should be available again
        released = pool._all_collections[collection_name]
        assert released.status == CollectionStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_mark_for_deletion(self, pool):
        """Test marking collection for deletion."""
        collection = await pool.acquire(dimension=128)
        collection_name = collection.name

        await pool.mark_for_deletion(collection_name)

        # Should be marked for deletion
        marked = pool._all_collections[collection_name]
        assert marked.is_deleted is True
        assert marked.status == CollectionStatus.MARKED_FOR_DELETION

    @pytest.mark.asyncio
    async def test_get_status(self, pool):
        """Test getting pool status."""
        status = await pool.get_status()

        assert "total_collections" in status
        assert "available" in status
        assert "in_use" in status
        assert "dimensions_supported" in status
        assert status["is_initialized"] is True

    @pytest.mark.asyncio
    async def test_concurrent_acquire_release(self, pool):
        """Test concurrent acquire and release operations."""
        results = []

        async def worker(worker_id: int):
            try:
                collection = await pool.acquire(dimension=128, timeout_seconds=5)
                results.append(("acquired", worker_id, collection.name))
                await asyncio.sleep(0.1)  # Simulate work
                await pool.release(collection.name)
                results.append(("released", worker_id, collection.name))
            except Exception as e:
                results.append(("error", worker_id, str(e)))

        # Run 5 concurrent workers
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # All workers should have completed successfully
        assert len([r for r in results if r[0] == "error"]) == 0
        assert len([r for r in results if r[0] == "acquired"]) == 5
        assert len([r for r in results if r[0] == "released"]) == 5

    @pytest.mark.asyncio
    async def test_acquire_before_initialization(self, mock_adapter, pool_config):
        """Test that acquire fails if pool not initialized."""
        pool = PersistentCollectionPool(mock_adapter, pool_config)
        # Don't call initialize()

        with pytest.raises(RuntimeError, match="Pool not initialized"):
            await pool.acquire(dimension=128)


# ============================================================================
# Collection Cleanup Tests
# ============================================================================

class TestCollectionCleanup:
    """Tests for collection cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_collections(self, mock_adapter):
        """Test automatic cleanup of expired collections."""
        config = CollectionPoolConfig(
            min_pool_size=2,
            max_idle_seconds=1,  # 1 second expiration
            cleanup_interval_seconds=0.5,
            enable_auto_cleanup=True
        )

        pool = PersistentCollectionPool(mock_adapter, config)
        await pool.initialize()

        initial_count = len(pool._all_collections)

        # Wait for collections to expire and cleanup to run
        await asyncio.sleep(2)

        final_status = await pool.get_status()
        # Some collections should have been cleaned up
        assert final_status["total_collections"] <= initial_count

        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_logical_deletion_cleanup(self, pool):
        """Test that logically deleted collections are cleaned up."""
        collection = await pool.acquire(dimension=128)
        collection_name = collection.name

        # Mark for deletion
        await pool.mark_for_deletion(collection_name)

        # Trigger cleanup manually
        await pool._cleanup_expired()

        # Collection should be removed
        assert collection_name not in pool._all_collections


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_release_unknown_collection(self, pool):
        """Test releasing an unknown collection (should be safe)."""
        # Should not raise exception
        await pool.release("unknown_collection")

    @pytest.mark.asyncio
    async def test_mark_unknown_for_deletion(self, pool):
        """Test marking unknown collection for deletion."""
        # Should not raise exception
        await pool.mark_for_deletion("unknown_collection")

    @pytest.mark.asyncio
    async def test_shutdown_already_shutdown(self, pool):
        """Test that double shutdown is safe."""
        await pool.shutdown()
        # Should not raise exception
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_collection_name_generation(self, mock_adapter, pool_config):
        """Test that collection names are unique."""
        pool = PersistentCollectionPool(mock_adapter, pool_config)

        names = set()
        for _ in range(100):
            name = pool._generate_collection_name(128)
            names.add(name)

        # All names should be unique
        assert len(names) == 100

        # All names should follow the pattern
        for name in names:
            assert name.startswith("pool_dim128_")
            assert len(name) > len("pool_dim128_")


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance tests for collection pool."""

    @pytest.mark.asyncio
    async def test_acquire_latency_p99(self, pool):
        """Test that P99 acquire latency is under 100ms."""
        latencies = []

        for _ in range(100):
            start = asyncio.get_event_loop().time()
            collection = await pool.acquire(dimension=128)
            end = asyncio.get_event_loop().time()
            latencies.append((end - start) * 1000)  # Convert to ms
            await pool.release(collection.name)

        # Calculate P99
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]

        # P99 should be under 100ms
        assert p99_latency < 100, f"P99 latency {p99_latency:.2f}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_concurrent_throughput(self, pool):
        """Test throughput under concurrent load."""
        num_operations = 50
        start_time = asyncio.get_event_loop().time()

        async def worker():
            for _ in range(10):
                collection = await pool.acquire(dimension=128)
                await asyncio.sleep(0.01)  # Simulate minimal work
                await pool.release(collection.name)

        tasks = [worker() for _ in range(5)]
        await asyncio.gather(*tasks)

        elapsed = asyncio.get_event_loop().time() - start_time
        throughput = num_operations * 10 / elapsed

        # Should handle at least 50 operations per second
        assert throughput > 50


# ============================================================================
# Integration with create_pool
# ============================================================================

class TestCreatePool:
    """Tests for create_pool convenience function."""

    @pytest.mark.asyncio
    async def test_create_pool(self, mock_adapter):
        """Test create_pool convenience function."""
        config = CollectionPoolConfig(
            min_pool_size=2,
            enable_auto_cleanup=False
        )

        pool = await create_pool(mock_adapter, config)

        assert pool._is_initialized is True
        assert len(pool._all_collections) >= 2

        await pool.shutdown()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/pools", "--cov-report=html"])
