# [Bug]: Semantic search with near_vector returns fewer results than specified in limit (top_k)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
When performing a semantic search using `near_vector` with a high `limit` (e.g., 10,000), the database returns significantly fewer results than requested (e.g., only 4 items) despite the collection containing sufficient data. This violates the expected behavior where the `limit` parameter dictates the maximum number of results to return.

### Steps To Reproduce
```python
import weaviate
from weaviate.classes.config import Configure
import numpy as np

# 1. Connect to Weaviate
client = weaviate.WeaviateClient(connection_params=weaviate.connect.ConnectionParams.from_url("http://localhost:8080", grpc_port=50051))
client.connect()

# 2. Create Collection
collection_name = "TestShoesCollection"
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

client.collections.create(
    name=collection_name,
    properties=[
        wvc.config.Property(name="description", data_type=wvc.config.DataType.TEXT),
    ],
    vectorizer_config=Configure.Vectorizer.none(),
)

# 3. Insert Data (Simulating 1000 items)
collection = client.collections.get(collection_name)

data_objects = []
vectors = []

# Generate 1000 objects with random vectors
for i in range(1000):
    data_objects.append({"description": f"Item {i}"})
    # Generate a random vector of dimension 768
    vectors.append(np.random.rand(768).tolist())

with collection.batch.dynamic() as batch:
    for i in range(len(data_objects)):
        batch.add_object(
            properties=data_objects[i],
            vector=vectors[i]
        )

# 4. Perform Query with high limit
query_vector = vectors[0] # Use the first vector as the query target

response = collection.query.near_vector(
    near_vector=query_vector,
    limit=10000
)

# 5. Verify Result Count
print(f"Requested limit: 10000")
print(f"Actual results returned: {len(response.objects)}")

assert len(response.objects) == 1000, f"Expected 1000 results, but got {len(response.objects)}"

client.close()
```

### Expected Behavior
The query should return up to the number of objects matching the vector similarity, capped by the `limit` parameter. If 1000 objects exist and `limit=10000`, all 1000 objects should be returned.

### Actual Behavior
The query returned only 4 results when 10,000 were requested (and 1000 were available). The system appears to be truncating the results unexpectedly.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Violation)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The `max_top_k` configuration (10000) implies support for high limits, but the system fails to adhere to the requested limit parameter during execution.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)