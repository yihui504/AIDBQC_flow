# [Bug]: Hybrid search fails to prioritize exact text matches over generic noise

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A Hybrid Search query for 'Apple MacBook Pro M2' fails to retrieve the exact text match. Instead, the top results consist of generic 'noise' items (e.g., 'Standard laptop product for general use'). This indicates a failure in the search retrieval or ranking logic, where the BM25 (keyword) component is not effectively prioritizing exact matches within the hybrid score.

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.filters import Filter

# 1. Connect to Weaviate
client = weaviate.WeaviateClient(connection_params=weaviate.connect.ConnectionParams.from_url("http://localhost:8080", grpc_port=50051))
client.connect()

# 2. Create Collection with Hybrid Search enabled
collection = client.collections.create(
    name="TestProduct",
    properties=[
        wvc.Property(name="name", data_type=wvc.DataType.TEXT),
        wvc.Property(name="description", data_type=wvc.DataType.TEXT),
        wvc.Property(name="category", data_type=wvc.DataType.TEXT)
    ],
    vectorizer_config=wvc.Configure.Vectorizer.text2VecTransformers()
)

# 3. Insert Data (Target + Noise)
with collection.batch.dynamic() as batch:
    batch.add_object({
        "name": "Apple MacBook Pro M2",
        "description": "High-performance laptop by Apple.",
        "category": "target"
    })
    for _ in range(5):
        batch.add_object({
            "name": "Standard laptop product",
            "description": "Standard laptop product for general use",
            "category": "noise"
        })

# 4. Execute Hybrid Search
response = collection.query.hybrid(
    query="Apple MacBook Pro M2",
    alpha=0.5, # Balance between BM25 and Vector search
    limit=5
)

# 5. Verify Results
for obj in response.objects:
    print(f"Category: {obj.properties['category']}, Name: {obj.properties['name']}")

client.close()
```

### Expected Behavior
The exact text match 'Apple MacBook Pro M2' (Category: target) should appear in the top results, ideally ranked first, given the high BM25 score for the exact match term.

### Actual Behavior
The top results returned were exclusively 'noise' items (e.g., 'Standard laptop product for general use'). The specific entity 'Apple MacBook Pro M2' was not retrieved in the top 5 results.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The general documentation states that Weaviate supports "searches based on both semantic similarity and keywords," but does not explicitly define the ranking priority for exact matches in hybrid mode.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)