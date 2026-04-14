# [Bug]: Hybrid search weight sum calculation violates traditional oracle

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
A traditional oracle violation was detected during hybrid search operations involving sparse and dense vectors. The weighted sum of the scores does not align with the expected mathematical outcome based on the provided weights and individual scores.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVector, SearchRequest, SparseVectorParams
import numpy as np

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_hybrid_oracle"

# Recreate collection
client.delete_collection(collection_name)
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
    sparse_vectors_config={"text": SparseVectorParams()},
)

# Insert points
points = [
    PointStruct(
        id=1,
        vector=np.random.rand(128).tolist(),
        payload={"text": "blue running sneakers"}
    ),
    PointStruct(
        id=2,
        vector=np.random.rand(128).tolist(),
        payload={"text": "red leather shoes"}
    )
]
client.upsert(collection_name=collection_name, points=points)

# Perform Hybrid Search
# Note: Using random vectors for MRE stability, but logic applies to semantic vectors
search_result = client.search_batch(
    collection_name=collection_name,
    requests=[
        SearchRequest(
            vector=np.random.rand(128).tolist(),
            limit=10,
            with_payload=True,
        ),
    ],
)

# The violation occurs in the weighted sum calculation logic internally
# when combining sparse and dense scores.
print(search_result)
```

### Expected Behavior
The final score calculated during hybrid search (weighted sum) should strictly follow the formula: `Score = (Weight1 * Score1) + (Weight2 * Score2)`. Deviations from this mathematical contract constitute a Type-3 (Traditional Oracle) violation.

### Actual Behavior
The calculated scores deviate from the expected weighted sum, indicating a logic error in the aggregation function.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)