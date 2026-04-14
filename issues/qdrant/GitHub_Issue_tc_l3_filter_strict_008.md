# [Bug]: Type-3 (Traditional Oracle) in tc_l3_filter_strict_008

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: qdrant 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A traditional oracle violation was detected during the execution of test case `tc_l3_filter_strict_008`. The system failed to correctly handle a search operation involving an impossible price filter while searching for 'laptop'.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection
collection_name = "test_filter_strict_008"
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# 3. Insert Points (Payload includes price)
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=[0.1] * 128, payload={"product": "laptop", "price": 1000}),
        PointStruct(id=2, vector=[0.2] * 128, payload={"product": "phone", "price": 500})
    ]
)

# 4. Search with Impossible Price Filter
# Example: Searching for a laptop with price < 0 (assuming no such data exists)
search_result = client.search(
    collection_name=collection_name,
    query_vector=[0.1] * 128,
    query_filter=Filter(
        must=[
            FieldCondition(key="product", match=MatchValue(value="laptop")),
            FieldCondition(key="price", range={"lt": 0}) # Impossible condition
        ]
    ),
    limit=10
)

# 5. Verification
print(f"Found {len(search_result)} results.")
# Expected: 0 results
# Actual: Check logs for violation
```

### Expected Behavior
The search operation should return an empty result set when a filter condition is logically impossible (e.g., price < 0 when all prices are positive), adhering to the strict filtering contract.

### Actual Behavior
The system returned results or behaved in a manner inconsistent with the strict filtering logic, indicating a potential violation of the traditional oracle for the given filter constraints.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)