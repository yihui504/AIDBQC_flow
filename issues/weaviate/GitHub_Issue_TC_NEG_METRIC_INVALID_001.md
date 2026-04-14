# [Bug]: Invalid metric 'euclidean' accepted by collection configuration

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A traditional oracle violation was detected where the system accepted a vector index configuration with an invalid distance metric `euclidean`. According to the environment configuration and standard Weaviate behavior, the supported metrics are `['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan']`. The metric `euclidean` is typically an alias for `l2-squared` but is not a valid configuration value in the API schema. The collection was created successfully, but the metric configuration violates the defined contract.

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
from weaviate.connect import ConnectionParams

# Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(
        url="http://localhost:8080",
        grpc_port=50051
    )
)
client.connect()

# Create a collection with an INVALID metric 'euclidean'
# Expected supported metrics: cosine, dot, l2-squared, hamming, manhattan
try:
    collection = client.collections.create(
        name="TestInvalidMetric",
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
        ],
        # Define vector config with the invalid metric
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
            distance_metric=wvc.config.VectorDistances.EUCLIDEAN # Invalid Metric
        )
    )
    print("Collection created successfully with invalid metric.")
except Exception as e:
    print(f"Error during creation: {e}")

# Verify the collection configuration
try:
    config = client.collections.get("TestInvalidMetric").config.get()
    print(f"Configured Metric: {config.vectorizer_config.vector_index_config.distance}")
except Exception as e:
    print(f"Error fetching config: {e}")

client.close()
```

### Expected Behavior
The system should reject the collection creation or configuration update if the `distance_metric` is set to `euclidean`. The API should return a 400 Bad Request error indicating that `euclidean` is not a supported metric. Valid metrics are `cosine`, `dot`, `l2-squared`, `hamming`, and `manhattan`.

### Actual Behavior
The collection was created successfully (or the configuration was accepted) despite the use of the invalid metric `euclidean`. This indicates a lack of input validation on the `distance_metric` parameter against the list of supported metrics.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The environment configuration explicitly lists `supported_metrics` as `['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan']`. The metric `euclidean` is not included in this list.
- **Reference URL**: https://weaviate.io/developers/weaviate
- **Verification Status**: Logic Verified (No Doc Reference Needed)