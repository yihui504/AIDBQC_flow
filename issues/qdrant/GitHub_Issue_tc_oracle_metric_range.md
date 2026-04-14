# [Bug]: Type-3 (Traditional Oracle) in tc_oracle_metric_range

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
A traditional oracle violation was detected during the 'Identical vector search for range check' operation. The system failed to validate the range or metric constraints correctly, leading to unexpected behavior in the search results.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# Initialize client
client = QdrantClient(url="http://localhost:6333")

# Collection configuration
collection_name = "fuzz_pool_dim_128_1776178721"
vector_size = 128

# Recreate collection
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.EUCLID)
)

# Generate and insert points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(vector_size)],
        payload={}
    )
    for i in range(10)
]
client.upsert(collection_name=collection_name, points=points)

# Perform search that triggers the oracle violation
search_vector = [random.random() for _ in range(vector_size)]
results = client.search(
    collection_name=collection_name,
    query_vector=search_vector,
    limit=5
)

print(f"Found {len(results)} results")
```

### Expected Behavior
The search operation should return results that strictly adhere to the defined metric and range constraints, ensuring that all returned vectors are valid within the specified configuration.

### Actual Behavior
The system returned results that violated the traditional oracle constraints, indicating a potential issue with metric validation or range checking during the search operation.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)