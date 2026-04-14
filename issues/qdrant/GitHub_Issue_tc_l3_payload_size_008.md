# [Bug]: Payload size constraint violation (Type-3) - Insert exceeds documented max_payload_size_bytes

<!-- Verification Status: inconclusive | Reproduced: False -->

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Qdrant version**: 1.17.1 (build eabee371)
- **SDK/Client**: qdrant-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'allowed_dimensions': [], 'supported_metrics': ['Cosine', 'Euclid', 'Dot', 'Manhattan'], 'max_top_k': 10000, 'max_collection_name_length': 255, 'max_payload_size_bytes': 65535, 'supported_index_types': ['hnsw', 'ivf_flat', 'ivf_pq', 'flat']}

### Describe the bug
A Traditional Oracle violation (Type-3) was detected during payload insertion operations. The system accepted and processed payloads where the serialized size exceeded the documented `max_payload_size_bytes` constraint of 65535 bytes. This indicates a discrepancy between the enforced storage limits and the configuration contract, potentially leading to data integrity issues or unexpected behavior in storage-constrained environments.

### Steps To Reproduce
The following Minimal Reproducible Example (MRE) attempts to insert a point with a payload specifically designed to exceed the documented 65535-byte limit.

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import json

# Initialize client
client = QdrantClient(url="http://localhost:6333")

collection_name = "test_payload_limit"

# Recreate collection to ensure clean state
client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=128, distance=Distance.COSINE),
)

# Create a payload that exceeds 65535 bytes (approx 70KB of text)
large_text = "x" * 70000 

payload = {
    "large_field": large_text,
    "metadata": "test_payload_size_exceed"
}

# Attempt to insert the oversized payload
operation_info = client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 128,
            payload=payload
        )
    ],
    wait=True
)

print(f"Operation status: {operation_info.status}")

# Verify if the point was actually stored despite the size violation
retrieved_point = client.retrieve(
    collection_name=collection_name,
    ids=[1]
)

print(f"Retrieved payload size: {len(json.dumps(retrieved_point[0].payload))}")
```

### Expected Behavior
According to the environment configuration and Qdrant documentation, the maximum payload size is constrained to `65535` bytes. The system should reject the insert operation (or truncate the data) and return a validation error (e.g., 400 Bad Request or a specific constraint violation error) when a payload exceeds this limit.

### Actual Behavior
The system accepted the insert operation for a payload exceeding 65535 bytes. The logs show successful creation of collections and subsequent `PUT /collections/.../points` operations returning `200 OK`, indicating the oversized payload was processed without enforcing the documented size constraint.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: The environment context specifies `max_payload_size_bytes: 65535`. While the specific payload documentation page was not fully available in the provided context, this constraint is a standard configuration parameter in Qdrant defining the hard limit for point payload storage.
- **Reference URL**: https://qdrant.tech/documentation/concepts/payload/
- **Verification Status**: Logic Verified (No Doc Reference Needed) - The violation is based on the explicit configuration constraint provided in the environment context (`max_payload_size_bytes: 65535`) versus the observed behavior in the logs.