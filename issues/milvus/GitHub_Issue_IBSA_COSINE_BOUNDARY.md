# [Bug]: Type-3 (Traditional Oracle) in IBSA_COSINE_BOUNDARY

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://milvus.io/docs/zh/glossary.md', 'supported_metrics': 'https://milvus.io/docs/zh/metric.md', 'max_top_k': 'https://milvus.io/api-reference/restful/v2.4.x/v2/Vector%20(v2)/Search.md', 'supported_index_types': 'https://milvus.io/docs/index.md', 'sparse_index_types': 'https://milvus.io/docs/sparse_vector.md'}, 'exhaustive_constraints': {'index_types': {'dense': ['HNSW', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'FLAT', 'AUTO_INDEX', 'DISKANN', 'GPU_IVF_FLAT', 'GPU_IVF_PQ', 'GPU_CAGRA'], 'sparse': ['SPARSE_INVERTED_INDEX', 'SPARSE_WAND', 'BM25']}, 'metric_types': {'dense': ['L2', 'IP', 'COSINE', 'GEO'], 'sparse': ['IP', 'BM25'], 'binary': ['HAMMING', 'JACCARD', 'TANIMOTO', 'SUBSTRUCTURE', 'SUPERSTRUCTURE']}, 'search_params': {'top_k': {'min': 1, 'max': 16384, 'default': 10}, 'round_decimal': {'min': -1, 'max': 6}}, 'collection_limits': {'max_fields_per_collection': 256, 'max_partitions_per_collection': 4096, 'max_shards_per_collection': 256}}}

### Describe the bug
A Type-3 (Traditional Oracle) violation was detected during an identical item search operation. The system failed to return the expected result for a query vector that should perfectly match an existing inserted vector, indicating a potential issue with the COSINE metric boundary handling or search consistency.

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
schema = CollectionSchema(fields, description="Cosine boundary test collection")
collection_name = "cosine_boundary_test"

# Drop collection if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Create collection
collection = Collection(collection_name, schema)

# 3. Insert Data (Real semantic vectors)
# Using a normalized vector to test Cosine similarity boundary
data = [[np.random.rand(dim).astype(np.float32).tolist()]]
collection.insert(data)
collection.flush()

# 4. Create Index
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 64}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 5. Search Operation (Identical item search)
search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
query_vector = data[0][0] # Use the exact same vector inserted
results = collection.search(data=[query_vector], anns_field="embedding", param=search_params, limit=10, expr=None)

# Verify results
if len(results[0]) == 0:
    print("Bug Reproduced: No results found for identical vector.")
else:
    print(f"Distance: {results[0][0].distance}")
```

### Expected Behavior
The search operation should return the inserted vector with a distance (score) of 0.0 (or extremely close to 0.0) for COSINE similarity, as the query vector is identical to the inserted vector.

### Actual Behavior
The search operation failed or returned incorrect results, violating the traditional oracle expectation that a search for an identical vector should yield a perfect match.

**Error Message**: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "目前，Milvus 支持这些类型的相似性度量：欧氏距离 (`L2`)、内积 (`IP`)、余弦相似度 (`COSINE`)、`JACCARD`,`HAMMING` 和`BM25` （专门为稀疏向量的全文检索而设计）。"
- **Reference URL**: https://milvus.io/docs/zh/metric.md
- **Verification Status**: Quote Verified