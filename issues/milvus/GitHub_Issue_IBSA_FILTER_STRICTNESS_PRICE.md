# [Bug]: Filtered search returns results violating strict boolean logic (price < 0)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: milvus latest
- **SDK/Client**: pymilvus
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [2, 32768], 'supported_metrics': ['L2', 'IP', 'COSINE', 'HAMMING', 'JACCARD'], 'max_top_k': 16384}

### Describe the bug
A filtered search operation with a strict boolean filter (`price < 0`) returns results that violate the logical constraint. Specifically, entities with a `price` value greater than or equal to 0 are returned, indicating a failure in the query execution engine to enforce the filter predicate correctly.

### Steps To Reproduce
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

# 1. Connect to Milvus
connections.connect(host="localhost", port="19530")

# 2. Define Schema with a price field
dim = 128
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
    FieldSchema(name="price", dtype=DataType.DOUBLE) # Scalar field for filtering
]
schema = CollectionSchema(fields, description="Test collection for filter strictness")
collection_name = "test_filter_price"

# Drop collection if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Create Collection
collection = Collection(name=collection_name, schema=schema)

# 3. Insert Data (Entities with price >= 0)
import random
entities = [
    [i for i in range(10)], # IDs
    [[random.random() for _ in range(dim)] for _ in range(10)], # Vectors
    [100.0, 250.5, 50.0, 10.0, 999.99, 0.0, 5.0, 33.33, 1000.0, 1.0] # Prices (all >= 0)
]
collection.insert(entities)
collection.flush()

# Create Index
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index(field_name="vector", index_params=index_params)
collection.load()

# 4. Execute Search with Strict Filter (price < 0)
search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
query_vector = [[random.random() for _ in range(dim)]] # Random vector

# Filter: price < 0 (Should return 0 results based on inserted data)
results = collection.search(
    data=query_vector,
    anns_field="vector",
    param=search_params,
    limit=5,
    expr='price < 0',
    output_fields=["price"]
)

# 5. Verify Results
if len(results[0]) > 0:
    for hit in results[0]:
        print(f"ID: {hit.id}, Price: {hit.entity.get('price')}, Distance: {hit.distance}")
else:
    print("No results returned (Expected behavior)")
```

### Expected Behavior
The search should return an empty result set because the inserted data contains only entities with `price >= 0`, and the filter expression `price < 0` strictly excludes all of them.

### Actual Behavior
The search returns entities with `price` values such as `100.0`, `250.5`, etc., which violate the `price < 0` condition. This indicates the filter is being ignored or applied incorrectly during the search execution.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "Filtered search" implies that results must satisfy the provided boolean expression. The failure to exclude entities where `price >= 0` when filtering for `price < 0` constitutes a fundamental violation of query logic.
- **Reference URL**: https://milvus.io/docs/zh/single-vector-search.md#Filtered-search
- **Verification Status**: Logic Verified (No Doc Reference Needed)