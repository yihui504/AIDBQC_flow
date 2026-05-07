"""
Persistent Collection Pool Implementation

This module implements a collection pooling mechanism that:
1. Pre-creates collections for common dimensions
2. Uses logical deletion instead of physical deletion
3. Provides concurrent-safe operations
4. Automatically reclaims old collections

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
import time
import random
import string
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CollectionStatus(Enum):
    """Status of a pooled collection."""
    INITIALIZING = "initializing"
    AVAILABLE = "available"
    IN_USE = "in_use"
    MARKED_FOR_DELETION = "marked_for_deletion"
    EXPIRED = "expired"


@dataclass
class PooledCollection:
    """
    Represents a single collection in the pool.

    Attributes:
        name: Unique collection name
        dimension: Vector dimension
        metric_type: Distance metric (L2, IP, COSINE)
        status: Current status
        created_at: Creation timestamp
        last_used_at: Last usage timestamp
        usage_count: Number of times this collection was used
        is_deleted: Logical deletion flag
    """
    name: str
    dimension: int
    metric_type: str = "L2"
    status: CollectionStatus = CollectionStatus.INITIALIZING
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    is_deleted: bool = False

    @property
    def age_seconds(self) -> int:
        """Age of the collection in seconds."""
        return int((datetime.now() - self.created_at).total_seconds())

    @property
    def idle_seconds(self) -> int:
        """Idle time since last use in seconds."""
        return int((datetime.now() - self.last_used_at).total_seconds())

    def mark_in_use(self) -> None:
        """Mark collection as in use and update last_used_at."""
        self.status = CollectionStatus.IN_USE
        self.last_used_at = datetime.now()
        self.usage_count += 1

    def mark_available(self) -> None:
        """Mark collection as available."""
        self.status = CollectionStatus.AVAILABLE

    def mark_for_deletion(self) -> None:
        """Mark collection for logical deletion."""
        self.is_deleted = True
        self.status = CollectionStatus.MARKED_FOR_DELETION

    def is_expired(self, max_idle_seconds: int) -> bool:
        """Check if collection has expired due to inactivity."""
        return (
            self.idle_seconds > max_idle_seconds
            and self.status == CollectionStatus.AVAILABLE
        )


@dataclass
class CollectionPoolConfig:
    """Configuration for the collection pool."""
    # Pool size limits
    min_pool_size: int = 3
    max_pool_size: int = 10

    # Collection lifecycle
    collection_ttl_seconds: int = 3600  # 1 hour
    max_idle_seconds: int = 1800  # 30 minutes

    # Cleanup settings
    cleanup_interval_seconds: int = 300  # 5 minutes
    enable_auto_cleanup: bool = True

    # Retry settings
    max_init_retries: int = 3
    init_retry_delay_seconds: float = 1.0

    # Name generation
    name_prefix: str = "pool_"
    name_suffix_length: int = 8


class PersistentCollectionPool:
    """
    Thread-safe collection pool for vector databases.

    This class manages a pool of pre-created collections that can be reused
    across test runs, eliminating Type-2 environmental noise from frequent
    collection creation/deletion.

    Usage Example:
        ```python
        pool = PersistentCollectionPool(
            adapter=milvus_adapter,
            config=CollectionPoolConfig(min_pool_size=3)
        )
        await pool.initialize()

        # Acquire a collection for dimension 128
        collection = await pool.acquire(dimension=128)
        # Use the collection...
        await pool.release(collection.name)
        ```
    """

    def __init__(self, adapter, config: Optional[CollectionPoolConfig] = None):
        """
        Initialize the collection pool.

        Args:
            adapter: VectorDBAdapter instance (MilvusAdapter, QdrantAdapter, etc.)
            config: Pool configuration (uses defaults if None)
        """
        self.adapter = adapter
        self.config = config or CollectionPoolConfig()

        # Pool storage: dimension -> list of PooledCollection
        self._pools: Dict[int, List[PooledCollection]] = {}

        # Tracking
        self._all_collections: Dict[str, PooledCollection] = {}
        self._dimensions_in_pool: Set[int] = set()

        # Concurrency control
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

        # Status
        self._is_initialized = False
        self._is_shutting_down = False

        logger.info(f"[CollectionPool] Created pool with config: {self.config}")

    async def initialize(self) -> None:
        """
        Initialize the pool with pre-created collections.

        This method creates the minimum number of collections for common
        dimensions. Should be called before using the pool.
        """
        async with self._lock:
            if self._is_initialized:
                logger.warning("[CollectionPool] Already initialized")
                return

            logger.info("[CollectionPool] Starting initialization...")
            start_time = time.time()

            # Pre-create collections for common dimensions
            # Start with dimension 128 as default
            await self._ensure_pool_for_dimension(128)

            # Start cleanup task if enabled
            if self.config.enable_auto_cleanup:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.info("[CollectionPool] Cleanup task started")

            self._is_initialized = True
            elapsed = time.time() - start_time
            logger.info(f"[CollectionPool] Initialization complete in {elapsed:.2f}s")

    async def shutdown(self) -> None:
        """
        Shutdown the pool and cleanup resources.

        This method stops the cleanup task and optionally physically deletes
        all pooled collections.
        """
        async with self._lock:
            if self._is_shutting_down:
                return

            logger.info("[CollectionPool] Starting shutdown...")
            self._is_shutting_down = True

            # Stop cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
                logger.info("[CollectionPool] Cleanup task stopped")

            # Optionally drop all collections (commented out for safety)
            # await self._drop_all_collections()

            self._is_initialized = False
            logger.info("[CollectionPool] Shutdown complete")

    async def acquire(self, dimension: int, metric_type: str = "L2",
                     timeout_seconds: float = 30.0) -> PooledCollection:
        """
        Acquire a collection from the pool.

        Args:
            dimension: Vector dimension
            metric_type: Distance metric type
            timeout_seconds: Maximum time to wait for available collection

        Returns:
            PooledCollection that is ready to use

        Raises:
            RuntimeError: If pool is not initialized
            asyncio.TimeoutError: If no collection available within timeout
        """
        if not self._is_initialized:
            raise RuntimeError("Pool not initialized. Call initialize() first.")

        # Ensure pool exists for this dimension
        await self._ensure_pool_for_dimension(dimension)

        start_time = time.time()
        while True:
            async with self._lock:
                # Try to find an available collection
                for collection in self._pools.get(dimension, []):
                    if (collection.status == CollectionStatus.AVAILABLE
                            and not collection.is_deleted
                            and collection.dimension == dimension
                            and collection.metric_type == metric_type):
                        collection.mark_in_use()
                        logger.debug(
                            f"[CollectionPool] Acquired {collection.name} "
                            f"(usage #{collection.usage_count})"
                        )
                        return collection

            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise asyncio.TimeoutError(
                    f"No available collection for dimension={dimension} "
                    f"within {timeout_seconds}s"
                )

            # Wait a bit before retrying
            await asyncio.sleep(0.1)

    async def release(self, collection_name: str) -> None:
        """
        Release a collection back to the pool.

        This performs logical cleanup (clears data) but does not drop
        the collection.

        Args:
            collection_name: Name of collection to release
        """
        async with self._lock:
            collection = self._all_collections.get(collection_name)
            if collection is None:
                logger.warning(f"[CollectionPool] Unknown collection: {collection_name}")
                return

            # Perform logical cleanup: clear data but keep collection
            try:
                await self._clear_collection_data(collection)
                logger.debug(f"[CollectionPool] Cleared data from {collection_name}")
            except Exception as e:
                logger.error(f"[CollectionPool] Failed to clear {collection_name}: {e}")

            # Mark as available
            collection.mark_available()
            logger.debug(f"[CollectionPool] Released {collection_name}")

    async def mark_for_deletion(self, collection_name: str) -> None:
        """
        Mark a collection for logical deletion.

        The collection is not immediately dropped; it will be cleaned up
        during the next cleanup cycle.

        Args:
            collection_name: Name of collection to mark for deletion
        """
        async with self._lock:
            collection = self._all_collections.get(collection_name)
            if collection:
                collection.mark_for_deletion()
                logger.info(f"[CollectionPool] Marked for deletion: {collection_name}")

    async def get_status(self) -> Dict:
        """
        Get current pool status.

        Returns:
            Dictionary with pool statistics
        """
        async with self._lock:
            total = len(self._all_collections)
            available = sum(
                1 for c in self._all_collections.values()
                if c.status == CollectionStatus.AVAILABLE and not c.is_deleted
            )
            in_use = sum(
                1 for c in self._all_collections.values()
                if c.status == CollectionStatus.IN_USE
            )
            marked_for_deletion = sum(
                1 for c in self._all_collections.values()
                if c.is_deleted
            )

            return {
                "total_collections": total,
                "available": available,
                "in_use": in_use,
                "marked_for_deletion": marked_for_deletion,
                "dimensions_supported": list(self._dimensions_in_pool),
                "is_initialized": self._is_initialized,
            }

    # ========================================================================
    # Private Methods
    # ========================================================================

    async def _ensure_pool_for_dimension(self, dimension: int) -> None:
        """
        Ensure minimum pool size for a specific dimension.

        Creates new collections if needed to meet min_pool_size.
        """
        if dimension in self._dimensions_in_pool:
            return

        logger.info(f"[CollectionPool] Creating pool for dimension {dimension}")

        # Create minimum number of collections
        for i in range(self.config.min_pool_size):
            await self._create_and_add_collection(dimension)

        self._dimensions_in_pool.add(dimension)
        logger.info(
            f"[CollectionPool] Pool ready for dimension {dimension} "
            f"({self.config.min_pool_size} collections)"
        )

    async def _create_and_add_collection(
        self, dimension: int, metric_type: str = "L2"
    ) -> Optional[PooledCollection]:
        """
        Create a new collection and add it to the pool.

        Args:
            dimension: Vector dimension
            metric_type: Distance metric type

        Returns:
            PooledCollection if successful, None otherwise
        """
        name = self._generate_collection_name(dimension)

        for attempt in range(self.config.max_init_retries):
            try:
                # Use adapter to create collection
                success = self.adapter.initialize_collection(
                    collection_name=name,
                    dimension=dimension,
                    metric_type=metric_type
                )

                if success:
                    collection = PooledCollection(
                        name=name,
                        dimension=dimension,
                        metric_type=metric_type,
                        status=CollectionStatus.AVAILABLE
                    )

                    # Add to pool
                    if dimension not in self._pools:
                        self._pools[dimension] = []
                    self._pools[dimension].append(collection)
                    self._all_collections[name] = collection

                    logger.info(
                        f"[CollectionPool] Created {name} "
                        f"(dim={dimension}, attempt={attempt + 1})"
                    )
                    return collection

            except Exception as e:
                logger.warning(
                    f"[CollectionPool] Failed to create {name} "
                    f"(attempt {attempt + 1}): {e}"
                )
                if attempt < self.config.max_init_retries - 1:
                    await asyncio.sleep(self.config.init_retry_delay_seconds)

        logger.error(f"[CollectionPool] Failed to create collection after {self.config.max_init_retries} attempts")
        return None

    async def _clear_collection_data(self, collection: PooledCollection) -> bool:
        """
        Clear all data from a collection without dropping it.

        This implements the logical deletion concept.

        Args:
            collection: PooledCollection to clear

        Returns:
            True if successful, False otherwise
        """
        try:
            # For Milvus, we need to delete all entities
            if hasattr(self.adapter, '_delete_all_entities'):
                return await self.adapter._delete_all_entities(collection.name)

            # Generic approach: insert empty data or use adapter-specific method
            # This is a placeholder - actual implementation depends on adapter
            logger.debug(f"[CollectionPool] Data clear for {collection.name} (adapter-specific)")
            return True

        except Exception as e:
            logger.error(f"[CollectionPool] Failed to clear {collection.name}: {e}")
            return False

    async def _cleanup_loop(self) -> None:
        """
        Background task that periodically cleans up expired collections.
        """
        while not self._is_shutting_down:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CollectionPool] Cleanup loop error: {e}")

    async def _cleanup_expired(self) -> None:
        """
        Clean up expired and marked-for-deletion collections.
        """
        async with self._lock:
            now = datetime.now()
            to_remove: List[str] = []

            for name, collection in self._all_collections.items():
                # Check if marked for deletion
                if collection.is_deleted:
                    to_remove.append(name)
                    continue

                # Check if expired
                if collection.is_expired(self.config.max_idle_seconds):
                    collection.status = CollectionStatus.EXPIRED
                    to_remove.append(name)

            # Remove expired collections from pool
            for name in to_remove:
                await self._remove_collection(name)

            if to_remove:
                logger.info(f"[CollectionPool] Cleaned up {len(to_remove)} collections")

    async def _remove_collection(self, name: str) -> None:
        """
        Remove a collection from the pool.

        Args:
            name: Collection name to remove
        """
        if name not in self._all_collections:
            return

        collection = self._all_collections[name]

        # Remove from dimension-specific pool
        if collection.dimension in self._pools:
            self._pools[collection.dimension] = [
                c for c in self._pools[collection.dimension]
                if c.name != name
            ]

        # Remove from tracking
        del self._all_collections[name]

        logger.debug(f"[CollectionPool] Removed {name} from pool")

    def _generate_collection_name(self, dimension: int) -> str:
        """
        Generate a unique collection name.

        Format: {prefix}dim{dimension}_{random_suffix}

        Args:
            dimension: Vector dimension

        Returns:
            Unique collection name
        """
        suffix = ''.join(
            random.choices(string.ascii_lowercase + string.digits,
                          k=self.config.name_suffix_length)
        )
        return f"{self.config.name_prefix}dim{dimension}_{suffix}"

    async def _drop_all_collections(self) -> None:
        """
        Physically drop all collections in the pool.

        WARNING: This is irreversible. Use with caution.
        """
        logger.warning("[CollectionPool] Dropping all pooled collections...")

        for name in list(self._all_collections.keys()):
            try:
                if hasattr(self.adapter, 'teardown_harness'):
                    self.adapter.teardown_harness(name)
                logger.debug(f"[CollectionPool] Dropped {name}")
            except Exception as e:
                logger.error(f"[CollectionPool] Failed to drop {name}: {e}")

        self._pools.clear()
        self._all_collections.clear()
        self._dimensions_in_pool.clear()


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_pool(adapter, config: Optional[CollectionPoolConfig] = None) -> PersistentCollectionPool:
    """
    Create and initialize a collection pool.

    Args:
        adapter: VectorDBAdapter instance
        config: Pool configuration

    Returns:
        Initialized PersistentCollectionPool
    """
    pool = PersistentCollectionPool(adapter, config)
    await pool.initialize()
    return pool
