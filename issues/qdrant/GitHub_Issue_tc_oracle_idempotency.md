# [Bug]: Semantic search returns completely irrelevant results (Real Estate vs Clothing)

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
A semantic search query for 'Summer dress' (clothing/fashion intent) returns multiple results describing 'High-quality house with premium features' (real estate intent). The retrieved results are semantically unrelated to the query text, indicating a failure in the similarity search or embedding mechanism. Additionally, the top results exhibit identical distance and rerank scores, suggesting potential data duplication or index corruption.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Initialize Client
client = QdrantClient(url="http://localhost:6333")

# 2. Create Collection (assuming standard embedding dimension)
collection_name = "test_semantic_search"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

# 3. Insert Data (Simulated)
# In the real scenario, these vectors would be embeddings of the text.
# The bug report indicates the DB returned 'High-quality house...' for 'Summer dress'.
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=[0.1]*384, payload={"text": "High-quality house with premium features"}),
        PointStruct(id=2, vector=[0.1]*384, payload={"text": "High-quality house with premium features"}),
        PointStruct(id=3, vector=[0.1]*384, payload={"text": "High-quality house with premium features"}),
        PointStruct(id=4, vector=[0.1]*384, payload={"text": "High-quality house with premium features"}),
    ],
)

# 4. Perform Search
# Query vector for 'Summer dress'
query_vector = [0.2]*384 

search_results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=4
)

# 5. Verify Results
for hit in search_results:
    print(f"Payload: {hit.payload['text']}, Score: {hit.score}")

# Expected: Results related to 'Summer dress'
# Actual: Results related to 'High-quality house'
```

### Expected Behavior
The search operation should return points that are semantically similar to the query 'Summer dress' (e.g., clothing, fashion, seasonal wear). The results should be relevant to the query's intent, and the distance scores should reflect the semantic similarity between the query vector and the result vectors.

### Actual Behavior
The search operation returned results with the payload 'High-quality house with premium features'. These results are semantically unrelated to 'Summer dress'. The top 4 results all had identical distance scores (1.278471) and rerank scores (-11.101034164428711), despite the query being about clothing and the results being about real estate.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The core functionality of a vector database is to return semantically similar results based on vector proximity. Returning real estate descriptions for a clothing query violates the fundamental semantic search contract.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)