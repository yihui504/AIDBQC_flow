# [Bug]: Type-3 (Traditional Oracle) in POS_STANDARD_ECOMMERCE

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready']}

### Describe the bug
A Traditional Oracle violation was detected during the 'Find running shoes for men' operation. The system failed to return the expected results, reporting a readiness issue.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host='localhost', port='19530')

collection_name = "pos_standard_ecommerce"

# 2. Define Schema (E-commerce context)
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="product_vector", dtype=DataType.FLOAT_VECTOR, dim=768) # Standard embedding dim
]
schema = CollectionSchema(fields=fields, description="E-commerce product catalog")

# Drop if exists to ensure clean state
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# 3. Insert Data (Simulated E-commerce Vectors)
# Using random vectors for MRE stability, though semantic search prefers real embeddings
entities = [np.random.rand(1000, 768).astype(np.float32)]
collection.insert(entities)
collection.flush()

# 4. Create Index and Load
index_params = {"index_type": "HNSW", "metric_type": "L2", "params": {"M": 16, "efConstruction": 256}}
collection.create_index(field_name="product_vector", index_params=index_params)
collection.load()

# 5. Execute Search (The failing operation)
search_params = {"metric_type": "L2", "params": {"ef": 32}}
query_vector = [np.random.rand(768).astype(np.float32)]

results = collection.search(
    data=query_vector,
    anns_field="product_vector",
    param=search_params,
    limit=10,
    expr=None
)

print(results)
```

### Expected Behavior
The search operation should return the top 10 nearest neighbors for the given query vector based on L2 distance.

### Actual Behavior
The operation failed with the error: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)