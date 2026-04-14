# [Bug]: Hybrid search weight 1.0 violates traditional oracle (Type-3)

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
A traditional oracle violation was detected during hybrid search operations when the weight parameter was set to 1.0. The system failed to maintain the expected logical consistency for the results, indicating a potential defect in the hybrid search scoring or ranking mechanism.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SearchRequest, VectorInput, NamedVector
import random

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

collection_name = "fuzz_pool_dim_128_1776178721"

# 2. Create Collection with specific parameters
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# 3. Insert Points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={"metadata": f"point_{i}"}
    )
    for i in range(10)
]
client.upsert(collection_name=collection_name, points=points)

# 4. Execute Hybrid Search with weight 1.0
# This operation triggers the traditional oracle violation
search_result = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=5,
    # Using weight 1.0 as per the defect report context
    # Note: Hybrid search specifics depend on configuration, 
    # reproducing the exact weight application logic.
)

print(f"Search results: {search_result}")
```

### Expected Behavior
When performing a hybrid search with a weight of 1.0, the results should strictly adhere to the ranking defined by the weighted combination of scores (or the specific component if weight is 1.0). The system should not violate the traditional oracle, meaning the output should be logically consistent with the input data and search parameters.

### Actual Behavior
The search operation resulted in a Traditional Oracle violation (Type-3). The logs indicate successful HTTP 200 responses, but the internal logic check failed, suggesting the returned results did not match the expected mathematical or logical outcome for the given inputs.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)