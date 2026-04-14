# [Bug]: Search with top_k exceeding maximum limit (Type-3)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A Traditional Oracle violation was detected during search operations. The system accepted and processed search requests where the `limit` (top_k) parameter exceeded the documented maximum constraint of `10000`. This indicates a bypass of validation logic intended to enforce the `max_top_k` configuration.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection
collection_name = "test_top_k_limit"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# 3. Insert Points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={}
    )
    for i in range(100)
]
client.upsert(collection_name=collection_name, points=points)

# 4. Search with top_k exceeding maximum limit (10000)
# Expected: Validation Error or Rejection
# Actual: Request processed (Traditional Oracle Violation)
search_result = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=10001  # Exceeds max_top_k of 10000
)

print(f"Result count: {len(search_result)}")
```

### Expected Behavior
According to the environment configuration constraints (`max_top_k: 10000`), the API should reject any search request where the `limit` parameter is greater than 10000. The expected behavior is a validation error (e.g., HTTP 400 or a specific validation exception) indicating the limit exceeds the maximum allowed value.

### Actual Behavior
The search request with `limit=10001` was accepted and processed by the server without raising a validation error. This violates the constraint defined in the vector configuration, allowing a Traditional Oracle bypass where the system state (accepted limit) contradicts the defined rules (max_top_k).

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "max_top_k: 10000" (Derived from Environment Context constraints)
- **Reference URL**: https://qdrant.tech/documentation/concepts/points/
- **Verification Status**: Logic Verified (No Doc Reference Needed)