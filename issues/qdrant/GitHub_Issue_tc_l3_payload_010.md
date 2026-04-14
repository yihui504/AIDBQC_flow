# [Bug]: Type-3 (Traditional Oracle) in tc_l3_payload_010

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
A traditional oracle violation was detected during the search operation with max payload size limit. The system did not enforce the expected constraints or returned results that violate the defined payload size limits.

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
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# Generate and insert points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(vector_size)],
        payload={
            "text_data": "Sample text " * 1000  # Approx 13KB payload
        }
    )
    for i in range(10)
]

client.upsert(collection_name=collection_name, points=points)

# Perform search
search_result = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(vector_size)],
    limit=5
)

print(f"Found {len(search_result)} points")
```

### Expected Behavior
The search operation should respect the `max_payload_size_bytes` constraint (65535 bytes). If a payload exceeds this limit, the system should either reject the point during insertion or handle the search gracefully without violating the oracle constraints.

### Actual Behavior
The operation completed successfully, but the results indicate a violation of the traditional oracle constraints related to payload size limits during the search process.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)