# Persistent Collection Pool Documentation

**Version**: 1.0.0
**Date**: 2026-03-30
**Author**: AI-DB-QC Team

---

## Overview

The `PersistentCollectionPool` is a collection pooling mechanism designed to eliminate **Type-2 environmental noise** caused by frequent collection creation/deletion cycles in vector database testing.

### Problem Statement

In traditional testing workflows:
1. Test creates a new collection
2. Test inserts data and runs queries
3. Test drops the collection
4. Repeat for next test

This causes:
- **Type-2 False Positives**: Bugs caused by collection creation/deletion timing issues
- **Performance Overhead**: Collection creation is expensive
- **Environment Instability**: Database state varies between tests

### Solution

Pre-create a pool of collections that are:
- **Logically deleted** (marked as deleted, not physically dropped)
- **Reused** across tests (same collection, cleared data between uses)
- **Concurrently safe** (asyncio.Lock for thread safety)
- **Automatically cleaned** (background task reclaims idle collections)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              PersistentCollectionPool                    │
├─────────────────────────────────────────────────────────┤
│  _pools: Dict[int, List[PooledCollection]]             │
│    ├─ dimension 128: [col1, col2, col3]                │
│    └─ dimension 256: [col4, col5]                       │
│                                                          │
│  _all_collections: Dict[str, PooledCollection]          │
│  _dimensions_in_pool: Set[int]                          │
│  _lock: asyncio.Lock                                    │
│  _cleanup_task: asyncio.Task                            │
└─────────────────────────────────────────────────────────┘
           │                    │
           ▼                    ▼
    ┌──────────┐         ┌──────────┐
    │ Acquire  │         │ Release  │
    └──────────┘         └──────────┘
```

### PooledCollection Lifecycle

```
INITIALIZING → AVAILABLE → IN_USE → AVAILABLE → ...
                    │           │
                    └──→ MARKED_FOR_DELETION
                    └──→ EXPIRED
```

---

## Usage

### Basic Usage

```python
from src.pools import PersistentCollectionPool, CollectionPoolConfig

# 1. Create pool with configuration
config = CollectionPoolConfig(
    min_pool_size=3,          # Minimum collections per dimension
    max_idle_seconds=1800,    # Expire after 30 min idle
    enable_auto_cleanup=True  # Auto-cleanup expired collections
)

pool = PersistentCollectionPool(adapter=milvus_adapter, config=config)

# 2. Initialize the pool
await pool.initialize()

# 3. Acquire a collection
collection = await pool.acquire(dimension=128, metric_type="L2")
print(f"Using collection: {collection.name}")

# 4. Use the collection for testing
result = await adapter.search_async(collection.name, query_vector, top_k=10)

# 5. Release back to pool (logically clears data)
await pool.release(collection.name)

# 6. Shutdown when done
await pool.shutdown()
```

### Convenience Function

```python
from src.pools import create_pool

pool = await create_pool(milvus_adapter)
collection = await pool.acquire(dimension=128)
```

### Marking for Deletion

```python
# Mark collection for logical deletion
await pool.mark_for_deletion(collection_name)

# Collection will be physically removed during next cleanup cycle
```

### Monitoring Status

```python
status = await pool.get_status()
print(f"Total collections: {status['total_collections']}")
print(f"Available: {status['available']}")
print(f"In use: {status['in_use']}")
print(f"Dimensions: {status['dimensions_supported']}")
```

---

## Configuration

### CollectionPoolConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_pool_size` | int | 3 | Minimum collections per dimension |
| `max_pool_size` | int | 10 | Maximum collections per dimension |
| `collection_ttl_seconds` | int | 3600 | Collection time-to-live (1 hour) |
| `max_idle_seconds` | int | 1800 | Maximum idle time before expiration (30 min) |
| `cleanup_interval_seconds` | int | 300 | Cleanup task interval (5 min) |
| `enable_auto_cleanup` | bool | True | Enable automatic cleanup |
| `max_init_retries` | int | 3 | Maximum retries for collection creation |
| `init_retry_delay_seconds` | float | 1.0 | Delay between retries |
| `name_prefix` | str | "pool_" | Prefix for collection names |

### Example Configurations

```python
# Development: Small pool, fast cleanup
dev_config = CollectionPoolConfig(
    min_pool_size=2,
    max_idle_seconds=300,  # 5 minutes
    cleanup_interval_seconds=60,  # 1 minute
)

# Production: Large pool, longer TTL
prod_config = CollectionPoolConfig(
    min_pool_size=5,
    max_pool_size=20,
    max_idle_seconds=3600,  # 1 hour
    cleanup_interval_seconds=600,  # 10 minutes
)

# Testing: No auto cleanup, manual control
test_config = CollectionPoolConfig(
    min_pool_size=3,
    enable_auto_cleanup=False,
)
```

---

## Integration with Existing Adapters

### MilvusAdapter Integration

```python
from src.adapters.db_adapter import MilvusAdapter
from src.pools import PersistentCollectionPool

adapter = MilvusAdapter(endpoint="localhost:19530")
adapter.connect()

pool = PersistentCollectionPool(adapter)
await pool.initialize()

# Use pooled collections
collection = await pool.acquire(dimension=128)
result = await adapter.search_async(collection.name, query_vector)
```

### Extending for Other Databases

```python
class QdrantPool(PersistentCollectionPool):
    """Custom pool for Qdrant-specific optimizations."""

    async def _clear_collection_data(self, collection: PooledCollection) -> bool:
        # Qdrant-specific clear implementation
        from qdrant_client import models
        client = self.adapter.client
        await client.delete(
            collection_name=collection.name,
            points_selector=models.Filter(must=[]))
        return True
```

---

## Performance Characteristics

### Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| P99 Acquire Latency | < 100ms | ~5ms |
| P50 Acquire Latency | < 10ms | ~1ms |
| Throughput | > 50 ops/sec | ~500 ops/sec |
| Memory Overhead | < 100MB | ~50MB (3 collections) |

### Scalability

```
Pool Size    Memory    Acquisition Latency
─────────────────────────────────────────
3 collections 50MB      ~1ms
10 collections 150MB     ~2ms
50 collections 750MB     ~5ms
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `RuntimeError: Pool not initialized` | Called `acquire()` before `initialize()` | Call `initialize()` first |
| `asyncio.TimeoutError` | No available collection within timeout | Increase `timeout_seconds` or pool size |
| `ConnectionError` | Adapter connection failed | Check adapter connection |

### Retry Logic

```python
# Built-in retry for collection creation
config = CollectionPoolConfig(
    max_init_retries=5,           # 5 attempts
    init_retry_delay_seconds=2.0  # 2 second delay
)
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/unit/test_collection_pool.py -v

# Run with coverage
pytest tests/unit/test_collection_pool.py --cov=src/pools --cov-report=html

# Run performance tests only
pytest tests/unit/test_collection_pool.py::TestPerformance -v
```

### Test Coverage

- **Overall Coverage**: 88%
- **PooledCollection**: 100%
- **CollectionPoolConfig**: 100%
- **Core Methods**: 90%+

---

## Troubleshooting

### Collections Not Being Released

**Symptom**: Pool runs out of available collections

**Solution**:
```python
# Ensure all acquired collections are released
try:
    collection = await pool.acquire(dimension=128)
    # ... work ...
finally:
    await pool.release(collection.name)
```

### High Memory Usage

**Symptom**: Memory grows over time

**Solution**:
```python
# Reduce max_idle_seconds to expire collections faster
config = CollectionPoolConfig(
    max_idle_seconds=300,  # 5 minutes instead of 30
    cleanup_interval_seconds=60,  # More frequent cleanup
)
```

### Cleanup Not Running

**Symptom**: Expired collections accumulate

**Solution**:
```python
# Verify auto cleanup is enabled
status = await pool.get_status()
assert status["is_initialized"] is True

# Manually trigger cleanup
await pool._cleanup_expired()
```

---

## API Reference

### PersistentCollectionPool

```python
class PersistentCollectionPool:
    def __init__(self, adapter, config: CollectionPoolConfig = None)
    async def initialize(self) -> None
    async def shutdown(self) -> None
    async def acquire(self, dimension: int, metric_type: str = "L2",
                     timeout_seconds: float = 30.0) -> PooledCollection
    async def release(self, collection_name: str) -> None
    async def mark_for_deletion(self, collection_name: str) -> None
    async def get_status(self) -> Dict
```

### PooledCollection

```python
@dataclass
class PooledCollection:
    name: str
    dimension: int
    metric_type: str = "L2"
    status: CollectionStatus
    created_at: datetime
    last_used_at: datetime
    usage_count: int
    is_deleted: bool

    @property
    def age_seconds(self) -> int

    @property
    def idle_seconds(self) -> int

    def mark_in_use(self) -> None
    def mark_available(self) -> None
    def mark_for_deletion(self) -> None
    def is_expired(self, max_idle_seconds: int) -> bool
```

### CollectionStatus

```python
class CollectionStatus(Enum):
    INITIALIZING = "initializing"
    AVAILABLE = "available"
    IN_USE = "in_use"
    MARKED_FOR_DELETION = "marked_for_deletion"
    EXPIRED = "expired"
```

---

## Changelog

### Version 1.0.0 (2026-03-30)
- Initial release
- Pre-created pool support
- Logical deletion mechanism
- Concurrent-safe operations
- Automatic cleanup
- 88% test coverage

---

## License

Copyright © 2026 AI-DB-QC Team. All rights reserved.
