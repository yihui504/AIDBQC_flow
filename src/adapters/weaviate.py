from __future__ import annotations

import asyncio
import json
from typing import Optional

import weaviate
import weaviate.classes as wvc
from weaviate.classes.query import Filter

from src.adapters.base import VectorDBBase


class WeaviateAdapter(VectorDBBase):
    def __init__(self, host: str = "localhost", port: int = 8080, grpc_port: int = 50051):
        self._host = host
        self._port = port
        self._grpc_port = grpc_port
        self._client: Optional[weaviate.WeaviateAsyncClient] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> weaviate.WeaviateAsyncClient:
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        self._client = weaviate.use_async_with_local(
                            host=self._host,
                            port=self._port,
                            grpc_port=self._grpc_port,
                        )
                        await self._client.connect()
                    except Exception:
                        self._client = None
                        raise
        return self._client

    async def create_collection(self, name: str, dimension: int, **kwargs) -> dict:
        try:
            client = await self._get_client()
            if await client.collections.exists(name):
                return {"success": False, "data": None, "error": f"Collection '{name}' already exists. Use drop_collection first if you want to recreate."}
            await client.collections.create(
                name=name,
                vector_config=wvc.config.Configure.Vectors.self_provided(dimensions=dimension),
                properties=[
                    wvc.config.Property(name="payload", data_type=wvc.config.DataType.TEXT),
                ],
            )
            return {"success": True, "data": f"Created collection '{name}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def drop_collection(self, name: str) -> dict:
        try:
            client = await self._get_client()
            await client.collections.delete(name)
            return {"success": True, "data": f"Dropped collection '{name}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def insert(self, collection: str, data: list[dict], **kwargs) -> dict:
        try:
            client = await self._get_client()
            col = client.collections.use(collection)
            inserted = 0
            for item in data:
                vector = item.get("vector")
                properties = {k: str(v) for k, v in item.items() if k not in ("id", "vector")}
                if vector:
                    await col.data.insert(properties=properties, vector=vector)
                else:
                    await col.data.insert(properties=properties)
                inserted += 1
            return {"success": True, "data": {"insert_count": inserted}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def search(self, collection: str, vector: list[float], top_k: int = 10, **kwargs) -> dict:
        try:
            client = await self._get_client()
            col = client.collections.use(collection)
            results = await col.query.near_vector(
                near_vector=vector,
                limit=top_k,
            )
            search_results = []
            for obj in results.objects:
                search_results.append({"id": str(obj.uuid), "score": obj.metadata.score if obj.metadata else None, "properties": obj.properties})
            return {"success": True, "data": {"result_count": len(search_results), "results": search_results}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def query(self, collection: str, filter_expr: str, **kwargs) -> dict:
        try:
            client = await self._get_client()
            col = client.collections.use(collection)
            limit = kwargs.get("limit", 100)
            if filter_expr:
                try:
                    filter_obj = json.loads(filter_expr)
                    if isinstance(filter_obj, dict):
                        filters = []
                        for key, value in filter_obj.items():
                            filters.append(Filter.by_property(key).equal(value))
                        if filters:
                            combined = filters[0]
                            for f in filters[1:]:
                                combined = combined & f
                            results = await col.query.fetch_objects(limit=limit, filters=combined)
                        else:
                            results = await col.query.fetch_objects(limit=limit)
                    else:
                        results = await col.query.fetch_objects(limit=limit)
                except (json.JSONDecodeError, ValueError) as parse_err:
                    return {"success": False, "data": None, "error": f"Invalid filter_expr JSON: {parse_err}"}
                except Exception as parse_err:
                    return {"success": False, "data": None, "error": f"Failed to parse filter_expr: {parse_err}"}
            else:
                results = await col.query.fetch_objects(limit=limit)
            items = [{"id": str(obj.uuid), "properties": obj.properties} for obj in results.objects]
            return {"success": True, "data": {"result_count": len(items), "sample": items[:10]}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def delete(self, collection: str, ids: list[str], **kwargs) -> dict:
        try:
            client = await self._get_client()
            col = client.collections.use(collection)
            for oid in ids:
                await col.data.delete_by_id(oid)
            return {"success": True, "data": f"Deleted {len(ids)} records from '{collection}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def upsert(self, collection: str, data: list[dict], **kwargs) -> dict:
        return {"success": False, "data": None, "error": "Not supported by weaviate"}

    async def flush(self, collection: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by weaviate"}

    async def load_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by weaviate"}

    async def release_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by weaviate"}

    async def get_collection_info(self, name: str) -> dict:
        try:
            client = await self._get_client()
            config = await client.collections.export_config(name)
            return {"success": True, "data": {"name": name, "config": str(config)}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def list_collections(self) -> list[str]:
        try:
            client = await self._get_client()
            collections = await client.collections.list_all()
            return list(collections.keys())
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            client = await self._get_client()
            ready = await client.is_ready()
            return {"success": ready, "data": {"ready": ready}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                await self._client.close()
                self._client = None
