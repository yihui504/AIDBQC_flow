# [Bug]: Type-3 (Traditional Oracle) in IBSA_IP_RANGE_NEGATIVE

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://milvus.io/docs/zh/glossary.md', 'supported_metrics': 'https://milvus.io/docs/zh/metric.md', 'max_top_k': 'https://milvus.io/api-reference/restful/v2.4.x/v2/Vector%20(v2)/Search.md', 'supported_index_types': 'https://milvus.io/docs/index.md', 'sparse_index_types': 'https://milvus.io/docs/sparse_vector.md'}, 'exhaustive_constraints': {'index_types': {'dense': ['HNSW', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'FLAT', 'AUTO_INDEX', 'DISKANN', 'GPU_IVF_FLAT', 'GPU_IVF_PQ', 'GPU_CAGRA'], 'sparse': ['SPARSE_INVERTED_INDEX', 'SPARSE_WAND', 'BM25']}, 'metric_types': {'dense': ['L2', 'IP', 'COSINE', 'GEO'], 'sparse': ['IP', 'BM25'], 'binary': ['HAMMING', 'JACCARD', 'TANIMOTO', 'SUBSTRUCTURE', 'SUPERSTRUCTURE']}, 'search_params': {'top_k': {'min': 1, 'max': 16384, 'default': 10}, 'round_decimal': {'min': -1, 'max': 6}}, 'collection_limits': {'max_fields_per_collection': 256, 'max_partitions_per_collection': 4096, 'max_shards_per_collection': 256}}}

### Describe the bug
A Type-3 (Traditional Oracle) violation was detected during an orthogonal vector search operation. The system failed to return valid results, reporting a readiness issue instead.

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
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="Orthogonal test collection")
collection_name = "ibsa_orthogonal_test"

# 3. Create Collection
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(collection_name, schema)

# 4. Insert Data (Orthogonal Vectors)
vectors = [[1.0 if i == j else 0.0 for j in range(dim)] for i in range(10)]
entities = [vectors]
collection.insert(entities)
collection.flush()

# 5. Create Index
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 6. Search (Triggering the failure)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [vectors[0]]
results = collection.search(data=query_vector, anns_field="embedding", param=search_params, limit=10, expr=None)
print(results)
```

### Expected Behavior
The search operation should complete successfully and return the nearest neighbors for the query vector, as the collection is loaded and the database is connected.

### Actual Behavior
The operation failed with the following error:
`L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)