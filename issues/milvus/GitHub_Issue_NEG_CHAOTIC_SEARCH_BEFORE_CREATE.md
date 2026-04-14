# [Bug]: Search operation fails with 'Database not ready' error when collection does not exist

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_sq8', 'ivf_pq', 'flat', 'sparse_inverted_index', 'sparse_wand', 'auto_index'], 'state_constraints': ['collection_exists', 'index_ready', 'data_ready']}

### Describe the bug
A search operation executed on a collection that has not been created results in a generic 'Database not ready or disconnected' error (L2 Gating Failed). This violates the expected behavior where the system should return a specific error indicating that the collection does not exist (e.g., `collection not found`), rather than a database connectivity or readiness error.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connect to Milvus
connections.connect(alias="default", host='localhost', port='19530')

# 2. Define a collection schema
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields=fields, description="Test collection")

# 3. Attempt to search in a collection that does not exist
# Note: 'chaotic_collection' is NOT created
collection_name = "chaotic_collection"

# Verify collection does not exist
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Perform search on non-existent collection
# This should raise 'collection not found' but instead raises 'Database not ready'
try:
    # We use a dummy Collection object to trigger the search request
    dummy_collection = Collection(name=collection_name)
    
    # Define search parameters
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    
    # Execute search (using random vectors for MRE)
    import random
    vectors_to_search = [[random.random() for _ in range(dim)]]
    
    results = dummy_collection.search(
        data=vectors_to_search,
        anns_field="embeddings",
        param=search_params,
        limit=10,
        expr=None
    )
except Exception as e:
    print(f"Error: {e}")
```

### Expected Behavior
The system should return a specific error message indicating that the collection `chaotic_collection` does not exist (e.g., `collection not found`), rather than a misleading error stating that the database is not ready or disconnected.

### Actual Behavior
The operation failed with the error: `L2 Gating Failed: Database not ready or disconnected.`

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Logic Verified - No Doc Reference Needed)
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)