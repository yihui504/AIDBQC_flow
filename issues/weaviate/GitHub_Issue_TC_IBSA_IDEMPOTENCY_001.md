# [Bug]: Semantic search returns irrelevant results (Type-4 Oracle Violation)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic search query for specific product attributes ('wireless noise cancelling headphones black') returns results that are semantically irrelevant. The top results include items categorized as fruit ('apples') and a generic headphone description that lacks the requested specific features (wireless, noise cancelling, black). This indicates a failure in the vector search's ability to match semantic intent.

### Steps To Reproduce
```python
import weaviate
from weaviate.classes.init import Auth
import os

# 1. Connection logic
client = weaviate.WeaviateClient(
    connection_params=weaviate.connect.ConnectionParams.from_url(
        url="http://localhost:8080",
        grpc_port=50051
    )
)
client.connect()

# 2. Collection creation with specific parameters
collection = client.collections.create(
    name="ProductCatalog",
    properties=[
        weaviate.classes.Property(name="name", data_type=weaviate.classes.DataType.TEXT),
        weaviate.classes.Property(name="description", data_type=weaviate.classes.DataType.TEXT),
        weaviate.classes.Property(name="category", data_type=weaviate.classes.DataType.TEXT),
    ],
    # Configuration based on environment context
    vectorizer_config=weaviate.classes.Configure.Vectorizer.text2VecTransformers(
        vectorize_collection_name=False
    ),
    vector_index_config=weaviate.classes.Configure.VectorIndex.hnsw(
        distance_metric=weaviate.classes.VectorDistances.COSINE
    )
)

# 3. Data Insertion (Simulating the scenario)
with collection.batch.dynamic() as batch:
    # Irrelevant Item 1
    batch.add_object({
        "name": "Fuji Apple",
        "description": "High-quality apple with premium features",
        "category": "Fruit"
    })
    # Irrelevant Item 2
    batch.add_object({
        "name": "Gala Apple",
        "description": "High-quality apple with premium features",
        "category": "Fruit"
    })
    # Partially Relevant Item
    batch.add_object({
        "name": "Standard Headphones",
        "description": "Standard headphones product for general use",
        "category": "Electronics"
    })

# 4. The exact operation that triggered the failure
response = collection.query.near_text(
    query="wireless noise cancelling headphones black",
    limit=4
)

for obj in response.objects:
    print(obj.properties["description"])

client.close()
```

### Expected Behavior
The search should return objects that semantically match the query "wireless noise cancelling headphones black". Specifically, results should be headphones that possess the attributes of being wireless, noise-cancelling, and black. Irrelevant items (such as apples) should not appear in the top results.

### Actual Behavior
The search returned mostly irrelevant items (apples) and one partially relevant item (generic headphones) that lacked the specific requested features. The retrieved items did not match the semantic intent of the query.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable. The core functionality of Weaviate is defined as enabling "advanced semantic search capabilities by comparing the meaning encoded in vectors". The failure to distinguish between 'apples' and 'specific headphones' violates this semantic contract.
- **Reference URL**: https://weaviate.io/developers/weaviate
- **Verification Status**: Logic Verified (No Doc Reference Needed)