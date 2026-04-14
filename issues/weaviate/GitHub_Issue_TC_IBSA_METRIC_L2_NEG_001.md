# [Bug]: Type-3 (Traditional Oracle) in TC_IBSA_METRIC_L2_NEG_001

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [256, 384, 512, 768, 1024, 1536, 3072], 'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'flat', 'dynamic', 'hnsw_dynamic', 'flat_dynamic'], 'state_constraints': ['collection_exists', 'index_ready', 'vector_index_configured'], 'source_urls': {'allowed_dimensions': 'https://weaviate.io/developers/weaviate', 'supported_metrics': 'https://weaviate.io/developers/weaviate', 'max_top_k': 'https://weaviate.io/developers/weaviate', 'supported_index_types': 'https://weaviate.io/developers/weaviate'}, 'exhaustive_constraints': {'vectorIndexType': 'hnsw', 'vectorizer': 'text2vec-transformers', 'moduleConfig': {'type': 'object'}}}

### Describe the bug
A Type-3 (Traditional Oracle) violation was detected during the `L2 squared distance check` operation. The system returned results that deviate from the expected mathematical contract for the L2-squared metric, indicating a potential logic error in the distance calculation or sorting mechanism.

### Steps To Reproduce
```python
import weaviate
import os
import numpy as np

# Connect to Weaviate
client = weaviate.connect_to_local()

# Create Collection
collection_name = "TestL2Metric"
if client.collections.exists(collection_name):
    client.collections.delete(collection_name)

client.collections.create(
    name=collection_name,
    properties=[
        wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
    ],
    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
        distance_metric=wvc.config.VectorDistances.L2_SQUARED
    )
)

collection = client.collections.get(collection_name)

# Insert Data with specific vectors to test L2 distance
# Vector 1: [1, 0, 0]
# Vector 2: [0, 1, 0]
# Query: [0, 0, 0]
# Expected Dist: Query-V1 = 1.0, Query-V2 = 1.0

data_objs = [{"text": "obj1"}, {"text": "obj2"}]
vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

with collection.batch.dynamic() as batch:
    for i, obj in enumerate(data_objs):
        batch.add_object(
            properties=obj,
            vector=vectors[i]
        )

# Perform Near Vector Search
query_vector = [0.0, 0.0, 0.0]
response = collection.query.near_vector(
    near_vector=query_vector,
    limit=2
)

for o in response.objects:
    print(o.properties, o.metadata.distance)

client.close()
```

### Expected Behavior
The search results should return objects sorted by the correct L2-squared distance. For the provided vectors, the distance from the query vector `[0, 0, 0]` to both `[1, 0, 0]` and `[0, 1, 0]` should be exactly `1.0`. The results should reflect this mathematical truth.

### Actual Behavior
The system behavior violated the traditional oracle check for the L2-squared metric. The results did not match the expected mathematical output, suggesting a calculation or logic error in the metric implementation.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: No direct documentation reference found.
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)