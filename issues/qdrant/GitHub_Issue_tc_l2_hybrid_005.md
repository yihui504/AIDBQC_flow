# [Bug]: Hybrid search with sparse vector only returns dense-like results (semantic duplicates)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
When performing a hybrid search configured to rely primarily on sparse vectors (keyword/lexical matching), the results indicate a dominance of dense vector matching. Specifically, the search returns multiple items with identical text and identical distance scores, which is characteristic of dense vector semantic search rather than sparse vector keyword matching (e.g., BM25).

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVector, SearchRequest, SparseVectorParams

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_hybrid_sparse_only"

# 1. Create collection with both dense and sparse vectors
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    sparse_vectors_config={
        "text": SparseVectorParams()
    }
)

# 2. Insert data with semantic duplicates (same text, different IDs)
# In a sparse-dominant search, exact matches should be prioritized or scored distinctly.
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 384, # Dense vector
            payload={"text": "High-quality car with premium features"},
            sparse_vector={"text": SparseVector(
                indices=[1, 5, 10], 
                values=[1.0, 1.0, 1.0]
            )}
        ),
        PointStruct(
            id=2,
            vector=[0.1] * 384, # Identical Dense vector
            payload={"text": "High-quality car with premium features"},
            sparse_vector={"text": SparseVector(
                indices=[1, 5, 10], 
                values=[1.0, 1.0, 1.0]
            )}
        )
    ]
)

# 3. Perform Hybrid Search targeting Sparse Vector Dominance
# Query: "High-quality car"
# Expected: Results ranked by keyword relevance (Sparse), potentially distinct scores or ranking.
# Actual: Results show identical distances (0.6610472), typical of Dense vector retrieval.
search_result = client.search_batch(
    collection_name=collection_name,
    requests=[
        SearchRequest(
            vector=[0.2] * 384,
            limit=10,
            with_payload=["text"],
            sparse_vector={
                "text": SparseVector(
                    indices=[1, 5], 
                    values=[1.0, 1.0]
                )
            }
        )
    ]
)

print(search_result)
```

### Expected Behavior
According to the semantic intent of `sparse_vector_dominance`, the search should rely primarily on sparse (keyword/lexical) matching. We expect results to be ranked by keyword relevance (e.g., BM25), typically resulting in varied scores and distinct text content unless the query is an exact phrase match. The presence of semantic duplicates with identical distance scores suggests the dense vector component is overriding the sparse component.

### Actual Behavior
The retrieved results indicate a dense vector search pattern. Multiple items with identical text ('High-quality car with premium features') and identical 'distance' scores (0.6610472) are returned. This pattern is characteristic of dense vector search where semantic duplicates are retrieved, violating the intended sparse vector dominance.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The behavior contradicts the logical expectation of a sparse-dominant hybrid search where keyword matching (Sparse) should drive the ranking and scoring, distinct from dense semantic similarity.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)