from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np

import time

# 1. Connect to Milvus
for i in range(10):
    try:
        connections.connect(host="127.0.0.1", port="19530")
        print("Connected to Milvus")
        break
    except Exception as e:
        print(f"Waiting for Milvus to start... {e}")
        time.sleep(3)
else:
    raise Exception("Could not connect to Milvus")


# 2. Define Collection Schema
dim = 128
fields = [
    FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]
schema = CollectionSchema(fields, description="Cosine test collection")
collection_name = "test_cosine_overflow"

# Drop if exists
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)

# Create Collection
collection = Collection(collection_name, schema)

# 3. Insert Data (Normalized vectors for Cosine)
# Create a normalized vector
np.random.seed(42)
data = np.random.rand(10000, dim).astype(np.float32)
# Normalize manually to ensure unit length
norms = np.linalg.norm(data, axis=1, keepdims=True)
vectors = data / norms

insert_result = collection.insert([vectors])
collection.flush()

# 4. Create Index and Load
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index(field_name="embeddings", index_params=index_params)
collection.load()

# 5. Search with Identical Vector
search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
results = collection.search(
    data=vectors[:100], 
    anns_field="embeddings", 
    param=search_params, 
    limit=1, 
    expr=None
)

# 6. Check Result
bug_reproduced = False
for i, hits in enumerate(results):
    dist = hits[0].distance
    if dist > 1.0:
        print(f"BUG REPRODUCED! Distance {dist} > 1.0 for vector {i}")
        bug_reproduced = True
        break

if not bug_reproduced:
    print(f"Bug not reproduced or fixed. Max distance observed: {max(hits[0].distance for hits in results)}")
