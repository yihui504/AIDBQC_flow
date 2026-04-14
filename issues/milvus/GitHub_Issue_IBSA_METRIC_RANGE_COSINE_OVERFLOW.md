# [Bug]: Cosine metric returns distance > 1.0 for identical vectors

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
When performing a vector search using the `COSINE` metric type, the distance returned for identical vectors (which should be 0.0) is greater than 1.0. This violates the mathematical definition of Cosine Similarity/Distance, where the distance between identical vectors must be 0 (and similarity 1), and the range of valid distances is typically [0, 2]. A value > 1.0 for identical vectors indicates a calculation overflow or normalization error.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="Cosine test collection")
collection_name = "test_cosine_overflow"

# Drop if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Create Collection
collection = Collection(collection_name, schema)

# 3. Insert Data (Normalized vectors for Cosine)
import numpy as np
# Create a normalized vector
data = [[0.1] * dim]
vectors = [np.array(v).astype(np.float32) for v in data]
# Normalize manually to ensure unit length
norms = np.linalg.norm(vectors, axis=1, keepdims=True)
vectors = vectors / norms

insert_result = collection.insert([vectors])
collection.flush()

# 4. Create Index and Load
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index(field_name="embeddings", index_params=index_params)
collection.load()

# 5. Search with Identical Vector
search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
results = collection.search(
    data=vectors, 
    anns_field="embeddings", 
    param=search_params, 
    limit=1, 
    expr=None
)

# 6. Check Result
dist = results[0].distances[0]
print(f"Distance for identical vector: {dist}")

# Expected: 0.0
# Actual: > 1.0 (Overflow)
assert dist < 1.0, f"Cosine distance should be < 1.0 for identical vectors, got {dist}"
```

### Expected Behavior
The distance between identical vectors using the `COSINE` metric should be `0.0`. The result should strictly adhere to the range constraints of the metric type.

### Actual Behavior
The search operation returns a distance value greater than `1.0` (e.g., overflow value) when searching for the identical vector that was just inserted.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "目前，Milvus 支持这些类型的相似性度量：欧氏距离 (`L2`)、内积 (`IP`)、余弦相似度 (`COSINE`)..." (Milvus supports COSINE similarity). The mathematical contract of Cosine Similarity dictates that identical vectors have a similarity of 1.0 (distance 0.0).
- **Reference URL**: https://milvus.io/docs/zh/metric.md
- **Verification Status**: Logic Verified (No Doc Reference Needed)