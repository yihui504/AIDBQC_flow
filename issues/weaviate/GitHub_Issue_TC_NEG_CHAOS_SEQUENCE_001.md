# [Bug]: Type-3 (Traditional Oracle) in TC_NEG_CHAOS_SEQUENCE_001

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured']}

### Describe the bug
A Traditional Oracle violation was detected during a negative chaos sequence test. The system attempted to perform a query operation on a collection that did not exist or was not fully initialized, violating the expected state constraints of the database schema.

### Steps To Reproduce
```python
import weaviate
import os
import random
import numpy as np

# Connect to Weaviate
client = weaviate.connect_to_local()

# Define a collection name that has not been created yet
chaos_collection_name = "NonExistentCollection"

# Attempt to query the non-existent collection to trigger the oracle violation
try:
    collection = client.collections.get(chaos_collection_name)
    
    # Generate a random vector for the query attempt
    vector_dim = 768
    random_vector = np.random.rand(vector_dim).tolist()
    
    # This operation should fail as the collection does not exist
    response = collection.query.near_vector(
        near_vector=random_vector,
        limit=1
    )
    print("Query succeeded unexpectedly:", response)

except Exception as e:
    print(f"Exception caught as expected: {e}")

finally:
    client.close()
```

### Expected Behavior
The system should strictly enforce schema state constraints. Attempting to query or access a collection that has not been created should result in a clear, deterministic error (e.g., 404 Not Found or specific collection missing error) rather than an undefined state or a traditional oracle violation where the behavior contradicts the known schema state.

### Actual Behavior
The test case `TC_NEG_CHAOS_SEQUENCE_001` indicated a Traditional Oracle violation. The operation `chaos query before create` resulted in a state where the expected error handling or schema validation logic failed to correctly identify the absence of the collection, or the system behaved inconsistently with the defined schema state.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)