from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class VectorDBAdapter(ABC):
    """Abstract Base Class for Vector Database Adapters."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the database."""
        pass
        
    @abstractmethod
    def disconnect(self):
        """Close connection to the database."""
        pass
        
    @abstractmethod
    def initialize_collection(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        """Create a collection/index ready for searching."""
        pass
        
    @abstractmethod
    def insert_data(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        """Insert vectors and metadata into the collection."""
        pass
        
    @abstractmethod
    def setup_harness(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        """Initialize environment and inject controlled dummy data for the test harness."""
        pass

    @abstractmethod
    def teardown_harness(self, collection_name: str) -> bool:
        """Clean up test collections and state after testing is done."""
        pass

    @abstractmethod
    async def search_async(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        """Perform a vector similarity search asynchronously."""
        pass

# --- Milvus Implementation ---
class MilvusAdapter(VectorDBAdapter):
    """Adapter for Milvus Vector Database."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        # Require explicit host:port format
        if ":" not in endpoint:
            raise ValueError(f"Invalid endpoint format '{endpoint}'. Expected 'host:port'.")
        self.host, self.port = endpoint.split(":")
        
        # We will lazy load pymilvus so it doesn't break if not installed
        self.connections = None
        self.utility = None
        self.Collection = None
        self.DataType = None
        
        # WBS 1.0: Persistent Collection Pool
        self.collection_pool = {} # Map of dimension -> collection_name
        self.is_connected = False
        self.current_alias = "default"
        self.current_collection_name = None
        self.current_collection_dim = None  # Track the dimension of current collection
        
    def _lazy_init(self):
        if not self.connections:
            try:
                import pymilvus
                from pymilvus import connections, utility, Collection, DataType, FieldSchema, CollectionSchema
                self.connections = connections
                self.utility = utility
                self.Collection = Collection
                self.DataType = DataType
                self.FieldSchema = FieldSchema
                self.CollectionSchema = CollectionSchema
            except ImportError as e:
                raise ImportError(f"pymilvus is not installed correctly or there is an issue importing it: {e}")

    def connect(self) -> bool:
        self._lazy_init()
        if getattr(self, 'is_connected', False):
            return True
        try:
            self.connections.connect("default", host=self.host, port=self.port)
            # Test connection explicitly
            try:
                from pymilvus import utility
                utility.list_collections()
            except Exception as e:
                print(f"[MilvusAdapter] Connection test failed: {e}")
                self.is_connected = False
                return False
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[MilvusAdapter] Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        if self.connections:
            self.connections.disconnect("default")

    def initialize_collection(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        """
        Initialize a Milvus collection for testing.

        Uses collection pooling to reuse collections across test iterations.
        """
        self._lazy_init()
        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, utility
            import time

            # WBS 1.0: Check if we can reuse a collection from the pool for this dimension
            if dimension in self.collection_pool:
                reusable_name = self.collection_pool[dimension]
                print(f"[MilvusAdapter] Reusing pooled collection: {reusable_name} for dimension {dimension}")
                self.current_collection_name = reusable_name
                self.current_collection_dim = dimension  # Store dimension
                return True

            # Create new pooled collection
            safe_name = f"fuzz_pool_dim_{dimension}_{int(time.time())}"
            print(f"[MilvusAdapter] Creating pooled collection {safe_name}...")

            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="payload", dtype=DataType.VARCHAR, max_length=65535)
            ]
            schema = CollectionSchema(fields=fields, description=f"Fuzz Pool Collection Dim {dimension}")

            # Create collection using standard pymilvus API
            print(f"[MilvusAdapter] Creating collection via standard API...")
            collection = Collection(name=safe_name, schema=schema)

            # Wait a moment for creation to propagate
            time.sleep(1)

            # Create index on vector field
            index_params = {
                "metric_type": metric_type,
                "index_type": "FLAT",
                "params": {}
            }
            collection.create_index(field_name="vector", index_params=index_params)
            print(f"[MilvusAdapter] Index created on vector field")

            # Load collection into memory
            collection.load()
            time.sleep(1)
            print(f"[MilvusAdapter] Collection loaded")

            # Smoke test - verify collection is operational
            ready = False
            for i in range(5):
                try:
                    # Insert test data - pymilvus 2.6.x requires row-by-row format
                    collection.insert([
                        {"payload": "smoke_test", "vector": [0.1] * dimension}
                    ])
                    time.sleep(0.5)

                    # Test search
                    collection.search(
                        data=[[0.1] * dimension],
                        anns_field="vector",
                        param={"metric_type": metric_type, "params": {}},
                        limit=1
                    )
                    ready = True
                    print(f"[MilvusAdapter] Pool smoke test passed for {safe_name}")
                    break
                except Exception as e:
                    print(f"[MilvusAdapter] Pool smoke test retry {i} failed: {e}")
                    time.sleep(2)

            if ready:
                self.collection_pool[dimension] = safe_name
                self.current_alias = "default"
                self.current_collection_name = safe_name
                self.current_collection_dim = dimension  # Store dimension
                print(f"[MilvusAdapter] Collection pool updated: {self.collection_pool}")

            return ready

        except Exception as e:
            print(f"[MilvusAdapter] Failed to initialize pooled collection: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_data(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        self._lazy_init()
        try:
            from pymilvus import Collection, utility
            alias = getattr(self, 'current_alias', 'default')
            collection = Collection(collection_name, using=alias)
            # Convert payloads to strings since we defined it as VARCHAR
            import json
            payload_strs = [json.dumps(p) for p in payloads]

            # Ensure vectors match dimension
            dim = collection.schema.fields[1].params.get("dim", len(vectors[0]))

            # Build rows in pymilvus 2.6.x format: list of dicts
            rows = []
            for v, p in zip(vectors, payload_strs):
                if len(v) == dim:
                    rows.append({"payload": p, "vector": v})
                else:
                    # Pad or truncate if needed for robustness
                    new_v = list(v)
                    if len(new_v) < dim:
                        new_v.extend([0.0] * (dim - len(new_v)))
                    else:
                        new_v = new_v[:dim]
                    rows.append({"payload": p, "vector": new_v})

            # Insert using row-by-row format
            collection.insert(rows)
            collection.flush()

            try:
                utility.wait_for_loading_complete(collection_name, using=alias)
            except Exception as e:
                logger.warning(
                    "[MilvusAdapter] wait_for_loading_complete failed for collection=%s alias=%s: %s",
                    collection_name,
                    alias,
                    e
                )

            # Adding a small delay to ensure data is visible for search
            import time
            time.sleep(1)
            return True
        except Exception as e:
            print(f"[MilvusAdapter] Failed to insert data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_harness(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        """Sets up the Milvus collection and injects basic data for the harness."""
        print(f"[Harness] Setting up environment for collection: {collection_name}")
        success = self.initialize_collection(collection_name, dimension, metric_type)
        return success

    def teardown_harness(self, collection_name: str) -> bool:
        """
        WBS 1.0: In pool mode, we don't drop the collection during the run.
        We only drop if it's NOT part of our managed pool.
        """
        self._lazy_init()
        # Check if this collection is in our pool
        is_pooled = any(name == collection_name for name in self.collection_pool.values())
        
        if is_pooled:
            print(f"[Harness] Skipping teardown for pooled collection: {collection_name}")
            return True
            
        print(f"[Harness] Tearing down non-pooled environment for collection: {collection_name}")
        try:
            if self.utility.has_collection(collection_name):
                self.utility.drop_collection(collection_name)
            return True
        except Exception as e:
            print(f"[Harness] Failed to teardown collection: {e}")
            return False

    async def search_async(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        # For pymilvus, true async support requires aiohttp/grpc-async or running in executor.
        # Here we simulate async using asyncio.to_thread for the synchronous call.
        import asyncio
        return await asyncio.to_thread(self._search_sync, collection_name, query_vector, top_k, metric_type)

    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        """
        Public search method.
        """
        return self._search_sync(collection_name, query_vector, top_k, metric_type)

    def _search_sync(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        self._lazy_init()
        try:
            from pymilvus import Collection
            # Debug: Print vector dimension
            print(f"[MilvusAdapter] Search: vector_dim={len(query_vector)}, collection={collection_name}")

            # Re-initialize collection object to ensure it sees the loaded data
            alias = getattr(self, 'current_alias', 'default')
            collection = Collection(collection_name, using=alias)
            search_params = {
                "metric_type": metric_type,
                "params": {} # Remove nprobe since we are using FLAT index
            }
            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["payload"]
            )

            # Parse results
            hits = []
            if results and len(results) > 0:
                for hit in results[0]:
                    hits.append({
                        "id": hit.id,
                        "distance": hit.distance,
                        "payload": hit.entity.get("payload")
                    })

            return {
                "success": True,
                "hits": hits,
                "error": None
            }
        except Exception as e:
            error_data = {
                "success": False,
                "hits": [],
                "error": str(e)
            }
            # Record raw MilvusException details if available
            if hasattr(e, 'code'):
                error_data["code"] = e.code
            if hasattr(e, 'message'):
                error_data["message"] = e.message
            return error_data


# --- Weaviate Implementation ---
class WeaviateAdapter(VectorDBAdapter):
    """Adapter for Weaviate Vector Database."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        if ":" not in endpoint:
            raise ValueError(f"Invalid endpoint format '{endpoint}'. Expected 'host:port'.")
        self.host, self.port = endpoint.split(":")

        self.client = None
        self.collection_pool = {}
        self.is_connected = False
        self.current_collection_name = None
        self.current_collection_dim = None

    def _lazy_init(self):
        if not self.client:
            try:
                import weaviate
                from weaviate.classes.config import Configure, Property, DataType
                self.weaviate = weaviate
                self.Configure = Configure
                self.Property = Property
                self.DataType = DataType
            except ImportError as e:
                raise ImportError(f"weaviate-client is not installed correctly: {e}")

    def _get_metric_type(self, metric_type: str):
        """Convert common metric names to Weaviate VectorDistances."""
        from weaviate.classes.config import VectorDistances
        metric_map = {
            "cosine": VectorDistances.COSINE,
            "l2": VectorDistances.L2_SQUARED,
            "l2-squared": VectorDistances.L2_SQUARED,
            "dot": VectorDistances.DOT,
            "manhattan": VectorDistances.MANHATTAN,
            "hamming": VectorDistances.HAMMING,
        }
        return metric_map.get(metric_type.lower(), VectorDistances.COSINE)

    def connect(self) -> bool:
        self._lazy_init()
        if getattr(self, 'is_connected', False):
            return True
        try:
            print(f"[WeaviateAdapter] Connecting to http://{self.host}:{self.port} (grpc_port=50051)...")
            self.client = self.weaviate.WeaviateClient(
                connection_params=self.weaviate.connect.ConnectionParams.from_url(
                    url=f"http://{self.host}:{self.port}",
                    grpc_port=50051
                )
            )
            self.client.connect()
            self.is_connected = True
            print(f"[WeaviateAdapter] Connected successfully!")
            return True
        except Exception as e:
            print(f"[WeaviateAdapter] Connection failed: {type(e).__name__}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        if self.client:
            self.client.close()

    def initialize_collection(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        self._lazy_init()
        try:
            import time

            if dimension in self.collection_pool:
                reusable_name = self.collection_pool[dimension]
                print(f"[WeaviateAdapter] Reusing pooled collection: {reusable_name} for dimension {dimension}")
                self.current_collection_name = reusable_name
                self.current_collection_dim = dimension
                return True

            safe_name = f"FuzzPoolDim{dimension}_{int(time.time())}"
            print(f"[WeaviateAdapter] Creating pooled collection {safe_name}...")

            vector_distance = self._get_metric_type(metric_type)

            self.client.collections.create(
                name=safe_name,
                properties=[
                    self.Property(name="payload", data_type=self.DataType.TEXT)
                ],
                vectorizer_config=self.Configure.Vectorizer.none(),
                vector_index_config=self.Configure.VectorIndex.hnsw(
                    distance_metric=vector_distance
                )
            )

            time.sleep(1)
            print(f"[WeaviateAdapter] Collection created")

            collection = self.client.collections.get(safe_name)
            ready = False
            for i in range(5):
                try:
                    collection.data.insert(
                        properties={"payload": "smoke_test"},
                        vector=[0.1] * dimension
                    )
                    time.sleep(0.5)

                    collection.query.near_vector(
                        near_vector=[0.1] * dimension,
                        limit=1
                    )
                    ready = True
                    print(f"[WeaviateAdapter] Pool smoke test passed for {safe_name}")
                    break
                except Exception as e:
                    print(f"[WeaviateAdapter] Pool smoke test retry {i} failed: {e}")
                    time.sleep(2)

            if ready:
                self.collection_pool[dimension] = safe_name
                self.current_collection_name = safe_name
                self.current_collection_dim = dimension
                print(f"[WeaviateAdapter] Collection pool updated: {self.collection_pool}")

            return ready

        except Exception as e:
            print(f"[WeaviateAdapter] Failed to initialize pooled collection: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_data(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        self._lazy_init()
        try:
            import json
            collection = self.client.collections.get(collection_name)

            for v, p in zip(vectors, payloads):
                payload_str = json.dumps(p)
                collection.data.insert(
                    properties={"payload": payload_str},
                    vector=v
                )

            import time
            time.sleep(1)
            return True
        except Exception as e:
            print(f"[WeaviateAdapter] Failed to insert data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_harness(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        print(f"[Harness] Setting up environment for collection: {collection_name}")
        success = self.initialize_collection(collection_name, dimension, metric_type)
        return success

    def teardown_harness(self, collection_name: str) -> bool:
        self._lazy_init()
        is_pooled = any(name == collection_name for name in self.collection_pool.values())

        if is_pooled:
            print(f"[Harness] Skipping teardown for pooled collection: {collection_name}")
            return True

        print(f"[Harness] Tearing down non-pooled environment for collection: {collection_name}")
        try:
            self.client.collections.delete(collection_name)
            return True
        except Exception as e:
            print(f"[Harness] Failed to teardown collection: {e}")
            return False

    async def search_async(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self._search_sync, collection_name, query_vector, top_k, metric_type)

    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        return self._search_sync(collection_name, query_vector, top_k, metric_type)

    def _search_sync(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        self._lazy_init()
        try:
            print(f"[WeaviateAdapter] Search: vector_dim={len(query_vector)}, collection={collection_name}")

            collection = self.client.collections.get(collection_name)
            results = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                return_properties=["payload"],
                return_metadata=["distance"]
            )

            hits = []
            for obj in results.objects:
                hits.append({
                    "id": str(obj.uuid),
                    "distance": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None,
                    "payload": obj.properties.get("payload")
                })

            return {
                "success": True,
                "hits": hits,
                "error": None
            }
        except Exception as e:
            error_data = {
                "success": False,
                "hits": [],
                "error": str(e)
            }
            return error_data


# --- Qdrant Implementation ---
class QdrantAdapter(VectorDBAdapter):
    """Adapter for Qdrant Vector Database."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        if ":" not in endpoint:
            raise ValueError(f"Invalid endpoint format '{endpoint}'. Expected 'host:port'.")
        self.host, self.port = endpoint.split(":")
        
        self.client = None
        self.is_connected = False
        self.collection_pool = {}
        self.current_collection_name = None
        self.current_collection_dim = None
        
    def _lazy_init(self):
        if not self.client:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.models import Distance, VectorParams, PointStruct
                self.QdrantClient = QdrantClient
                self.Distance = Distance
                self.VectorParams = VectorParams
                self.PointStruct = PointStruct
            except ImportError as e:
                raise ImportError(f"qdrant-client is not installed correctly: {e}")

    def _metric_to_distance(self, metric_type: str):
        metric_map = {
            "L2": self.Distance.EUCLID,
            "EUCLID": self.Distance.EUCLID,
            "COSINE": self.Distance.COSINE,
            "IP": self.Distance.DOT,
            "DOT": self.Distance.DOT,
        }
        return metric_map.get(metric_type.upper(), self.Distance.COSINE)

    def connect(self) -> bool:
        self._lazy_init()
        if getattr(self, 'is_connected', False):
            return True
        try:
            self.client = self.QdrantClient(host=self.host, port=int(self.port))
            self.client.get_collections()
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[QdrantAdapter] Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
            self.is_connected = False

    def initialize_collection(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        self._lazy_init()
        try:
            import time
            
            if dimension in self.collection_pool:
                reusable_name = self.collection_pool[dimension]
                print(f"[QdrantAdapter] Reusing pooled collection: {reusable_name} for dimension {dimension}")
                self.current_collection_name = reusable_name
                self.current_collection_dim = dimension
                return True
            
            safe_name = f"fuzz_pool_dim_{dimension}_{int(time.time())}"
            print(f"[QdrantAdapter] Creating pooled collection {safe_name}...")
            
            distance = self._metric_to_distance(metric_type)
            
            self.client.create_collection(
                collection_name=safe_name,
                vectors_config=self.VectorParams(size=dimension, distance=distance)
            )
            
            time.sleep(0.5)
            
            ready = False
            for i in range(5):
                try:
                    self.client.upsert(
                        collection_name=safe_name,
                        points=[self.PointStruct(id=1, vector=[0.1] * dimension, payload={"test": "smoke"})]
                    )
                    
                    self.client.search(
                        collection_name=safe_name,
                        query_vector=[0.1] * dimension,
                        limit=1
                    )
                    ready = True
                    print(f"[QdrantAdapter] Pool smoke test passed for {safe_name}")
                    break
                except Exception as e:
                    print(f"[QdrantAdapter] Pool smoke test retry {i} failed: {e}")
                    time.sleep(1)
            
            if ready:
                self.collection_pool[dimension] = safe_name
                self.current_collection_name = safe_name
                self.current_collection_dim = dimension
                print(f"[QdrantAdapter] Collection pool updated: {self.collection_pool}")
            
            return ready
            
        except Exception as e:
            print(f"[QdrantAdapter] Failed to initialize pooled collection: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_data(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        self._lazy_init()
        try:
            import uuid
            
            dim = self.current_collection_dim or len(vectors[0])
            
            points = []
            for i, (v, p) in enumerate(zip(vectors, payloads)):
                vector = list(v)
                if len(vector) < dim:
                    vector.extend([0.0] * (dim - len(vector)))
                elif len(vector) > dim:
                    vector = vector[:dim]
                
                point = self.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=p
                )
                points.append(point)
            
            self.client.upsert(collection_name=collection_name, points=points)
            
            import time
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[QdrantAdapter] Failed to insert data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_harness(self, collection_name: str, dimension: int, metric_type: str = "L2") -> bool:
        print(f"[Harness] Setting up environment for collection: {collection_name}")
        success = self.initialize_collection(collection_name, dimension, metric_type)
        return success

    def teardown_harness(self, collection_name: str) -> bool:
        self._lazy_init()
        is_pooled = any(name == collection_name for name in self.collection_pool.values())
        
        if is_pooled:
            print(f"[Harness] Skipping teardown for pooled collection: {collection_name}")
            return True
        
        print(f"[Harness] Tearing down non-pooled environment for collection: {collection_name}")
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"[Harness] Failed to teardown collection: {e}")
            return False

    async def search_async(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self._search_sync, collection_name, query_vector, top_k, metric_type)

    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        return self._search_sync(collection_name, query_vector, top_k, metric_type)

    def _search_sync(self, collection_name: str, query_vector: List[float], top_k: int = 10, metric_type: str = "L2") -> Dict[str, Any]:
        self._lazy_init()
        try:
            print(f"[QdrantAdapter] Search: vector_dim={len(query_vector)}, collection={collection_name}")
            
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True
            )
            
            hits = []
            for hit in results:
                hits.append({
                    "id": hit.id,
                    "distance": hit.score,
                    "payload": hit.payload
                })
            
            return {
                "success": True,
                "hits": hits,
                "error": None
            }
        except Exception as e:
            error_data = {
                "success": False,
                "hits": [],
                "error": str(e)
            }
            if hasattr(e, 'code'):
                error_data["code"] = e.code
            if hasattr(e, 'message'):
                error_data["message"] = e.message
            return error_data
