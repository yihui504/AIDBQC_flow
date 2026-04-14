# [Bug]: Semantic Oracle Violation - Identical Vector Query Returns Non-Zero Distance

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
When performing a semantic search using a query vector that is identical to a vector stored in the database, the system returns a distance significantly greater than 0.0 (specifically 1.2395). This violates the mathematical contract of the cosine distance metric, where identical vectors should result in a distance of 0.0.

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
from weaviate.collections import Collection

# 1. Connect to Weaviate
client = weaviate.WeaviateClient(connection_params=weaviate.connect.ConnectionParams.from_url("http://localhost:8080", grpc_port=50051))
client.connect()

# 2. Create Collection with Cosine Similarity
collection_name = "TestSemanticOracle"
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

client.collections.create(
    name=collection_name,
    properties=[
        wvc.Property(name="text", data_type=wvc.DataType.TEXT)
    ],
    # Configure vector settings explicitly
    vectorizer_config=wvc.Configure.Vectorizer.none(),
    vector_index_config=wvc.Configure.VectorIndex.hnsw(
        distance_metric=wvc.VectorDistances.COSINE
    )
)

collection = client.collections.get(collection_name)

# 3. Insert an object with a specific vector
# Using a fixed vector to ensure reproducibility
test_vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

with collection.batch.dynamic() as batch:
    batch.add_object(
        properties={"text": "Test Object"},
        vector=test_vector
    )

# 4. Query with the EXACT same vector
response = collection.query.near_vector(
    near_vector=test_vector,
    limit=1
)

# 5. Verify the distance
if response.objects:
    result_distance = response.objects[0].metadata.distance
    print(f"Distance: {result_distance}")
    # Expected: 0.0
    # Actual: 1.2395336627960205 (as per defect report)
    assert result_distance == 0.0, f"Expected distance 0.0 for identical vectors, got {result_distance}"

client.close()
```

### Expected Behavior
When querying with a vector that is identical to a stored vector, the `distance` returned should be `0.0` (or extremely close to 0.0, e.g., < 1e-6) for the `cosine` distance metric. The object containing the identical vector should be ranked first.

### Actual Behavior
The query returned a result with a distance of `1.2395336627960205`. This indicates that the system failed to recognize the identical vector or the distance calculation is incorrect, resulting in a semantic match that is mathematically incorrect.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The mathematical definition of Cosine Distance dictates that identical vectors yield a distance of 0.0.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)