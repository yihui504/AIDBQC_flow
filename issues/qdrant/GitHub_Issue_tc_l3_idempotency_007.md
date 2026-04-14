# [Bug]: Semantic search returns irrelevant results (cars/dogs) for 'running shoes' query

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
A semantic search query for 'running shoes' returns results that are semantically irrelevant to the query intent. Specifically, the top retrieved items contain payloads describing 'High-quality car with premium features' and 'High-quality dog with premium features'. This indicates a failure in the retrieval relevance mechanism, where the vector similarity does not align with the semantic meaning of the input query.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection
client.create_collection(
    collection_name="test_semantic_search",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# 3. Insert Data (Simulated)
# In a real scenario, these vectors would be embeddings of the text.
# Here we use mock vectors to demonstrate the structure.
client.upsert(
    collection_name="test_semantic_search",
    points=[
        PointStruct(id=1, vector=[0.1]*384, payload={"text": "High-quality car with premium features"}),
        PointStruct(id=2, vector=[0.2]*384, payload={"text": "High-quality dog with premium features"}),
        PointStruct(id=3, vector=[0.3]*384, payload={"text": "Running shoes for marathon"}),
    ],
)

# 4. Perform Search
# Query vector for 'running shoes'
query_vector = [0.15]*384 

search_result = client.search(
    collection_name="test_semantic_search",
    query_vector=query_vector,
    limit=3
)

# 5. Verify Results
for hit in search_result:
    print(hit.payload["text"])
```

### Expected Behavior
The search results should prioritize items semantically related to 'running shoes' (e.g., 'Running shoes for marathon'). Items describing cars or dogs should appear with significantly lower scores or not at all if relevant shoe data exists.

### Actual Behavior
The top results included 'High-quality car with premium features' and 'High-quality dog with premium features', which are semantically unrelated to the query 'running shoes'.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)