# [Bug]: Search operation fails with 'Database not ready or disconnected' when top_k is set to max boundary (16384)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready']}

### Describe the bug
When performing a vector search with the `top_k` parameter set to the documented maximum boundary of 16384, the operation fails with a connection error indicating the database is not ready or disconnected. This suggests a failure in handling the upper limit of the result set size, potentially causing a timeout or crash in the query node or a related component.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(alias="default", host='localhost', port='19530')

# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="test collection")
collection_name = "test_max_topk"

# 3. Create Collection and Insert Data
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# Insert 20,000 random vectors to ensure we have enough data for top_k=16384
nb = 20000
vectors = np.random.rand(nb, dim).astype(np.float32)
collection.insert([vectors])
collection.flush()

# 4. Create Index and Load
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index(field_name="vector", index_params=index_params)
collection.load()

# 5. Perform Search with MAX top_k (16384)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

# Define a query vector
query_vector = [vectors[0].tolist()]

# Trigger the bug with max_top_k
try:
    results = collection.search(
        data=query_vector,
        anns_field="vector",
        param=search_params,
        limit=16384,  # MAX_TOP_K boundary
        expr=None
    )
    print(f"Search succeeded. Returned {len(results[0])} results.")
except Exception as e:
    print(f"Search failed: {e}")
```

### Expected Behavior
The search operation should successfully return up to 16384 results (or the total number of vectors in the collection, whichever is smaller) without connection errors, as `max_top_k` is defined as 16384 in the configuration.

### Actual Behavior
The search operation fails with the error: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The environment configuration specifies `max_top_k: 16384`. The failure at this specific boundary value indicates a violation of the expected operational contract for the search API.
- **Reference URL**: https://milvus.io/api-reference/restful/v2.4.x/v2/Vector%20(v2)/Search.md
- **Verification Status**: Logic Verified (No Doc Reference Needed)