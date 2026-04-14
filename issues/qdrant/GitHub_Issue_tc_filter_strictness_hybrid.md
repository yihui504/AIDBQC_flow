# [Bug]: Hybrid search filter strictness violation in tc_filter_strictness_hybrid

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A Traditional Oracle violation (Type-3) was detected during hybrid search operations. The system returned results that violated the expected strictness of the applied filter, specifically when querying for items matching a condition like "shoes under 50 dollars". The search results included points that should have been excluded by the filter criteria, indicating a potential issue in how filters are applied or respected during hybrid query execution.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# 1. Initialize client
client = QdrantClient(url="http://localhost:6333")

# 2. Create collection
collection_name = "test_filter_strictness"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# 3. Insert points with specific payload attributes
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=[0.1] * 128, payload={"price": 40, "product": "shoes"}),
        PointStruct(id=2, vector=[0.2] * 128, payload={"price": 60, "product": "shoes"}),
        PointStruct(id=3, vector=[0.3] * 128, payload={"price": 30, "product": "shirt"}),
    ],
)

# 4. Perform search with filter (Price < 50)
# Expected: Only points with price < 50 (IDs 1, 3)
results = client.search(
    collection_name=collection_name,
    query_vector=[0.1] * 128,
    query_filter=Filter(
        must=[
            FieldCondition(key="price", range={"lt": 50})
        ]
    ),
    limit=10
)

# 5. Verify strictness
for res in results:
    assert res.payload["price"] < 50, f"Filter violation: Point {res.id} has price {res.payload['price']}"
```

### Expected Behavior
All search results returned by the hybrid query should strictly satisfy the filter conditions provided in the request. In the example above, no point with a `price` greater than or equal to 50 should be present in the output.

### Actual Behavior
The search operation returned points where the payload values violated the filter condition (e.g., items with prices >= 50 were included in the results for a "price < 50" filter). This indicates a failure in the filtering logic during the search execution.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)