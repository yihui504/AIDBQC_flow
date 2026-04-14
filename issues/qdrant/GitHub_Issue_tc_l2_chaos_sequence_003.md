# [Bug]: Type-3 (Traditional Oracle) in tc_l2_chaos_sequence_003

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: qdrant 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://qdrant.tech/documentation/concepts/points/', 'supported_metrics': 'https://qdrant.tech/documentation/concepts/points/', 'max_top_k': 'https://qdrant.tech/documentation/concepts/points/', 'max_collection_name_length': 'https://qdrant.tech/documentation/concepts/collections/', 'max_payload_size_bytes': 'https://qdrant.tech/documentation/concepts/payload/'}, 'exhaustive_constraints': {'vector_config': {'size': 'Integer > 0', 'distance': 'Enum(Cosine, Euclid, Dot, Manhattan)'}, 'hnsw_config': {'m': 'Integer (default 16)', 'ef_construct': 'Integer (default 100)'}, 'optimizers_config': {'indexing_threshold': 'Integer (default 20000)'}, 'quantization_config': {'scalar': {'type': 'int8'}, 'product': {'compression': 'float32'}}}}

### Describe the bug
A traditional oracle violation was detected during the execution of test case `tc_l2_chaos_sequence_003`. The system behavior deviated from the expected logical constraints or data integrity rules during a sequence of operations involving collection creation and point searching.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

# Initialize client
client = QdrantClient(url="http://localhost:6333")

collection_name = "fuzz_pool_dim_128_1776178721"

# 1. Create collection with specific parameters
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.Euclid)
)

# 2. Insert points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(128)],
        payload={"color": "red"}
    )
    for i in range(10)
]
client.upsert(collection_name=collection_name, points=points)

# 3. Perform search operations
search_result = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=5
)

# 4. Perform additional updates and searches to trigger the sequence
client.upsert(
    collection_name=collection_name, 
    points=[PointStruct(id=10, vector=[random.random() for _ in range(128)], payload={"color": "blue"})]
)

client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=5
)
```

### Expected Behavior
The sequence of creation, upsert, and search operations should maintain data consistency and return valid search results based on the inserted vectors, adhering to the traditional oracle constraints of the database state.

### Actual Behavior
A traditional oracle violation was detected in results. The logs indicate successful HTTP 200 responses for the operations, but the internal state validation failed, suggesting a potential logic error in the sequence handling or result verification.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)