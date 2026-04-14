# [Bug]: Search results violate Top-K limit (Traditional Oracle)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: Dimensions: 128, 3, 1536; Metrics: Cosine, Euclid, Dot, Manhattan

### Describe the bug
A Traditional Oracle violation was detected during search operations. The search API returned more results than requested via the `limit` parameter, violating the expected Top-K constraint.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_top_k_oracle"
vector_size = 128

# 1. Create collection
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# 2. Insert points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(vector_size)],
        payload={"color": "red"}
    )
    for i in range(100)
]
client.upsert(collection_name=collection_name, points=points)

# 3. Search with specific limit
search_limit = 10
query_vector = [random.random() for _ in range(vector_size)]

results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=search_limit
)

# 4. Verify Oracle
print(f"Requested limit: {search_limit}")
print(f"Actual results returned: {len(results)}")

# Assert violation
if len(results) > search_limit:
    print(f"VIOLATION: Received {len(results)} results, expected max {search_limit}")
```

### Expected Behavior
The search operation should return a maximum of `limit` (Top-K) results. If `limit=10`, the response list length must be <= 10.

### Actual Behavior
The search operation returned more results than specified by the `limit` parameter. This indicates a bypass of the Top-K constraint logic.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "The `limit` parameter allows you to specify the number of results to return."
- **Reference URL**: https://qdrant.tech/documentation/concepts/points/
- **Verification Status**: Logic Verified (No Doc Reference Needed)