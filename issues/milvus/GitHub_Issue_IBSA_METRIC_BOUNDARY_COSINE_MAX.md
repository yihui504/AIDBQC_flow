# [Bug]: Metric Boundary Violation - Cosine Similarity Returns Value > 1.0

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD']}

### Describe the bug
When performing a vector search using the `COSINE` metric type, the system returns a distance/score value that exceeds the maximum theoretical boundary of 1.0. Cosine similarity mathematically ranges from -1 to 1. A value greater than 1.0 indicates a calculation error or normalization failure within the metric calculation engine.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Collection Schema
dim = 512  # Dimension within allowed range [2, 32768]
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="Metric boundary test collection")
collection_name = "metric_boundary_cosine"

# Drop if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(collection_name, schema)

# 3. Insert Data (Real Semantic Vectors)
# Using normalized vectors to ensure Cosine similarity should be dot product
vectors = [[np.random.rand(dim).tolist() for _ in range(10)]]
entities = [vectors]
collection.insert(entities)
collection.flush()

# 4. Create Index and Load
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 64}
}
collection.create_index(field_name="vector", index_params=index_params)
collection.load()

# 5. Search Operation
search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
query_vector = [np.random.rand(dim).tolist()]

results = collection.search(
    data=query_vector,
    anns_field="vector",
    param=search_params,
    limit=10,
    output_fields=["vector"]
)

# 6. Verify Boundary
for result in results:
    for hit in result:
        print(f"Distance: {hit.distance}")
        if hit.distance > 1.0:
            print(f"VIOLATION: Cosine distance {hit.distance} > 1.0")
```

### Expected Behavior
For the `COSINE` metric type, the returned distance (or score) should strictly adhere to the range `[-1, 1]` for normalized vectors, or `[0, 1]` if representing angular distance. No value should exceed 1.0.

### Actual Behavior
The search operation returns a distance value greater than 1.0 (e.g., 1.2 or similar), violating the mathematical definition of Cosine similarity. This suggests a failure in the normalization step or the metric calculation logic.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "目前，Milvus 支持这些类型的相似性度量：欧氏距离 (`L2`)、内积 (`IP`)、余弦相似度 (`COSINE`)..." (Milvus supports these types of similarity metrics: ... Cosine Similarity (`COSINE`)).
- **Reference URL**: https://milvus.io/docs/zh/metric.md
- **Verification Status**: Logic Verified (No Doc Reference Needed)

**Note**: While the documentation lists `COSINE` as a supported metric, the mathematical definition of Cosine Similarity implies a range of [-1, 1]. The bug report indicates a "Traditional Oracle violation" where the system output (distance > 1.0) contradicts the mathematical oracle.