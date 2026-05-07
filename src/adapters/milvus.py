from __future__ import annotations

import asyncio
import threading
from typing import Optional

from pymilvus import MilvusClient, DataType

from src.adapters.base import VectorDBBase


class MilvusAdapter(VectorDBBase):
    def __init__(self, host: str = "localhost", port: int = 19530, timeout: int = 30):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._client: Optional[MilvusClient] = None
        self._lock = threading.RLock()

    def _get_client(self) -> MilvusClient:
        with self._lock:
            if self._client is None:
                self._client = MilvusClient(
                    uri=f"http://{self._host}:{self._port}",
                    timeout=self._timeout,
                )
            return self._client

    async def create_collection(self, name: str, dimension: int, **kwargs) -> dict:
        index_type = kwargs.get("index_type", "IVF_FLAT")
        metric_type = kwargs.get("metric_type", "L2")
        auto_id = kwargs.get("auto_id", True)
        enable_dynamic_field = kwargs.get("enable_dynamic_field", True)

        def _sync():
            with self._lock:
                client = self._get_client()
                if client.has_collection(name):
                    return {"success": False, "data": None, "error": f"Collection '{name}' already exists. Use drop_collection first if you want to recreate."}
                schema = client.create_schema(auto_id=auto_id, enable_dynamic_field=enable_dynamic_field)
                schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=auto_id)
                schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)
                index_params = client.prepare_index_params()
                index_params.add_index(
                    field_name="vector",
                    index_type=index_type,
                    metric_type=metric_type,
                    index_name="vector_index",
                )
                client.create_collection(collection_name=name, schema=schema, index_params=index_params)
                return {"success": True, "data": f"Created collection '{name}' with dim={dimension}", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def drop_collection(self, name: str) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                client.drop_collection(name)
                return {"success": True, "data": f"Dropped collection '{name}'", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def insert(self, collection: str, data: list[dict], **kwargs) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                result = client.insert(collection_name=collection, data=data)
                insert_count = result.get("insert_count", 0) if isinstance(result, dict) else getattr(result, "insert_count", 0)
                return {"success": True, "data": {"insert_count": insert_count}, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def search(self, collection: str, vector: list[float], top_k: int = 10, **kwargs) -> dict:
        metric_type = kwargs.get("metric_type", "L2")
        search_params = kwargs.get("search_params", {})
        output_fields = kwargs.get("output_fields", ["id"])
        filter_expr = kwargs.get("filter_expr", None)

        def _sync():
            with self._lock:
                client = self._get_client()
                sp = dict(search_params)
                if "metric_type" not in sp:
                    sp["metric_type"] = metric_type
                if "params" not in sp:
                    sp["params"] = {"nprobe": 10}
                s_kwargs = {
                    "collection_name": collection,
                    "data": [vector],
                    "limit": top_k,
                    "search_params": sp,
                    "output_fields": output_fields,
                }
                if filter_expr:
                    s_kwargs["filter"] = filter_expr
                results = client.search(**s_kwargs)
                search_results = []
                if results and len(results) > 0:
                    for hit in results[0]:
                        if isinstance(hit, dict):
                            search_results.append({"id": hit.get("id", ""), "distance": hit.get("distance", 0.0)})
                        else:
                            search_results.append({"id": getattr(hit, "id", ""), "distance": getattr(hit, "distance", 0.0)})
                return {"success": True, "data": {"result_count": len(search_results), "results": search_results}, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def query(self, collection: str, filter_expr: str, **kwargs) -> dict:
        output_fields = kwargs.get("output_fields", ["id"])
        limit = kwargs.get("limit", 100)

        def _sync():
            with self._lock:
                client = self._get_client()
                results = client.query(
                    collection_name=collection,
                    filter=filter_expr,
                    output_fields=output_fields,
                    limit=limit,
                )
                return {"success": True, "data": {"result_count": len(results) if results else 0, "sample": (results or [])[:10]}, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def delete(self, collection: str, ids: list[str], **kwargs) -> dict:
        filter_expr = kwargs.get("filter_expr", None)

        def _sync():
            with self._lock:
                client = self._get_client()
                d_kwargs: dict = {"collection_name": collection}
                if ids:
                    d_kwargs["ids"] = ids
                elif filter_expr:
                    d_kwargs["filter"] = filter_expr
                else:
                    return {"success": False, "data": None, "error": "Must provide ids or filter_expr"}
                client.delete(**d_kwargs)
                return {"success": True, "data": f"Deleted records from '{collection}'", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def upsert(self, collection: str, data: list[dict], **kwargs) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                result = client.upsert(collection_name=collection, data=data)
                upsert_count = result.get("upsert_count", 0) if isinstance(result, dict) else getattr(result, "upsert_count", 0)
                return {"success": True, "data": {"upsert_count": upsert_count}, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def flush(self, collection: str) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                client.flush(collection_name=collection)
                return {"success": True, "data": f"Flushed collection '{collection}'", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def load_collection(self, name: str) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                client.load_collection(collection_name=name)
                return {"success": True, "data": f"Loaded collection '{name}'", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def release_collection(self, name: str) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                client.release_collection(collection_name=name)
                return {"success": True, "data": f"Released collection '{name}'", "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def get_collection_info(self, name: str) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                info = client.describe_collection(name)
                return {"success": True, "data": info, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def list_collections(self) -> list[str]:
        def _sync():
            with self._lock:
                client = self._get_client()
                return client.list_collections()

        try:
            return await asyncio.to_thread(_sync)
        except Exception:
            return []

    async def health_check(self) -> dict:
        def _sync():
            with self._lock:
                client = self._get_client()
                version = client.get_server_version()
                return {"success": True, "data": {"version": version}, "error": None}

        try:
            return await asyncio.to_thread(_sync)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
