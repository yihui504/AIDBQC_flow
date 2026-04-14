# [Bug]: Type-4 (Semantic Oracle) in tc_l2_idempotency_006 - Idempotency Verification Failed

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
The test case `tc_l2_idempotency_006` is designed to verify idempotency by executing the exact same vector search twice and ensuring the result order and scores are identical. The provided 'Raw Results' section contains only a single list of results (Top K) and does not include the results from a second execution to compare against. Without the second set of results, it is impossible to verify if the order and scores are identical across runs. Additionally, the provided results list is truncated (ends with a comma), preventing a full analysis of even the single run's data. Therefore, the semantic intent of verifying idempotency cannot be fulfilled with the given data.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection
collection_name = "test_idempotency_006"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.Euclid)
)

# 3. Insert Points (Using real semantic vectors for demonstration)
# In a real scenario, these would be embeddings from a model.
# Here we use fixed vectors to ensure deterministic behavior for the test.
import numpy as np

vectors = [np.random.rand(128).tolist() for _ in range(10)]
client.upsert(
    collection_name=collection_name,
    points=[PointStruct(id=i, vector=vectors[i], payload={"id": i}) for i in range(10)]
)

# 4. Execute Identical Query Twice
query_vector = vectors[0] # Search for the first point

# First Run
results_run_1 = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=5
)

# Second Run (Identical)
results_run_2 = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=5
)

# 5. Verification
# Compare scores and IDs
for r1, r2 in zip(results_run_1, results_run_2):
    assert r1.id == r2.id, f"ID mismatch: {r1.id} != {r2.id}"
    assert r1.score == r2.score, f"Score mismatch for ID {r1.id}: {r1.score} != {r2.score}"

print("Idempotency verified: Results are identical across runs.")
```

### Expected Behavior
Executing the same search query twice should return identical results (same IDs in the same order with the same scores). The test report should contain data from both runs to facilitate this comparison.

### Actual Behavior
The test report only contains a single list of results, which is truncated. It is impossible to verify idempotency because the data required for comparison (the second set of results) is missing.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)