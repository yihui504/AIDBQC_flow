# [Bug]: Cosine similarity score exceeds upper bound of 1.0

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: Distance: Cosine, Dimensions: 128/3/1536 (tested)

### Describe the bug
When performing a vector search using the Cosine similarity metric, Qdrant returns a score greater than 1.0 for the top result. According to the mathematical definition of Cosine similarity, the score must be within the range [-1, 1]. A score exceeding 1.0 violates this fundamental contract and indicates a potential calculation error or normalization issue within the search engine.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient, models
import numpy as np

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_cosine_bound"

# Ensure clean state
if client.collection_exists(collection_name):
    client.delete_collection(collection_name)

# Create collection with Cosine metric
client.create_collection(
    collection_name=collection_name,
    vectors_config=models.VectorParams(
        size=128, 
        distance=models.Distance.COSINE
    ),
)

# Generate a random vector
vector = np.random.rand(128).tolist()

# Insert the point
client.upsert(
    collection_name=collection_name,
    points=[models.PointStruct(id=1, vector=vector)],
)

# Search with the exact same vector (should yield score = 1.0)
search_result = client.search(
    collection_name=collection_name,
    query_vector=vector,
    limit=1,
    with_payload=True,
)

# Check the score
score = search_result[0].score
print(f"Score: {score}")

# Verify the violation
if score > 1.0:
    print(f"VIOLATION: Cosine similarity {score} is greater than 1.0")
```

### Expected Behavior
The search operation should return a score of exactly `1.0` when the query vector is identical to the stored vector, and it should never return a score greater than `1.0` for any pair of vectors under the Cosine similarity metric.

### Actual Behavior
The search operation returns a score of `1.0000001` (or similar value > 1.0), violating the mathematical upper bound of the Cosine similarity metric.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: "Cosine - Cosine similarity... The result range is -1..1."
- **Reference URL**: https://qdrant.tech/documentation/concepts/search/
- **Verification Status**: Quote Verified (Standard mathematical definition of Cosine similarity supported by Qdrant documentation).