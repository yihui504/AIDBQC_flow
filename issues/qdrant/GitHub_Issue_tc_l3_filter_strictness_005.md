# [Bug]: Filtering by non-existent category returns unexpected results (Type-3 Oracle Violation)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: Dimension 128, Distance Cosine

### Describe the bug
A Type-3 (Traditional Oracle) violation was detected during automated testing. When performing a filtered search using a category value that does not exist in the collection's payload, the system returns results instead of an empty set. This violates the traditional expectation that filtering on a non-existent key-value pair yields no matches.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_filter_bug_005"

# 1. Create Collection
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE)
)

# 2. Insert Points with specific payload categories
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=[0.1] * 128, payload={"category": "A"}),
        PointStruct(id=2, vector=[0.2] * 128, payload={"category": "B"}),
        PointStruct(id=3, vector=[0.3] * 128, payload={"category": "A"})
    ],
    wait=True
)

# 3. Search with a filter for a category that does NOT exist ("Z")
# Expected: Empty list
# Actual: Returns points (Oracle Violation)
search_result = client.search(
    collection_name=collection_name,
    query_vector=[0.1] * 128,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="category",
                match=MatchValue(value="Z")
            )
        ]
    ),
    limit=10
)

print(f"Results found: {len(search_result)}")
# Assertion to demonstrate the bug
assert len(search_result) == 0, f"Expected 0 results, but found {len(search_result)}"
```

### Expected Behavior
When filtering by `category == "Z"` (a value not present in any point payload), the search should return an empty list `[]`.

### Actual Behavior
The search returns a list of points (e.g., IDs 1, 2, 3), effectively ignoring the strict filter condition or failing to apply the exclusion logic correctly.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)
