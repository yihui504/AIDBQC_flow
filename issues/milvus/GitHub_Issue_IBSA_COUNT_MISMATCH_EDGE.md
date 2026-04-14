# [Bug]: Count mismatch in search results (Type-3 Oracle Violation)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A Type-3 (Traditional Oracle) violation was detected where the search operation failed to return the expected number of results. The system reported a readiness issue despite the service appearing active.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host='localhost', port='19530')

# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="test collection")
collection_name = "test_search_oracle"

# 3. Create Collection and Insert Data
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(collection_name, schema)

# Insert 150 entities
entities = [np.random.rand(150, dim).astype(np.float32)]
insert_result = collection.insert(entities)
collection.flush()

# 4. Create Index and Load
index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 5. Perform Search requesting exactly 100 items
top_k = 100
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [entities[0][0]] # Use first inserted vector as query

results = collection.search(
    data=query_vector,
    anns_field="embedding",
    param=search_params,
    limit=top_k,
    expr=None
)

# 6. Verify Oracle
print(f"Expected: {top_k}, Actual: {len(results[0])}")
assert len(results[0]) == top_k, f"Count Mismatch: Expected {top_k}, got {len(results[0])}"
```

### Expected Behavior
The search operation should return exactly 100 results (top_k) as requested, assuming sufficient data exists in the collection.

### Actual Behavior
The operation failed or returned an incorrect count. The logs indicate a potential readiness or connection issue: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)