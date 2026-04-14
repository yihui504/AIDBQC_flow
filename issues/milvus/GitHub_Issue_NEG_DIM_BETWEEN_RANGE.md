# [Bug]: Type-4 Semantic Oracle Violation in NEG_DIM_BETWEEN_RANGE

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready'], 'source_urls': {'dimension_constraint': 'https://milvus.io/docs/zh/glossary.md', 'supported_metrics': 'https://milvus.io/docs/zh/metric.md', 'max_top_k': 'https://milvus.io/api-reference/restful/v2.4.x/v2/Vector%20(v2)/Search.md', 'supported_index_types': 'https://milvus.io/docs/index.md', 'sparse_index_types': 'https://milvus.io/docs/sparse_vector.md'}, 'exhaustive_constraints': {'index_types': {'dense': ['HNSW', 'IVF_FLAT', 'IVF_SQ8', 'IVF_PQ', 'FLAT', 'AUTO_INDEX', 'DISKANN', 'GPU_IVF_FLAT', 'GPU_IVF_PQ', 'GPU_CAGRA'], 'sparse': ['SPARSE_INVERTED_INDEX', 'SPARSE_WAND', 'BM25']}, 'metric_types': {'dense': ['L2', 'IP', 'COSINE', 'GEO'], 'sparse': ['IP', 'BM25'], 'binary': ['HAMMING', 'JACCARD', 'TANIMOTO', 'SUBSTRUCTURE', 'SUPERSTRUCTURE']}, 'search_params': {'top_k': {'min': 1, 'max': 16384, 'default': 10}, 'round_decimal': {'min': -1, 'max': 6}}, 'collection_limits': {'max_fields_per_collection': 256, 'max_partitions_per_collection': 4096, 'max_shards_per_collection': 256}}}

### Describe the bug
The system failed to correctly handle an adversarial input test case (NEG_DIM_BETWEEN_RANGE) designed to verify dimension constraints. The semantic intent was to validate that the system rejects a dimension of 128 against a specific allowed list ([2, 32768]) at the L1 (Contract/Validation) layer. However, the execution failed at the L2 (Gating/Database connection) layer with the error "L2 Gating Failed: Database not ready or disconnected." This indicates a semantic oracle violation where the system failed to process the request due to a backend connection issue rather than a proper contract validation check.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connection logic
connections.connect(host="localhost", port="19530")

# 2. Define schema with a specific dimension (128) that is not in the allowed list [2, 32768]
# Note: This test assumes the environment enforces the legacy list constraint.
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="Test collection for dimension validation")

# 3. Attempt to create the collection
# Expected: L1 Validation Error (Dimension not allowed)
# Actual: L2 Gating Failed (Database not ready or disconnected)
collection_name = "test_neg_dim"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

collection = Collection(name=collection_name, schema=schema)
```

### Expected Behavior
The system should reject the collection creation request at the L1 (Contract/Validation) layer with a specific error indicating that the dimension 128 is not allowed (or is out of the supported range), rather than failing due to a database connection error.

### Actual Behavior
The operation failed with the error: "L2 Gating Failed: Database not ready or disconnected." This indicates that the request was blocked by a backend connectivity issue (L2) rather than a semantic validation of the input parameters (L1).

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The test relies on the logical consistency of the validation layer (L1) catching invalid inputs before they reach the execution layer (L2).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)