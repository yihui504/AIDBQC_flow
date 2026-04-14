# [Bug]: Semantic search returns irrelevant results for 'Sony noise cancelling headphones' query

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic search query for 'Sony noise cancelling headphones' returns results that are semantically irrelevant to the user's intent. The system returns generic 'Standard headphones' and an unrelated 'headache product' instead of items matching the specific brand (Sony) or feature (noise cancelling) requested.

### Steps To Reproduce
```python
import weaviate
import os

# 1. Connection logic
client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        url="http://localhost:8080",
        grpc_port=50051
    )
)
client.connect()

# 2. Collection creation with specific parameters (simulating the test environment)
# Note: The collection likely contains data with generic descriptions like 'Standard headphones product'
collection = client.collections.get("ECommerceCollection")

# 3. The exact operation that triggered the failure
# Query for specific 'Sony noise cancelling headphones'
query_text = "Sony noise cancelling headphones"
response = collection.query.near_text(
    query=query_text,
    limit=4
)

# 4. Verification
for o in response.objects:
    print(o.properties)

client.close()
```

### Expected Behavior
According to Weaviate's semantic search capabilities, the system should return results ranked by semantic similarity. For a query specifically mentioning 'Sony' and 'noise cancelling', the top results should be semantically related to these attributes (e.g., Sony brand headphones, noise cancelling features), rather than generic 'Standard headphones' or completely unrelated 'headache products'.

### Actual Behavior
The query returned 4 items, but none were semantically relevant:
- Item 1 (ID 37): 'Standard headphones product for general use'
- Item 2 (ID 33): 'Standard headphones product for general use'
- Item 3 (ID 32): 'Standard headphones product for general use'
- Item 4 (ID 40): 'Standard headache product for general use'

The results failed to match the specific intent (Sony/Noise Cancelling) and included a 'headache product', indicating a failure in the semantic ranking or vectorization quality.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The general documentation states Weaviate supports "searches based on both semantic similarity and keywords" and "allows for more relevant results even when the query terms don’t exactly match the stored data." However, in this case, the results are semantically disconnected from the query.
- **Reference URL**: https://weaviate.io/developers/weaviate
- **Verification Status**: Logic Verified (No Doc Reference Needed)