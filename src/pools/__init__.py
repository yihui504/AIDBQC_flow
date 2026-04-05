"""
Persistent Collection Pool for AI-DB-QC

This module provides collection pooling to eliminate Type-2 environmental noise
caused by frequent collection creation/deletion cycles.

Core Concepts:
- Pre-created pool: Collections created once, reused across tests
- Logical deletion: Mark collections as deleted, don't actually drop
- Concurrent safety: asyncio.Lock for thread-safe operations
- Automatic cleanup: Background task to reclaim old collections
"""

from .collection_pool import (
    PersistentCollectionPool,
    CollectionPoolConfig,
    PooledCollection,
    CollectionStatus,
)

__all__ = [
    "PersistentCollectionPool",
    "CollectionPoolConfig",
    "PooledCollection",
    "CollectionStatus",
]
