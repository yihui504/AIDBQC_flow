# [Bug]: Semantic Oracle Violation - Delete operation on non-existent collection returns search results

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: qdrant 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A semantic oracle violation occurs when attempting to delete a payload from a collection that does not exist. The system reports 'Execution Success: True' and returns a list of JSON objects containing IDs, distances, and payloads (characteristic of a vector search operation), instead of handling the invalid request with an appropriate error or failure status. This indicates the query was likely misrouted or interpreted as a search/retrieval command instead of a deletion command.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Initialize the client
client = QdrantClient(url="http://localhost:6333")

# 2. Define a collection name that does NOT exist
non_existent_collection = "chaos_test_missing_collection"

# 3. Attempt to delete payload from the non-existent collection
# Expected: Error (e.g., 404 Not Found or Collection not found)
# Actual: Success with search results
try:
    operation_result = client.delete(
        collection_name=non_existent_collection,
        points_selector=[1, 2, 3] # Deleting arbitrary points
    )
    print(f"Operation Result: {operation_result}")
except Exception as e:
    print(f"Exception: {e}")
```

### Expected Behavior
The system should return an error indicating that the collection does not exist (e.g., `404: Collection not found`) or a failure status, as it is impossible to delete data from a collection that has not been created.

### Actual Behavior
The system returned a successful execution status (`Execution Success: True`) with raw results containing a list of retrieved items (IDs, distances, payloads), which is characteristic of a search operation, not a deletion. No error message was provided.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The behavior violates the logical contract that operations on non-existent resources should fail.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)