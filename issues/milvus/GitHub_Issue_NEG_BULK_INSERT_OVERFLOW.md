# [Bug]: NEG_BULK_INSERT_OVERFLOW - L2 Gating Failure Prevents Payload Size Validation

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index']}

### Describe the bug
The test case `NEG_BULK_INSERT_OVERFLOW` is designed to verify that the system correctly handles payloads exceeding the maximum size (65535 bytes). However, the execution failed with an infrastructure-level error ('L2 Gating Failed: Database not ready or disconnected'). This connectivity failure prevented the system from reaching the logic responsible for validating the payload size constraint (L1 Contract). Consequently, the semantic intent of testing the payload size limit was not met, as the request was rejected by the connection layer before the payload size could be evaluated.

### Steps To Reproduce
```python
from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType
import numpy as np

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Create a collection with a specific schema
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="test collection")
collection = Collection(name="test_bulk_insert_overflow", schema=schema)

# 3. Prepare data exceeding max_payload_size_bytes (65535 bytes)
# Generating a large list of vectors to exceed the limit
num_vectors = 10000  # Adjusted to ensure payload > 65535 bytes
data = [np.random.rand(num_vectors, dim).tolist()]

# 4. Attempt bulk insert with oversized payload
try:
    utility.do_bulk_insert(
        collection_name="test_bulk_insert_overflow",
        files=data  # Passing oversized payload directly
    )
except Exception as e:
    print(f"Error: {e}")
```

### Expected Behavior
The system should accept the connection, process the request, and then reject the payload specifically because it exceeds the maximum size of 65535 bytes, returning a specific error related to the size constraint (e.g., "payload size exceeded").

### Actual Behavior
The operation failed with the error: `L2 Gating Failed: Database not ready or disconnected.` This indicates a connectivity or readiness issue at the infrastructure level (L2), rather than a validation failure at the payload size constraint level (L1).

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The test aims to verify a constraint (max_payload_size_bytes: 65535) defined in the environment configuration, but the failure occurred due to an L2 gating issue preventing the validation of this constraint.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)