# [Bug]: Querying non-existent collection returns success instead of error

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic oracle violation occurs when attempting to query a collection that does not exist. The system is expected to recognize the non-existence of the collection and return an error (e.g., 'collection not found'). However, the system incorrectly returns 'Execution Success: True' along with a list of valid data points, indicating it queried an existing collection instead of enforcing the boundary condition for the non-existent one.

### Steps To Reproduce
```python
import weaviate
from weaviate.connect import ConnectionParams
from weaviate.classes.config import Configure, Property, DataType

# 1. Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(
        url="http://localhost:8080", 
        grpc_port=50051
    )
)
client.connect()

# 2. Define a collection name that has NOT been created yet
collection_name = "NonExistentCollection"

# 3. Attempt to query the non-existent collection
# Expected: Error (e.g., 404 or collection not found)
try:
    response = client.collections.get(collection_name).query.fetch_objects(limit=5)
    print(f"Execution Success: True")
    print(f"Objects found: {len(response.objects)}")
    for obj in response.objects:
        print(f"ID: {obj.uuid}, Properties: {obj.properties}")
except Exception as e:
    print(f"Execution Failed: {e}")

client.close()
```

### Expected Behavior
The system should enforce the `collection_exists` state constraint. Since the collection `NonExistentCollection` was never created, the query should fail and return an error indicating that the collection does not exist.

### Actual Behavior
The query execution returns `Success: True` and provides a list of data points with IDs, distances, and payloads. This suggests the query was executed against an existing collection, failing to handle the 'chaotic' scenario of querying a non-existent resource.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The behavior violates the logical state constraint that a collection must exist to be queried.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)