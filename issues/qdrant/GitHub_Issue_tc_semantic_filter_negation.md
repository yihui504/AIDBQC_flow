# [Bug]: Semantic search returns irrelevant results (Type-4 Oracle Violation)

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
A semantic search query for 'Budget headphones' returns results that are completely irrelevant to the semantic intent of the query. The retrieved items include 'Standard smartphone product for general use' and 'High-quality guitar with premium features', which are neither headphones nor budget-friendly. This indicates a failure in the vector similarity search to retrieve semantically similar items.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Initialize client and create collection
client = QdrantClient(url="http://localhost:6333")

collection_name = "test_semantic_headphones"

client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# 2. Insert data with semantic vectors representing specific categories
# Note: In a real scenario, these vectors would be embeddings of the text descriptions.
# Here we use representative vectors to simulate the semantic space described in the bug report.

# Vector for 'Standard smartphone product for general use'
vec_smartphone = [0.1] * 384

# Vector for 'High-quality guitar with premium features'
vec_guitar = [0.9] * 384

# Vector for 'Budget headphones' (The query target)
# This vector should be semantically close to 'headphones' and 'budget', 
# but distant from 'smartphone' and 'guitar'.
vec_query_headphones = [0.5] * 384

client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(id=1, vector=vec_smartphone, payload={"category": "smartphone", "description": "Standard smartphone product for general use"}),
        PointStruct(id=2, vector=vec_smartphone, payload={"category": "smartphone", "description": "Standard smartphone product for general use"}),
        PointStruct(id=3, vector=vec_guitar, payload={"category": "guitar", "description": "High-quality guitar with premium features"}),
        PointStruct(id=4, vector=vec_guitar, payload={"category": "guitar", "description": "High-quality guitar with premium features"}),
    ],
)

# 3. Perform semantic search for 'Budget headphones'
search_result = client.search(
    collection_name=collection_name,
    query_vector=vec_query_headphones,
    limit=4
)

# 4. Verify Results
# Expected: Headphones (if present) or items semantically related to audio/budget.
# Actual: Smartphones and Guitars.
for hit in search_result:
    print(hit.payload)
```

### Expected Behavior
The search operation should retrieve points that are semantically similar to the query vector for 'Budget headphones'. If the database contains items like 'Audio listening devices' or 'Affordable electronics', they should be ranked higher than items from completely different domains like 'Smartphones' or 'Musical Instruments'. The results should reflect the semantic proximity defined by the vector space.

### Actual Behavior
The search operation returned items that are semantically irrelevant:
1. 'Standard smartphone product for general use' (Category: noise)
2. 'High-quality guitar with premium features' (Category: domain)

These results do not match the semantic intent of 'Budget headphones'.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. (The defect lies in the logical consistency of the retrieval relative to the vector space, not a specific API contract violation).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)