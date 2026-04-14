# [Bug]: Payload size limit violation not enforced for large payloads

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1
- **SDK/Client**: qdrant-client
- **Deployment mode**: Docker Standalone
- **OS**: Linux / Windows
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat'], 'state_constraints': ['collection_exists', 'data_ready']}

### Describe the bug
Qdrant accepts payloads that exceed the documented maximum size limit of 65535 bytes without raising an error. This violates the documented constraint and can lead to unexpected behavior or data integrity issues where large payloads are silently accepted or truncated.

### Steps To Reproduce
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random
import string

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_payload_limit"

# Recreate collection
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# Create a payload significantly larger than the documented limit of 65535 bytes
# 100,000 characters * ~1 byte/char = ~100KB
massive_description = "".join(random.choices(string.ascii_letters + string.digits, k=100000))

payload = {
    "product_id": 123,
    "description": massive_description
}

# Check size
payload_size = len(str(payload).encode('utf-8'))
print(f"Payload size: {payload_size} bytes")

# Attempt to insert the oversized payload
operation_info = client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=1,
            vector=[random.random() for _ in range(128)],
            payload=payload
        )
    ],
    wait=True
)

print(f"Operation status: {operation_info.status}")

# Verify retrieval
retrieved_point = client.retrieve(
    collection_name=collection_name,
    ids=[1]
)

print(f"Retrieved payload size: {len(str(retrieved_point[0].payload).encode('utf-8'))} bytes")
```

### Expected Behavior
According to the environment configuration and documentation, the maximum payload size is 65535 bytes. Attempting to insert a payload larger than this limit should result in a clear error (e.g., 400 Bad Request or a validation error) indicating that the payload size exceeds the allowed limit.

### Actual Behavior
The system accepts the oversized payload (approx. 100KB) without error. The operation returns `status=completed`, and the full payload is retrievable, indicating that the 65535-byte constraint is not enforced.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The environment configuration specifies `max_payload_size_bytes: 65535`. This constraint is expected to be enforced by the API.
- **Reference URL**: https://qdrant.tech/documentation/concepts/payload/
- **Verification Status**: Logic Verified (No Doc Reference Needed)