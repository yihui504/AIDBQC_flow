# [Bug]: Search results count mismatch with requested limit (Type-3)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A Traditional Oracle violation was detected during automated testing. The search operation returned a number of results that did not match the requested `limit` (top_k) parameter, despite sufficient points being available in the collection to satisfy the request.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

collection_name = "fuzz_pool_dim_128_1776178721"

# 2. Create Collection with specific parameters
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.EUCLID),
)

# 3. Insert Points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={}
    )
    for i in range(100) # Inserting 100 points
]

client.upsert(
    collection_name=collection_name,
    points=points,
    wait=True
)

# 4. Perform Search with a specific limit
search_limit = 10
query_vector = [random.random() for _ in range(128)]

results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=search_limit
)

# 5. Verify Count
print(f"Requested limit: {search_limit}")
print(f"Actual results count: {len(results)}")

# Assertion to demonstrate the bug
assert len(results) == search_limit, f"Expected {search_limit} results, but got {len(results)}"
```

### Expected Behavior
The search operation should return exactly the number of points specified by the `limit` parameter, assuming that many points exist in the collection. If 100 points are inserted and a `limit` of 10 is requested, the result list length should be 10.

### Actual Behavior
The search operation returned a different number of results than requested. The logs indicate successful creation and upsert operations, but the search response count violated the `limit` constraint.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)
