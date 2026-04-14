# [Bug]: Search operation fails with 'Database not ready or disconnected' on unloaded collection

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A search operation executed on a collection before it is loaded into memory results in a failure with the error message "L2 Gating Failed: Database not ready or disconnected." This violates the expected behavior where the system should handle the state gracefully or explicitly require the load operation before searching.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import numpy as np

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Schema
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="test collection")

# 3. Create Collection and Insert Data
collection = Collection(name="test_search_unloaded", schema=schema)
data = [np.random.rand(10, dim).tolist()]
collection.insert(data)

# 4. Search WITHOUT Loading (Triggering the bug)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=np.random.rand(1, dim).tolist(),
    anns_field="embedding",
    param=search_params,
    limit=10,
    expr=None
)
```

### Expected Behavior
According to the consistency and state management principles, the search should either:
1. Explicitly raise an error indicating the collection is not loaded (e.g., "Collection not loaded"), or
2. Implicitly load the collection if the system supports auto-loading.

The current error "Database not ready or disconnected" is misleading as the database is connected, but the specific collection state is not ready for querying.

### Actual Behavior
The operation fails with the error:
`L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "Milvus 是一个存储和计算分离的系统... **查询节点** 负责处理搜索等计算任务... 由于网络延迟，查询节点通常无法保存最新的流数据。"
- **Reference URL**: https://milvus.io/docs/zh/consistency.md
- **Verification Status**: Quote Verified