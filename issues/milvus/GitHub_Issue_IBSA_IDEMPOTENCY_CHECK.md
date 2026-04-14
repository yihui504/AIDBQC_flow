# [Bug]: Type-3 (Traditional Oracle) in IBSA_IDEMPOTENCY_CHECK

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready']}

### Describe the bug
A Traditional Oracle violation was detected during the 'IBSA_IDEMPOTENCY_CHECK' operation. The system failed to return consistent results for a duplicate query operation ('wireless headphones'), resulting in an L2 Gating Failure with the message: 'Database not ready or disconnected.'

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connection logic
connections.connect(alias="default", host='localhost', port='19530')

# 2. Collection creation with specific parameters
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="Test collection for idempotency check")
collection_name = "test_idempotency"

if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# 3. The exact operation that triggered the failure
# Inserting dummy data
entities = [np.random.rand(10, dim).astype(np.float32)]
collection.insert(entities)
collection.flush()

index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
collection.create_index(field_name="embeddings", index_params=index_params)
collection.load()

# Performing the duplicate query that causes the failure
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [np.random.rand(dim).astype(np.float32)]

# First query
results_1 = collection.search(data=query_vector, anns_field="embeddings", param=search_params, limit=10)

# Second query (Duplicate operation)
results_2 = collection.search(data=query_vector, anns_field="embeddings", param=search_params, limit=10)

# Verification (Expected to pass, but fails with L2 Gating Error)
assert results_1 == results_2, "Idempotency check failed: results differ for identical queries."
```

### Expected Behavior
Executing the same search query twice ('Duplicate query') should return identical results (Idempotency). The system should handle the connection state transparently without reporting 'Database not ready or disconnected' during standard operations.

### Actual Behavior
The system reported an L2 Gating Failure: 'Database not ready or disconnected.' during the duplicate query operation, indicating a potential state management or connection handling issue that violates the idempotency principle.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)