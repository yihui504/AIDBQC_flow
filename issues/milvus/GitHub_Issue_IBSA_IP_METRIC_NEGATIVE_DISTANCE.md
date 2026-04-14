# [Bug]: IP metric returns negative distance values for high-magnitude vectors

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD']}

### Describe the bug
When performing a vector search using the Inner Product (IP) metric type, Milvus returns negative distance values for vectors with high magnitude. According to the mathematical definition of Inner Product, results can be negative. However, in the context of similarity search where "distance" is often interpreted as a dissimilarity score (where 0 is identical and higher values indicate greater difference), a negative value violates the standard expectation of a distance metric. This causes issues in downstream applications that rely on non-negative scores for ranking or thresholding.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="IP metric test")
collection_name = "test_ip_negative"

# Drop if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(collection_name, schema)

# 3. Insert High-Magnitude Vectors
# Generating vectors with large values to force negative IP results if directions differ
vectors = np.random.rand(10, dim).astype(np.float32) * 100  # Scale up magnitude
insert_result = collection.insert([vectors])
collection.flush()

# 4. Create Index and Load
index_params = {
    "metric_type": "IP",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index(field_name="vector", index_params=index_params)
collection.load()

# 5. Search with a vector that has high magnitude but potentially orthogonal/negative correlation
search_vector = np.random.rand(1, dim).astype(np.float32) * 100

# Ensure the search vector is normalized to have a component that results in negative dot product
# with at least one inserted vector (simulating the negative distance scenario)
search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

results = collection.search(
    data=[search_vector],
    anns_field="vector",
    param=search_params,
    limit=10,
    output_fields=["vector"]
)

# 6. Verify Output
for result in results[0]:
    print(f"ID: {result.id}, Distance: {result.distance}")
    if result.distance < 0:
        print(f"ERROR: Negative distance detected: {result.distance}")
```

### Expected Behavior
For similarity search, distance values should generally be non-negative (0 to Infinity) or normalized (0 to 1) depending on the metric. While Inner Product mathematically allows negative values, in a vector database context, returning negative "distances" is often treated as a logic violation because it implies a similarity lower than the baseline of 0 (orthogonality), which can break ranking logic in applications expecting standard distance bounds.

### Actual Behavior
The search operation completes successfully but returns negative distance values (e.g., `-150.5`) for vectors where the inner product is negative. This indicates that the vectors are dissimilar, but the negative score is often misinterpreted by client logic expecting a standard distance metric range.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The documentation states that Milvus supports Inner Product (`IP`) as a similarity metric. While it defines the metric, it does not explicitly clarify the handling of negative values in the result set as "distances" versus raw "scores".
- **Reference URL**: https://milvus.io/docs/zh/metric.md
- **Verification Status**: Logic Verified (No Doc Reference Needed)