from __future__ import annotations

import asyncio
import json
from typing import Optional

from qdrant_client import AsyncQdrantClient, models

from src.adapters.base import VectorDBBase


class QdrantAdapter(VectorDBBase):
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: str = ""):
        self._host = host
        self._port = port
        self._api_key = api_key
        self._client: Optional[AsyncQdrantClient] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    kwargs: dict = {"host": self._host, "port": self._port}
                    if self._api_key:
                        kwargs["api_key"] = self._api_key
                    self._client = AsyncQdrantClient(**kwargs)
        return self._client

    async def create_collection(self, name: str, dimension: int, **kwargs) -> dict:
        distance = kwargs.get("distance", "Cosine")
        distance_map = {"Cosine": models.Distance.COSINE, "L2": models.Distance.EUCLID, "IP": models.Distance.DOT}
        try:
            client = await self._get_client()
            if await client.collection_exists(name):
                return {"success": False, "data": None, "error": f"Collection '{name}' already exists. Use drop_collection first if you want to recreate."}
            await client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=dimension, distance=distance_map.get(distance, models.Distance.COSINE)),
            )
            return {"success": True, "data": f"Created collection '{name}' with dim={dimension}", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def drop_collection(self, name: str) -> dict:
        try:
            client = await self._get_client()
            await client.delete_collection(name)
            return {"success": True, "data": f"Dropped collection '{name}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def insert(self, collection: str, data: list[dict], **kwargs) -> dict:
        try:
            client = await self._get_client()
            points = []
            for i, item in enumerate(data):
                vector = item.get("vector")
                if vector is None:
                    return {"success": False, "data": None, "error": "Missing 'vector' field in data item"}
                point_id = item.get("id", i)
                payload = {k: v for k, v in item.items() if k not in ("vector", "id")}
                points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
            result = await client.upsert(collection_name=collection, points=points)
            return {"success": True, "data": {"operation_id": result.operation_id if result else None}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def search(self, collection: str, vector: list[float], top_k: int = 10, **kwargs) -> dict:
        try:
            client = await self._get_client()
            results = await client.query_points(
                collection_name=collection,
                query=vector,
                limit=top_k,
                with_payload=kwargs.get("with_payload", True),
            )
            search_results = []
            for point in results.points:
                search_results.append({"id": point.id, "score": point.score, "payload": point.payload})
            return {"success": True, "data": {"result_count": len(search_results), "results": search_results}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def query(self, collection: str, filter_expr: str, **kwargs) -> dict:
        try:
            client = await self._get_client()
            limit = kwargs.get("limit", 100)
            qdrant_filter = None
            try:
                filter_obj = json.loads(filter_expr)
                qdrant_filter = models.Filter.model_validate(filter_obj) if filter_obj else None
            except (json.JSONDecodeError, ValueError) as parse_err:
                return {"success": False, "data": None, "error": f"Invalid filter_expr JSON: {parse_err}"}
            scroll_kwargs = {
                "collection_name": collection,
                "limit": limit,
                "with_payload": True,
            }
            if qdrant_filter:
                scroll_kwargs["scroll_filter"] = qdrant_filter
            results, _ = await client.scroll(**scroll_kwargs)
            items = [{"id": p.id, "payload": p.payload} for p in results]
            return {"success": True, "data": {"result_count": len(items), "sample": items[:10]}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def delete(self, collection: str, ids: list[str], **kwargs) -> dict:
        try:
            client = await self._get_client()
            parsed_ids = []
            for i in ids:
                try:
                    parsed_ids.append(int(i))
                except ValueError:
                    parsed_ids.append(i)
            await client.delete(collection_name=collection, points_selector=models.PointIdsList(points=parsed_ids))
            return {"success": True, "data": f"Deleted {len(ids)} records from '{collection}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def upsert(self, collection: str, data: list[dict], **kwargs) -> dict:
        return await self.insert(collection, data, **kwargs)

    async def flush(self, collection: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by qdrant"}

    async def load_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by qdrant"}

    async def release_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by qdrant"}

    async def get_collection_info(self, name: str) -> dict:
        try:
            client = await self._get_client()
            info = await client.get_collection(name)
            vectors_count = getattr(info, "vectors_count", None) or getattr(info, "points_count", 0)
            return {"success": True, "data": {"points_count": info.points_count, "vectors_count": vectors_count, "status": str(info.status)}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def list_collections(self) -> list[str]:
        try:
            client = await self._get_client()
            collections = await client.get_collections()
            return [c.name for c in collections.collections]
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            client = await self._get_client()
            info = await client.get_collections()
            return {"success": True, "data": {"collections_count": len(info.collections)}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                await self._client.close()
                self._client = None
