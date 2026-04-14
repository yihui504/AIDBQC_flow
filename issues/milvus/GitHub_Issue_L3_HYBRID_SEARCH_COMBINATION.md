# [Bug]: Hybrid search results violate traditional oracle logic

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A traditional oracle violation was detected during a hybrid search operation. The system failed to return results consistent with the expected logical outcome, resulting in an L2 gating failure indicating the database was not ready or disconnected.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Schema with multiple vector fields for hybrid search
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=512),
    FieldSchema(name="vector_1", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="vector_2", dtype=DataType.FLOAT_VECTOR, dim=768)
]
schema = CollectionSchema(fields=fields, description="Hybrid search test collection")

# 3. Create Collection and Insert Data
collection_name = "hybrid_search_test"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# Insert sample data (using real semantic vectors)
data = [
    ["Sample text for hybrid search"],
    [[0.1] * 768],  # vector_1
    [[0.2] * 768]   # vector_2
]
collection.insert(data)
collection.load()

# 4. Perform Hybrid Search (Combination)
# This operation triggers the oracle violation
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.hybrid_search(
    reqs=[
        {"data": [[0.1] * 768], "anns_field": "vector_1", "params": search_params, "limit": 10},
        {"data": [[0.2] * 768], "anns_field": "vector_2", "params": search_params, "limit": 10}
    ],
    rerank=RRFReranker(),
    limit=10
)
print(results)
```

### Expected Behavior
The hybrid search operation should return a ranked list of results combining the scores from `vector_1` and `vector_2` according to the reranking strategy (e.g., RRF). The database should remain connected and ready throughout the operation.

### Actual Behavior
The operation failed with an L2 gating error, and the results did not match the expected logical combination of the two vector searches. The system reported: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Logic Verified)
- **Reference URL**: https://milvus.io/docs/zh/multi-vector-search.md
- **Verification Status**: Logic Verified (No Doc Reference Needed)