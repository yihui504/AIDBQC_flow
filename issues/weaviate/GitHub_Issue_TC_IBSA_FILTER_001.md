# [Bug]: Semantic search with 'near_text' fails to respect metadata filters (Type-4)

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: weaviate 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A semantic search query for 'laptop under 500 dollars' returns irrelevant results (e.g., 'High-quality apple') and fails to apply the specified price filter constraint. The results do not demonstrate that the 'under 500 dollars' constraint was respected or processed, indicating a semantic oracle violation where the intent to filter by metadata is not met.

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.filters import Filter

# 1. Connection logic
client = weaviate.WeaviateClient(connection_params=weaviate.connect.ConnectionParams.from_url("http://localhost:8080", grpc_port=50051))
client.connect()

# 2. Collection creation with specific parameters
collection = client.collections.create(
    name="Product",
    properties=[
        wvc.Property(name="name", data_type=wvc.DataType.TEXT),
        wvc.Property(name="description", data_type=wvc.DataType.TEXT),
        wvc.Property(name="price", data_type=wvc.DataType.NUMBER)
    ],
    vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers()
)

# 3. Insert data with real semantic vectors and metadata
with collection.batch.dynamic() as batch:
    batch.add_object(
        properties={"name": "Standard Laptop", "description": "Standard laptop product for general use", "price": 400}
    )
    batch.add_object(
        properties={"name": "Premium Apple", "description": "High-quality apple with premium features", "price": 1000}
    )

# 4. The exact operation that triggered the failure
response = collection.query.near_text(
    query="laptop under 500 dollars",
    filters=Filter.by_property("price").less_than(500),
    limit=5
)

for obj in response.objects:
    print(obj.properties)
```

### Expected Behavior
The query should return only the 'Standard Laptop' object, as it is the only item that matches both the semantic intent ('laptop') and the metadata constraint ('price < 500').

### Actual Behavior
The database returned irrelevant results (e.g., 'High-quality apple') and did not demonstrate the application of the price filter specified in the query.

### Evidence & Documentation
- **Violated Contract Type**: Type-4 (Semantic Oracle)
- **Official Docs Reference**: Semantic logic violation; direct documentation reference not applicable
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)