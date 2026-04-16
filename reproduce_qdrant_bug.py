from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

client = QdrantClient(url="http://localhost:6333")

collection_name = "test_top_k_oracle"
vector_size = 128

# Recreate to ensure clean state
if client.collection_exists(collection_name):
    client.delete_collection(collection_name)

# 1. Create collection
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# 2. Insert points
points = [
    PointStruct(
        id=i,
        vector=[random.random() for _ in range(vector_size)],
        payload={"color": "red"}
    )
    for i in range(100)
]
client.upsert(collection_name=collection_name, points=points)

# 3. Search with specific limit
bug_reproduced = False
for limit in [1, 5, 10, 50]:
    for _ in range(50):
        query_vector = [random.random() for _ in range(vector_size)]
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        if len(results) > limit:
            print(f"BUG REPRODUCED! Received {len(results)} results, expected max {limit}")
            bug_reproduced = True
            break
    if bug_reproduced:
        break

if not bug_reproduced:
    print("Bug not reproduced or fixed after multiple trials.")
