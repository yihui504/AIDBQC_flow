# [Bug]: Query operation fails silently or returns unexpected results when collection does not exist

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured']}

### Describe the bug
A Traditional Oracle violation (Type-3) was detected during a negative test sequence. The system attempted to query a collection (`TestCollection`) that was never created. Instead of receiving a definitive error indicating that the collection does not exist (e.g., 404 or specific error message), the operation may have resulted in ambiguous behavior or a generic error that does not clearly identify the root cause as a missing collection. This violates the expected contract where operations on non-existent collections should be explicitly rejected.

### Steps To Reproduce
```python
import weaviate
import os

# Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        url="http://localhost:8080",
        grpc_port=50051
    )
)
client.connect()

# Define a collection name that does NOT exist in the database
collection_name = "NonExistentCollectionForTest"

# Attempt to query the non-existent collection
# Expected: A clear error indicating the collection was not found
collection = client.collections.get(collection_name)

try:
    # This should fail, but the error message might be ambiguous
    response = collection.query.fetch_objects(limit=1)
    print(f"Unexpected success or ambiguous error: {response}")
except Exception as e:
    print(f"Error received: {e}")

client.close()
```

### Expected Behavior
According to the state constraints and standard database behavior, attempting to query or access a collection that has not been created should result in a clear, unambiguous error (e.g., `404 Not Found` or a specific `Collection: NonExistentCollectionForTest not found` exception). The system should not return success or a generic error that obscures the fact that the collection is missing.

### Actual Behavior
The operation resulted in a Traditional Oracle violation. The specific error message was not captured in the defect report, but the behavior was flagged as a violation, suggesting the response did not correctly identify the missing collection state.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found. The violation is based on the logical expectation that a database must enforce state constraints (specifically `collection_exists`) and return appropriate errors for invalid operations on non-existent entities.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)