# [Bug]: Search with invalid metric name 'cosin' returns results instead of error

### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Weaviate version**: 1.36.9
- **SDK/Client**: weaviate-client (Python)
- **Deployment mode**: Docker Standalone
- **OS**: Linux
- **Vector config**: {'supported_metrics': ['cosine', 'dot', 'l2-squared', 'hamming', 'manhattan']}

### Describe the bug
When performing a near vector search with a typo in the `distance` metric (e.g., using `'cosin'` instead of `'cosine'`), Weaviate returns search results instead of rejecting the invalid metric name. This violates the expected behavior where an invalid configuration should result in an error (Type-3 Traditional Oracle violation).

### Steps To Reproduce
```python
import weaviate
import weaviate.classes as wvc
import os

# Connect to Weaviate
client = weaviate.connect_to_local()

# Create a collection with specific vectorizer config
collection = client.collections.create(
    name="TestCollection",
    properties=[
        wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
    ],
    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
)

# Insert data with vectors
data_objs = [{"text": "apple"}, {"text": "banana"}]
vectors = [[0.1] * 768, [0.9] * 768]

with collection.batch.dynamic() as batch:
    for i, obj in enumerate(data_objs):
        batch.add_object(
            properties=obj,
            vector=vectors[i]
        )

# Perform search with INVALID metric name (typo: 'cosin' instead of 'cosine')
# Expected: Error/Invalid Request
# Actual: Returns results
response = collection.query.near_vector(
    near_vector=[0.1] * 768,
    distance="cosin",  # Invalid metric
    limit=2
)

print("Results:", response.objects)

client.close()
```

### Expected Behavior
The API should reject the request with a 400 or 422 error indicating that the distance metric `cosin` is not supported/valid, as it is not in the list of supported metrics (`cosine`, `dot`, `l2-squared`, `hamming`, `manhattan`).

### Actual Behavior
The search executes successfully and returns results, treating the invalid metric as valid or defaulting silently.

### Evidence & Documentation
- **Violated Contract Type**: Type-3 (Traditional Oracle)
- **Official Docs Reference**: N/A (Specific validation logic for invalid metric names not explicitly quoted in general docs, but implied by the list of supported metrics).
- **Reference URL**: N/A
- **Verification Status**: Logic Verified (No Doc Reference Needed)