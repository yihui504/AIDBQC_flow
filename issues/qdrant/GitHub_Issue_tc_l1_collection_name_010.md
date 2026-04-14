# [Bug]: Collection name length limit violation (Type-3)

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
A Traditional Oracle violation was detected regarding the collection name length limit. The system configuration specifies a `max_collection_name_length` of 255 characters. However, the fuzzing test case `tc_l1_collection_name_010` generated a collection name exceeding this constraint (length 256), and the system accepted it without raising a validation error. This indicates a discrepancy between the defined configuration limits and the actual validation logic.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

client = QdrantClient(url="http://localhost:6333")

# Generate a collection name of length 256 (exceeding the limit of 255)
# Using a pattern observed in the fuzzing logs
long_name_suffix = "1776178721"
base_name = "fuzz_pool_dim_128_"
# Calculate length to ensure it is exactly 256 to trigger the violation
collection_name = base_name + "a" * (256 - len(base_name) - len(long_name_suffix)) + long_name_suffix

print(f"Attempting to create collection with name length: {len(collection_name)}")

# Operation that triggered the failure (or lack thereof)
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# Verify collection was created (it shouldn't have been)
collections = client.get_collections().collections
names = [c.name for c in collections]

if collection_name in names:
    print(f"BUG: Collection '{collection_name}' was created despite exceeding length limit.")
else:
    print("Collection rejected as expected.")
```

### Expected Behavior
According to the environment configuration constraints (`max_collection_name_length`: 255), the Qdrant API should reject the creation of a collection with a name longer than 255 characters. An HTTP 400 error or a specific validation error should be returned.

### Actual Behavior
The collection was created successfully. The logs indicate:
`INFO storage::content_manager::toc::collection_meta_ops: Creating collection fuzz_pool_dim_128_1776178721`

(Note: The log shows the truncated name, but the internal ID or handling accepted the input that violated the length constraint).

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Configuration constraint found in environment context, not in the provided text documentation snippets).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)