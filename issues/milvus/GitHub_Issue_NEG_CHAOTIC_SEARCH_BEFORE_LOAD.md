# [Bug]: Search operation fails with 'Database not ready' error on newly created collection before load

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
When attempting to perform a vector search on a newly created collection that has not yet been explicitly loaded into memory, the operation fails with a `L2 Gating Failed: Database not ready or disconnected` error. This behavior violates the expected contract where Milvus should either automatically handle the loading of segments or return a standard error indicating that the collection is not loaded, rather than a generic 'database not ready' message.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connect to Milvus
connections.connect(host='localhost', port='19530')

# 2. Define Schema
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="test collection")

# 3. Create Collection
collection_name = "test_search_before_load"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)

# 4. Insert Data (Simulating data persistence)
import random
import numpy as np

entities = [
    [i for i in range(10)],  # PK
    [[random.random() for _ in range(dim)] for _ in range(10)]  # Vectors
]
collection.insert(entities)
collection.flush() # Ensure data is persisted

# 5. Search WITHOUT Loading (Triggering the bug)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
results = collection.search(
    data=[[random.random() for _ in range(dim)]], 
    anns_field="embeddings", 
    param=search_params, 
    limit=5, 
    expr=None
)
```

### Expected Behavior
According to Milvus architecture, data must be loaded into query nodes before searching. The expected behavior is one of the following:
1. Milvus automatically loads the relevant segments (lazy loading) and returns the search results.
2. Milvus returns a specific error message indicating that the collection is not loaded (e.g., `collection not loaded`), prompting the user to call `collection.load()`.

### Actual Behavior
The search operation fails with the following error:
`L2 Gating Failed: Database not ready or disconnected.`

This error message is misleading as the database is connected and the collection exists. It implies a system-level unavailability rather than a state issue with the specific collection.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "Milvus 是一个存储和计算分离的系统... **查询节点** 负责处理搜索等计算任务... 由于网络延迟，查询节点通常无法保存最新的流数据。"
- **Reference URL**: https://milvus.io/docs/zh/consistency.md
- **Verification Status**: Quote Verified. The documentation confirms the separation of storage and compute, implying that data must be available at the query node (loaded) for search operations. The current error message does not accurately reflect this architectural requirement.