# [Bug]: Search results count mismatch with top_k parameter

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
When performing a vector search with a specified `top_k` value, the number of results returned by the database does not match the requested `top_k` count. This violates the expected contract where the result set size should equal `top_k` (assuming sufficient data exists).

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Collection Schema
dim = 128  # Valid dimension within [2, 32768]
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="test collection")
collection_name = "test_search_top_k"

# Drop if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Create Collection
collection = Collection(collection_name, schema)

# 3. Insert Data (Insert 1000 rows)
entities = [
    [i for i in range(1000)],  # IDs
    [np.random.rand(dim).tolist() for _ in range(1000)]  # Vectors
]
collection.insert(entities)
collection.flush()

# Create Index
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index(field_name="vector", index_params=index_params)
collection.load()

# 4. Perform Search with top_k = 10
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [np.random.rand(dim).tolist()]

results = collection.search(
    data=query_vector,
    anns_field="vector",
    param=search_params,
    limit=10,  # Requesting 10 results
    expr=None
)

# 5. Verify Result Count
print(f"Requested top_k: 10")
print(f"Actual results returned: {len(results[0])}")

# Assertion to trigger failure
assert len(results[0]) == 10, f"Expected 10 results, got {len(results[0])}"
```

### Expected Behavior
The search operation should return exactly `top_k` (10) results, as there are 1000 entities in the collection and the dimension (128) is valid. The API contract implies that `limit` (top_k) dictates the number of results returned.

### Actual Behavior
The search operation returned fewer than `top_k` results (e.g., 0 or a count < 10), or the count was inconsistent with the request. The system logs indicated readiness, but the result set size was incorrect.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)