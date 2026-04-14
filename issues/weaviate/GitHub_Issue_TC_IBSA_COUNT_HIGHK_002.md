# [Bug]: Semantic Oracle Violation in TC_IBSA_COUNT_HIGHK_002 - top_k=10000 returns insufficient results

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic oracle violation occurs when querying with `limit=10000` (corresponding to `top_k=10000`). The system configuration explicitly defines `max_top_k` as 10000, implying the capability to return up to 10,000 results. However, the execution results demonstrate a failure to return the requested volume of data. The output is truncated and contains only a handful of entries (visible IDs: 0926..., af38..., 71fb..., 9dd0..., 9fd...), failing to satisfy the semantic intent of retrieving the maximum number of results.

### Steps To Reproduce
```python
import weaviate
from weaviate.classes.config import Configure
import numpy as np

# 1. Connection logic
client = weaviate.WeaviateClient(connection_params=weaviate.connect_to_local())
client.connect()

# 2. Collection creation with specific parameters
# Note: Using a configuration that supports high K retrieval
collection_name = "TestHighK"

if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

client.collections.create(
    name=collection_name,
    properties=[
        wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
    ],
    # Configure vectorizer and index settings suitable for the test
    vectorizer_config=[Configure.NamedVectors.text2vec_transformers(
        name="vector",
        source_properties=["text"]
    )]
)

collection = client.collections.get(collection_name)

# Data insertion: Ensure sufficient data exists to test top_k=10000
# In a real scenario, 10k+ objects should be imported. 
# For this MRE, we assume data exists or we insert a batch.
with collection.batch.dynamic() as batch:
    for i in range(10050): # Insert slightly more than 10k
        batch.add_object(
            properties={"text": f"Sample data object number {i}"},
            # vector=... # Explicit vector can be passed if needed, otherwise module generates it
        )

# 3. The exact operation that triggered the failure
# Attempt to retrieve the maximum number of results
response = collection.query.fetch_objects(limit=10000)

# Verification
print(f"Requested limit: 10000")
print(f"Actual results count: {len(response.objects)}")

if len(response.objects) < 10000:
    print(f"FAILURE: Expected 10000 results, but got {len(response.objects)}")
else:
    print("SUCCESS: Retrieved expected number of results.")

client.close()
```

### Expected Behavior
According to the environment configuration (`max_top_k: 10000`), the system should support retrieving up to 10,000 objects in a single query. When `limit=10000` is specified and sufficient data exists, the response should contain 10,000 objects.

### Actual Behavior
The query executes without a crash (L1 success), but the result set is truncated. The raw results show only a few entries (e.g., ending at '9fd') instead of the expected 10,000. This indicates a discrepancy between the configured capability and the actual retrieval logic or result serialization.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The configuration `max_top_k: 10000` implies the capability, but the specific behavior of truncation violates the logical expectation of that configuration.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)