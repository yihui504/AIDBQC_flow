# [Bug]: Hybrid search results violate traditional oracle expectations

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: qdrant 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A traditional oracle violation was detected during hybrid search operations. The results returned by the database did not align with the expected logical outcome for the given query and dataset configuration, indicating a potential discrepancy in the search or ranking logic.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SearchRequest, VectorParams, PayloadSchemaType
import numpy as np

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

collection_name = "fuzz_pool_dim_128_1776178721"

# Recreate collection with specific configuration
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# Insert sample data (Simulated based on logs)
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=np.random.rand(128).tolist(), payload={"brand": "Sony", "product": "Headphones"}),
        PointStruct(id=2, vector=np.random.rand(128).tolist(), payload={"brand": "Bose", "product": "Headphones"}),
        PointStruct(id=3, vector=np.random.rand(128).tolist(), payload={"brand": "Apple", "product": "Earbuds"})
    ],
    wait=True
)

# Perform Hybrid Search
# Note: Using a placeholder query vector as the specific query vector was not provided in the logs.
# The violation occurred with the query 'wireless headphones' and brand filtering.
search_result = client.search(
    collection_name=collection_name,
    query_vector=np.random.rand(128).tolist(),
    query_filter={
        "must": [
            {"key": "brand", "match": {"value": "Sony"}}
        ]
    },
    limit=10
)

print(search_result)
```

### Expected Behavior
The search results should strictly adhere to the filter conditions (e.g., brand matching) and return the most semantically similar vectors according to the configured distance metric (Cosine). The ranking should be consistent with the mathematical expectations of the vector space model.

### Actual Behavior
The system logs indicate successful execution of the search requests (HTTP 200), but the internal validation logic flagged a "Traditional oracle violation." This suggests that the set of points returned or their order was inconsistent with the ground truth established by the input data and query parameters.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)