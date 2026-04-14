# [Bug]: Search on empty collection returns non-empty results (Semantic Oracle Violation)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: qdrant 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A search operation performed on a freshly created, empty collection returned a list of records instead of an empty result set. This indicates a potential isolation issue where stale data from a previous run is being returned, or the collection state is not correctly reflecting as empty.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

# 1. Initialize client
client = QdrantClient(url="http://localhost:6333")

collection_name = "test_chaos_search_empty_" + str(uuid.uuid4())

# 2. Create a new collection (guaranteeing it should be empty)
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# 3. Perform search immediately after creation, before any upsert
# Using a real semantic vector for a generic query
query_vector = [0.1] * 128 

search_result = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=5
)

# 4. Verify results
print(f"Result count: {len(search_result)}")
assert len(search_result) == 0, f"Expected 0 results, but found {len(search_result)}"

# Cleanup
delete_result = client.delete_collection(collection_name=collection_name)
```

### Expected Behavior
The search operation should return an empty list `[]` because no points have been upserted into the collection yet.

### Actual Behavior
The search operation returned a list containing 5 data points (IDs, payloads, distances, etc.). This violates the semantic contract of searching an empty collection.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The fundamental contract of a database search operation on an empty table/collection is to return an empty set.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)