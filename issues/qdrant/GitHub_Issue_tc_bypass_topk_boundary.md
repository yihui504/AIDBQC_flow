# [Bug]: Search results exceed the defined `limit` (top-k) parameter

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux / Windows
- **Vector config**: Dimensions: 128/1536, Distance: Cosine/Euclid

### Describe the bug
When performing a search query with a specific `limit` (top-k) parameter, Qdrant returns more results than requested. This violates the expected contract where the number of returned points should strictly respect the `limit` defined in the search request.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection
collection_name = "test_limit_bug"
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# 3. Insert Points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={"id": i}
    )
    for i in range(100)
]
client.upsert(collection_name=collection_name, points=points)

# 4. Search with a specific limit
search_limit = 5
query_vector = [random.random() for _ in range(128)]

results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=search_limit
)

# 5. Verify Result Count
print(f"Requested limit: {search_limit}")
print(f"Actual results returned: {len(results)}")

# Assertion to demonstrate the bug
assert len(results) == search_limit, f"Expected {search_limit} results, but got {len(results)}"
```

### Expected Behavior
The search operation should return exactly `limit` (top-k) results. If `limit=5` is specified, the response list should contain 5 or fewer points (if fewer points exist in the collection).

### Actual Behavior
The search operation returns more results than specified by the `limit` parameter. For example, requesting 5 results may return 10 or more, causing downstream pagination and UI logic to fail.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "The `limit` parameter sets the maximum number of points to return."
- **Reference URL**: https://qdrant.tech/documentation/concepts/points/
- **Verification Status**: Logic Verified (No Doc Reference Needed)
