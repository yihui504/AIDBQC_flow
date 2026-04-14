# [Bug]: Search results count mismatch when requesting large top_k values

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
When performing a semantic search with a `limit` (top_k) parameter set to 10,000, the database returns significantly fewer results than requested (approximately 5), despite the collection containing sufficient data. This indicates a discrepancy between the requested pagination size and the actual output volume.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection with sufficient data
collection_name = "test_large_top_k"
if client.collection_exists(collection_name):
    client.delete_collection(collection_name)

client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# Insert 20,000 points to ensure we have enough data for top_k=10000
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={"color": "red"}
    )
    for i in range(20000)
]

client.upsert(
    collection_name=collection_name,
    points=points
)

# 3. Perform search with large top_k
search_result = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=10000
)

# 4. Verify Result Count
print(f"Requested limit: 10000")
print(f"Actual results returned: {len(search_result)}")

# Assert to demonstrate failure
assert len(search_result) == 10000, f"Expected 10000 results, got {len(search_result)}"
```

### Expected Behavior
The search operation should return exactly 10,000 points (or the total number of points in the collection if it is less than 10,000), as specified by the `limit` parameter in the search request.

### Actual Behavior
The search operation returned approximately 5 results, which is significantly less than the requested 10,000. The execution did not crash, but the result set was truncated unexpectedly.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Violation)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. While the environment config specifies `max_top_k: 10000`, the specific behavior of result truncation in this context is not explicitly documented in the provided text.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)