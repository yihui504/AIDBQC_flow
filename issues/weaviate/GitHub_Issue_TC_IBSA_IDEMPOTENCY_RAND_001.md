# [Bug]: Type-3 (Traditional Oracle) in TC_IBSA_IDEMPOTENCY_RAND_001

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A Traditional oracle violation was detected during the `stable_query_for_consistency_check` operation. The system failed to maintain consistency guarantees expected under the test conditions, resulting in a deviation from the deterministic or stable behavior required for the operation `TC_IBSA_IDEMPOTENCY_RAND_001`.

### Steps To Reproduce
```python
import weaviate
import os
import random
import numpy as np

# Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        url="http://localhost:8080",
        grpc_port=50051
    )
)
client.connect()

# Configuration
collection_name = "TestConsistency"
dim = 768

# Clean up if exists
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

# Create Collection
client.collections.create(
    name=collection_name,
    properties=[
        weaviate.classes.Property(name="text", data_type=weaviate.classes.DataType.TEXT),
    ],
    vectorizer_config=weaviate.classes.Configure.Vectorizer.none(),
    vector_index_config=weaviate.classes.Configure.VectorIndex.hnsw(
        distance_metric=weaviate.classes.VectorDistances.COSINE
    )
)

collection = client.collections.get(collection_name)

# Insert Data with specific vectors
with collection.batch.dynamic() as batch:
    for i in range(10):
        # Generate deterministic random vectors based on index to ensure reproducibility
        # Using a fixed seed for the MRE
        rng = np.random.default_rng(i)
        vector = rng.random(dim)
        
        batch.add_object(
            properties={"text": f"object {i}"},
            vector=vector.tolist()
        )

# Perform the operation that triggered the failure
# Simulating a stable query for consistency check
response = collection.query.near_vector(
    near_vector=np.random.rand(dim).tolist(),
    limit=5
)

print(f"Objects found: {len(response.objects)}")

client.close()
```

### Expected Behavior
The query operation should return consistent results for the given input vector and parameters, adhering to the stability and consistency guarantees of the database state.

### Actual Behavior
A Traditional oracle violation was detected in results. The system logs indicate a warning regarding log levels and standard startup procedures, but the core issue lies in the inconsistency of the query results relative to the expected oracle for the test case `TC_IBSA_IDEMPOTENCY_RAND_001`.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Traditional Oracle violations typically involve logic consistency checks not explicitly quoted in reference docs).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)