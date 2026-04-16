<!--- Provide a general summary of the issue in the Title above -->
# [Bug]: Cosine similarity score strictly exceeds upper bound of 1.0 for identical vectors

## Current Behavior
<!--- Tell us what happens instead of the expected behavior -->
When using the `COSINE` distance metric, searching for a vector that is identical to an inserted vector occasionally returns a similarity score strictly greater than `1.0` (e.g., `1.0000001` or similar).

## Steps to Reproduce
<!--- Provide a link to a live example, or an unambiguous set of steps to -->
<!--- reproduce this bug. Include code to reproduce, if relevant -->
1. Create a collection using `Distance.COSINE`.
2. Generate a random `float32` vector array (e.g. 128 dimensions).
3. Upsert this point into the collection.
4. Query the collection using `client.search` with the exact same vector.
5. In certain cases, the returned score will exceed the maximum bound of `1.0`.

<!--- Please make sure to include the data which could be used to reproduce the problem -->
Here is a minimal reproducible Python script (`qdrant-client`) that loops until the bug is triggered (usually within a few iterations):

```python
from qdrant_client import QdrantClient, models
import numpy as np

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_cosine_bound"

# Ensure clean state
if client.collection_exists(collection_name):
    client.delete_collection(collection_name)

# Create collection with Cosine metric
client.create_collection(
    collection_name=collection_name,
    vectors_config=models.VectorParams(
        size=128, 
        distance=models.Distance.COSINE
    ),
)

bug_reproduced = False
for i in range(100):
    # Generate a random vector
    vector = np.random.rand(128).tolist()

    # Insert the point
    client.upsert(
        collection_name=collection_name,
        points=[models.PointStruct(id=1, vector=vector)],
    )

    # Search with the exact same vector (should yield score = 1.0)
    search_result = client.search(
        collection_name=collection_name,
        query_vector=vector,
        limit=1,
        with_payload=True,
    )

    # Check the score
    score = search_result[0].score

    # Verify the violation
    if score > 1.0:
        print(f"BUG REPRODUCED! Score: {score}")
        bug_reproduced = True
        break

if not bug_reproduced:
    print("Bug not reproduced or fixed.")
```


## Expected Behavior
<!--- Tell us what should happen -->
The cosine similarity score should be mathematically bounded between `-1.0` and `1.0`. When comparing a vector to itself, the score should be exactly `1.0` and never exceed this theoretical upper bound.

## Possible Solution
<!--- Not obligatory, but suggest a fix/reason for the bug, -->
This is a floating-point precision issue. Explicitly clamping the output of the dot product (after normalization) to `1.0` before returning it as the score will resolve the issue.

## Context (Environment)
<!--- How has this issue affected you? What are you trying to accomplish? -->
<!--- Providing context helps us come up with a solution that is most useful in the real world -->
* **Qdrant Version:** 1.17.1 (Docker Standalone)
* **Client:** `qdrant-client` (Python)
* **Distance Metric:** `COSINE`

We are building a validation framework that strictly enforces the bounds of distance metrics. A similarity score exceeding `1.0` causes validation assertions and boundary checks in downstream systems to fail unexpectedly.

## Detailed Description
<!--- Provide a detailed description of the change or addition you are proposing -->
This is likely caused by floating-point arithmetic precision limits (`f32`) during the dot product calculation of normalized vectors in the core engine. While the theoretical maximum of a cosine similarity is `1.0`, floating-point inaccuracies can cause the result to slightly exceed `1.0` (e.g. `1.0000001192092896`). 

## Possible Implementation
<!--- Not obligatory, but suggest an idea for implementing addition or change -->
A simple and effective fix would be to explicitly clamp the cosine similarity score to a maximum of `1.0` before returning the result to the client.

For example, in the Rust core logic where the distance is computed and converted to a score:
```rust
// Clamp to valid range
let score = computed_score.min(1.0).max(-1.0); 
```