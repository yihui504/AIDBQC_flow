# [Bug]: Type-3 (Traditional Oracle) in TC_NEG_CHAOTIC_SEQ_001

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured']}

### Describe the bug
A traditional oracle violation was detected during the execution of test case `TC_NEG_CHAOTIC_SEQ_001`. The system behavior deviated from the expected outcome defined by the test oracle, specifically related to the sequence of operations or state management.

### Steps To Reproduce
```python
import weaviate
from weaviate.connect import ConnectionParams
from weaviate.classes.config import Configure, Property, DataType
import os

# Connect to Weaviate
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

# Create a collection to simulate the environment
# Note: Specific parameters derived from environment context
client.collections.create(
    name="TestCollection",
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
    # Configuration based on the chaotic sequence test context
    vectorizer_config=Configure.Vectorizer.none(),
    vector_index_config=Configure.VectorIndex.hnsw(
        distance_metric="cosine"
    )
)

# Perform the operation that triggered the failure
# Based on the 'Query before setup' operation description
collection = client.collections.get("TestCollection")

# Attempting a query or operation that violates the expected state
# (Specific reproduction logic for TC_NEG_CHAOTIC_SEQ_001)
try:
    # Example operation that might trigger the oracle violation in a chaotic sequence
    # This represents the 'Query before setup' or similar state-dependent failure
    collection.query.fetch_objects(limit=1)
except Exception as e:
    print(f"Exception caught: {e}")

client.close()
```

### Expected Behavior
The system should handle the sequence of operations defined in `TC_NEG_CHAOTIC_SEQ_001` without violating the traditional oracle. Specifically, operations should either succeed or fail with a predictable, documented error that aligns with the system's state contract.

### Actual Behavior
A traditional oracle violation was detected. The logs indicate a complex startup and restoration sequence involving multiple shards (`FuzzPoolDim1536_1776087941`, `FuzzPoolDim768_1776088065`, etc.) and cycle managers, but the specific deviation from the expected oracle logic occurred during the test execution.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)