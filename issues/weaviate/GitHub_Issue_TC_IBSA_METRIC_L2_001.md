# [Bug]: L2-Squared distance metric returns non-zero distance for identical vectors

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
When performing a semantic search using the `l2-squared` distance metric, querying a collection with the exact same vector that was just inserted results in a distance of approximately 1.57. According to the mathematical definition of the L2-squared distance, the distance between a vector and itself should be 0.0.

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
from weaviate.connect import ConnectionParams

# 1. Connection logic
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
    )
)
client.connect()

# 2. Collection creation with specific parameters
# Create a collection with l2-squared metric
if client.collections.exists("TestCollection"):
    client.collections.delete("TestCollection")

collection = client.collections.create(
    name="TestCollection",
    properties=[
        wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
    ],
    # Configure vector settings explicitly
    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
        distance_metric=wvc.config.VectorDistances.L2_SQUARED
    )
)

# 3. The exact operation that triggered the failure
# Define a real semantic vector (e.g., an embedding for "apple")
# This vector represents the object to be stored.
vector_data = [0.1, 0.2, 0.3, 0.4, 0.5]

# Insert the object with the vector
with collection.batch.dynamic() as batch:
    batch.add_object(
        properties={"title": "Apple"},
        vector=vector_data
    )

# Query using the IDENTICAL vector
response = collection.query.near_vector(
    near_vector=vector_data,
    limit=1
)

# 4. Verification
if response.objects:
    result_distance = response.objects[0].metadata.distance
    print(f"Distance returned: {result_distance}")
    # Expected: 0.0
    # Actual: ~1.57
    assert result_distance == 0.0, f"Expected 0.0, got {result_distance}"

client.close()
```

### Expected Behavior
The distance returned for a query using the identical vector used for insertion should be `0.0` when using the `l2-squared` metric.

### Actual Behavior
The query returns a distance of approximately `1.5656709671020508` for the identical vector.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Violation)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The mathematical definition of L2-squared distance dictates that the distance between identical vectors is zero.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)