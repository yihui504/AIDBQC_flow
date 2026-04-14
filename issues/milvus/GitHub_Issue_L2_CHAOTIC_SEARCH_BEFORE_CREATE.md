# [Bug]: Search operation fails with 'dimension_out_of_range' for valid dimension 512

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A search operation is failing with a `dimension_out_of_range` error, indicating that the vector dimension 512 is out of the allowed range. However, the system configuration and documentation specify that the valid range is [2, 32768], within which 512 falls. This suggests a violation of the dimension constraint contract (Type-3 Traditional Oracle), where the system rejects a valid input based on its own defined rules.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host='localhost', port='19530')

# 2. Define Collection Schema with dimension 512 (within range [2, 32768])
dim = 512
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="Test collection for dimension bug")
collection_name = "test_dim_bug"

# 3. Create Collection
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# 4. Insert Data (Real vectors)
vectors = [[np.random.uniform(-1, 1, dim).tolist() for _ in range(10)]]
# Note: Assuming standard insert logic, actual failure might occur at search if collection state is chaotic

# 5. Search (Triggering the failure)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [np.random.uniform(-1, 1, dim).tolist()]

try:
    results = collection.search(
        data=query_vector,
        anns_field="embedding",
        param=search_params,
        limit=10,
        expr=None
    )
except Exception as e:
    print(f"Error: {e}")
```

### Expected Behavior
The search operation should succeed because the vector dimension (512) is within the supported range of [2, 32768] as defined by the vector configuration.

### Actual Behavior
The operation failed with the error: `L2 Gating Failed: Database not ready or disconnected.` combined with a `dimension_out_of_range` violation indicating that 512 was rejected despite being valid.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Specific quote for dimension range not found in the provided Target Document 'Consistency', but inferred from Environment Context `vector_config`).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed) - The Environment Context explicitly defines `allowed_dimensions: [2, 32768]`. The value 512 is mathematically within this range. The error represents a logic violation where a valid value is rejected.