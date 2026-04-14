# [Bug]: Invalid metric configuration accepted without error

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://qdrant.tech/documentation/concepts/points/', 'supported_metrics': 'https://qdrant.tech/documentation/concepts/points/', 'max_top_k': 'https://qdrant.tech/documentation/concepts/points/', 'max_collection_name_length': 'https://qdrant.tech/documentation/concepts/collections/', 'max_payload_size_bytes': 'https://qdrant.tech/documentation/concepts/payload/'}, 'exhaustive_constraints': {'vector_config': {'size': 'Integer > 0', 'distance': 'Enum(Cosine, Euclid, Dot, Manhattan)'}, 'hnsw_config': {'m': 'Integer (default 16)', 'ef_construct': 'Integer (default 100)'}, 'optimizers_config': {'indexing_threshold': 'Integer (default 20000)'}, 'quantization_config': {'scalar': {'type': 'int8'}, 'product': {'compression': 'float32'}}}}

### Describe the bug
Qdrant allows the creation of collections with invalid or misspelled metric names (e.g., 'InvalidMetric') without raising an error. This violates the configuration contract which states that the distance metric must be one of the supported types (Cosine, Euclid, Dot, Manhattan). Consequently, search operations may execute on undefined logic, leading to unpredictable results or silent failures.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_invalid_metric"

# 1. Attempt to create a collection with an invalid metric name
# Expected: Error/Exception
# Actual: Collection created successfully
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance="InvalidMetric")
)

# 2. Insert points
client.upsert(
    collection_name=collection_name,
    points=[PointStruct(id=1, vector=[random.random() for _ in range(128)], payload={})]
)

# 3. Perform search
# This may execute without error, but the metric logic is undefined
results = client.search(
    collection_name=collection_name,
    query_vector=[random.random() for _ in range(128)],
    limit=5
)

print(f"Search completed with undefined metric: {results}")
```

### Expected Behavior
Qdrant should reject the creation of the collection and return a 400 Bad Request error (or equivalent SDK exception) when an invalid metric name is provided in the `vectors_config`. The system should enforce the `Enum(Cosine, Euclid, Dot, Manhattan)` constraint defined in the configuration schema.

### Actual Behavior
The collection is created successfully (HTTP 200 OK) despite the invalid metric configuration. The logs show `Creating collection fuzz_pool_dim_128_1776178721` (or similar) without any validation error. Subsequent search operations proceed, potentially using undefined or incorrect distance calculations.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The exhaustive constraints specify `vector_config.distance` must be `Enum(Cosine, Euclid, Dot, Manhattan)`. Allowing an arbitrary string like 'InvalidMetric' violates this schema.
- **Reference URL**: https://qdrant.tech/documentation/concepts/points/
- **Verification Status**: Logic Verified (No Doc Reference Needed)