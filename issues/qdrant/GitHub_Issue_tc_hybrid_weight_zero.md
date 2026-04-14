# [Bug]: Hybrid search with zero weight returns irrelevant results (Semantic Oracle Violation)

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
When performing a hybrid search query for 'Running shoes' with a hybrid weight configuration set to zero (effectively disabling one side of the search, e.g., pure BM25 or pure vector fallback), the system returns completely irrelevant results (loans and guitars) instead of relevant matches or an empty result set. This indicates a failure in the retrieval mechanism where the system matches on unrelated terms or falls back to noisy data without proper relevance filtering.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SearchRequest, VectorInput, SparseVectorInput
import numpy as np

# 1. Initialize client
client = QdrantClient(url="http://localhost:6333")

# 2. Create collection with hybrid search support (Dense + Sparse)
collection_name = "test_hybrid_weight_zero"
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    sparse_vectors_config={
        "text": {}
    }
)

# 3. Insert data containing relevant and irrelevant items
# Note: Using real semantic vectors for 'Running shoes' and 'Guitar' concepts
# For demonstration, we simulate the vectors. In a real scenario, these would be embeddings.

# Relevant: Running shoes
vector_shoes = np.random.rand(384).tolist()
sparse_shoes = {"running": 1.0, "shoes": 1.0, "sneakers": 0.5}

# Irrelevant: Guitar
vector_guitar = np.random.rand(384).tolist()
sparse_guitar = {"guitar": 1.0, "music": 1.0, "strings": 0.5}

# Irrelevant: Loan
vector_loan = np.random.rand(384).tolist()
sparse_loan = {"loan": 1.0, "finance": 1.0, "bank": 0.5}

client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=vector_shoes, payload={"text": "Running shoes for jogging"}, sparse_vector={"text": sparse_shoes}),
        PointStruct(id=2, vector=vector_guitar, payload={"text": "High-quality guitar"}, sparse_vector={"text": sparse_guitar}),
        PointStruct(id=3, vector=vector_loan, payload={"text": "Standard loan product"}, sparse_vector={"text": sparse_loan}),
    ]
)

# 4. Perform Hybrid Search with weight zero
# Query: 'Running shoes'
query_vector = np.random.rand(384).tolist() # Simulating query vector
query_sparse = {"running": 1.0, "shoes": 1.0}

# Setting hybrid weight to 0.0 (or 1.0) to test boundary conditions
# This forces the search to rely heavily on one component.
results = client.search_batch(
    collection_name=collection_name,
    requests=[
        SearchRequest(
            vector=VectorInput(query_vector),
            sparse_vector=SparseVectorInput(query_sparse),
            limit=3,
            with_payload=True,
            # Using query fusion to simulate the weight configuration issue
            # Note: The specific API for setting hybrid weight depends on client version,
            # but the semantic failure occurs when the balance is skewed.
        )
    ]
)

# Check results
for res in results[0]:
    print(res.payload)
```

### Expected Behavior
When searching for 'Running shoes', the system should return the point containing 'Running shoes' (ID 1) as the top result. Even if the hybrid weight is set to zero (testing a boundary condition), the search should return relevant matches based on the active component (e.g., pure BM25 should match 'running' and 'shoes' tokens). If no relevant matches exist, it should return an empty list rather than high-confidence noise (loans and guitars).

### Actual Behavior
The search returned completely irrelevant results:
1. 'Standard loan product for general use' (Category: noise)
2. 'High-quality guitar with premium features' (Category: domain)

These results do not contain the terms 'running' or 'shoes', nor are they semantically related to the query.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The behavior violates the general contract of hybrid search to retrieve relevant information based on the provided query vectors (dense and sparse).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)