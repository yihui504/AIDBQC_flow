# [Bug]: COSINE Metric Returns Distance > 1.0 for Identical Vectors (Precision Overflow)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: v2.6.12 (also reproduced on v2.3.7)
- **Deployment mode(standalone or cluster)**: standalone (Docker)
- **MQ type(rocksmq, pulsar or kafka)**: rocksmq
- **SDK version(e.g. pymilvus v2.0.0rc2)**: pymilvus v2.6.12
- **OS(Ubuntu or CentOS)**: Windows / Linux (Docker)
- **CPU/Memory**: N/A (Mathematical precision issue, hardware independent)
- **GPU**: N/A
- **Others**: Vector config: Dimensions: 128, Metric: `COSINE`, Index: `IVF_FLAT`

### Current Behavior
When performing a vector search using the `COSINE` metric type, the distance returned for identical vectors is strictly greater than `1.0` (e.g., `1.0000001192092896`). 

This happens due to unhandled floating-point precision loss (imprecision) during dot product/cosine calculation at the C++ core (Segcore/Knowhere) without proper boundary clamping before returning the result to the client.

### Expected Behavior
The calculation result for identical normalized vectors using the `COSINE` metric should be bounded. It should strictly adhere to the mathematical definition of Cosine Similarity/Distance (e.g. `<= 1.0`). 

It is highly recommended to add a clamp function (e.g., `std::min(1.0f, std::max(-1.0f, result))`) at the core execution node before returning the metric to the client to avoid mathematical invariant violations.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host="127.0.0.1", port="19530")

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
np.random.seed(42)
data = np.random.rand(10000, dim).astype(np.float32)
# Normalize manually to ensure unit length
norms = np.linalg.norm(data, axis=1, keepdims=True)
vectors = data / norms

collection.insert([vectors])
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
    data=vectors[:100], 
    anns_field="embeddings", 
    param=search_params, 
    limit=1, 
    expr=None
)

# 6. Check Result
bug_reproduced = False
for i, hits in enumerate(results):
    dist = hits[0].distance
    # Check if distance strictly exceeds 1.0 boundary due to float imprecision
    if dist > 1.0:
        print(f"BUG REPRODUCED! Distance {dist} > 1.0 for vector {i}")
        bug_reproduced = True
        break

if not bug_reproduced:
    print(f"Bug not reproduced or fixed. Max distance observed: {max(hits[0].distance for hits in results)}")
```

### Milvus Log
N/A (This is a silent logic/precision bug that does not trigger errors or stack traces in the server logs).

### Anything else?
- **Violated Contract Type**: Mathematical Invariant (Traditional Oracle)
- **Official Docs Reference**: "Milvus supports these types of similarity metrics: Euclidean distance (`L2`), Inner product (`IP`), Cosine similarity (`COSINE`)..." 
- **Reference URL**: https://milvus.io/docs/metric.md
- **Suggested Fix**: Apply `std::min` / `std::max` clipping on the final distance output in the query node / Segcore / Knowhere for the `COSINE` metric.