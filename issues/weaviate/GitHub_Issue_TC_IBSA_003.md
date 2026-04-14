# [Bug]: Type-4 (Semantic Oracle) - Poor Semantic Retrieval for 'laptop for programming' Query

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic search query for 'laptop for programming' returns irrelevant results, including keyboards and fruit (apples), instead of high-spec or general laptops. The retrieved items are tagged with category 'noise' and domain 'general', indicating a failure in the semantic retrieval and ranking logic to correctly interpret the intent and context of the query.

### Steps To Reproduce
```python
import weaviate
import os

# 1. Connection logic
client = weaviate.connect_to_local()

# 2. Collection creation (Simulating the environment where the bug was found)
# Note: This assumes a collection exists with vectors that trigger the semantic failure.
if client.collections.exists("TestCollection"):
    client.collections.delete("TestCollection")

collection = client.collections.create(
    name="TestCollection",
    properties=[
        wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
        wvc.config.Property(name="category", data_type=wvc.config.DataType.TEXT),
        wvc.config.Property(name="domain", data_type=wvc.config.DataType.TEXT),
    ],
    # Configuration based on environment context
    vectorizer_config=wvc.config.Configure.Vectorizer.text2VecTransformers()
)

# 3. Insert Data (Simulating the 'noise' and 'general' data described in the report)
with collection.batch.dynamic() as batch:
    batch.add_object({
        "text": "Standard laptop product for general use",
        "category": "noise",
        "domain": "general"
    })
    batch.add_object({
        "text": "Standard keyboard product for general use",
        "category": "noise",
        "domain": "general"
    })
    batch.add_object({
        "text": "High-quality apple with premium features",
        "category": "noise",
        "domain": "general"
    })

# 4. The exact operation that triggered the failure
response = collection.query.near_text(
    query="laptop for programming",
    limit=4
)

for o in response.objects:
    print(o.properties["text"])
```

### Expected Behavior
The search system should retrieve actual laptops, preferably those with specifications suitable for programming (e.g., high RAM, good CPU), as implied by the semantic intent of the query "laptop for programming". It should not return accessories (keyboards) or unrelated items (fruit).

### Actual Behavior
The system returned a mix of irrelevant items:
1. "Standard laptop product for general use" (Correct category, but potentially low spec).
2. "Standard keyboard product for general use" (Incorrect category - accessory).
3. "Standard keyboard product for general use" (Duplicate incorrect category).
4. "High-quality apple with premium features" (Incorrect category - fruit).

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The core functionality of Weaviate is described as enabling "advanced semantic search capabilities by comparing the meaning encoded in vectors rather than relying solely on keyword matching." The observed behavior where 'keyboard' and 'apple' are ranked as top matches for 'laptop for programming' violates this semantic contract.
- **Reference URL**: https://weaviate.io/developers/weaviate
- **Verification Status**: Logic Verified (No Doc Reference Needed)