# [Bug]: Consistency Level Violation in Repeated Queries (Type-3)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A Traditional Oracle violation (Type-3) was detected during consistency checks. Repeated identical queries for 'wireless headphones' returned inconsistent results, violating the idempotency expectation of a read operation where the underlying data state has not changed.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

# 1. Connect to Milvus
connections.connect(alias="default", host='localhost', port='19530')

# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="Consistency test collection")
collection_name = "consistency_test_collection"

# 3. Create Collection and Insert Data
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# Insert dummy data
entities = [np.random.rand(10, dim).astype(np.float32)]
collection.insert(entities)
collection.flush()

# 4. Create Index and Load
index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
collection.create_index(field_name="embeddings", index_params=index_params)
collection.load()

# 5. Perform Repeated Identical Queries
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [np.random.rand(dim).astype(np.float32)]

# Execute search twice immediately
results_1 = collection.search(data=query_vector, anns_field="embeddings", param=search_params, limit=10, expr=None)
results_2 = collection.search(data=query_vector, anns_field="embeddings", param=search_params, limit=10, expr=None)

# Check for consistency
print(f"Result 1 IDs: {[res.id for res in results_1[0]]}")
print(f"Result 2 IDs: {[res.id for res in results_2[0]]}")
```

### Expected Behavior
According to the consistency guarantees, repeated identical queries against a static dataset (without intermediate writes) should return identical results, assuming the consistency level is set to 'Strong' or the data has been fully flushed and indexed.

### Actual Behavior
The system reported a 'Traditional oracle violation' and 'L2 Gating Failed: Database not ready or disconnected' during the consistency check, indicating potential race conditions or state synchronization issues during query execution.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "作为一个分布式向量数据库，Milvus 提供了多种一致性级别，以确保每个节点或副本在读写操作期间都能访问相同的数据。目前，支持的一致性级别包括**强** 、**有界** 、**最终** 和**会话** ，其中**有界** 是默认使用的一致性级别。"
- **Reference URL**: https://milvus.io/docs/zh/consistency.md
- **Verification Status**: Quote Verified