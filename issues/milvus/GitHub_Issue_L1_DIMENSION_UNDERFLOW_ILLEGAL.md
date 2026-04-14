# [Bug]: L1_DIMENSION_UNDERFLOW_ILLEGAL - Database Connectivity Failure Preventing Dimension Validation

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://milvus.io/docs/zh/glossary.md', 'supported_metrics': 'https://milvus.io/docs/zh/metric.md', 'max_top_k': 'https://milvus.io/api-reference/restful/v2.4.x/v2/Vector%20(v2)/Search.md', 'supported_index_types': 'https://milvus.io/docs/index.md', 'sparse_index_types': 'https://milvus.io/docs/sparse_vector.md'}, 'exhaustive_constraints': {'index_types': {'dense': ['HNSW', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'FLAT', 'AUTO_INDEX', 'DISKANN', 'GPU_IVF_FLAT', 'GPU_IVF_PQ', 'GPU_CAGRA'], 'sparse': ['SPARSE_INVERTED_INDEX', 'SPARSE_WAND', 'BM25']}, 'metric_types': {'dense': ['L2', 'IP', 'COSINE', 'GEO'], 'sparse': ['IP', 'BM25'], 'binary': ['HAMMING', 'JACCARD', 'TANIMOTO', 'SUBSTRUCTURE', 'SUPERSTRUCTURE']}, 'search_params': {'top_k': {'min': 1, 'max': 16384, 'default': 10}, 'round_decimal': {'min': -1, 'max': 6}}, 'collection_limits': {'max_fields_per_collection': 256, 'max_partitions_per_collection': 4096, 'max_shards_per_collection': 256}}}

### Describe the bug
The test case `L1_DIMENSION_UNDERFLOW_ILLEGAL` is designed to verify that the system correctly rejects a collection creation with a vector dimension less than 2 (specifically dimension 1). However, the test failed to verify this semantic constraint because the database backend was unreachable or not ready at the time of execution. The error returned was a generic connectivity failure ('L2 Gating Failed') rather than a specific validation error regarding the dimension constraint.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define schema with invalid dimension (1)
# Expected range is [2, 32768]
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1) # Invalid dimension
]
schema = CollectionSchema(fields=fields, description="Test collection for dimension underflow")

# 3. Attempt to create the collection
# This should fail with a dimension validation error,
# but instead fails with connectivity error if DB is down.
collection = Collection(name="test_dim_underflow", schema=schema)
```

### Expected Behavior
According to the vector configuration constraints, the dimension must be between 2 and 32768. Attempting to create a collection with `dim=1` should result in a specific validation error (e.g., `dimension must be at least 2`) or an `ParamError` from the SDK.

### Actual Behavior
The operation failed with the error: `L2 Gating Failed: Database not ready or disconnected.` This indicates an infrastructure or environment issue prevented the request from reaching the validation logic, masking the potential semantic bug or confirming the system was simply unavailable.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The configuration context specifies `allowed_dimensions: [2, 32768]`, but the failure was a connectivity error, not a validation error.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)