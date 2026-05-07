from __future__ import annotations

import re
import asyncio
from typing import Optional

import asyncpg

from src.adapters.base import VectorDBBase

_TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_table_name(name: str) -> str:
    safe = name.replace("-", "_").replace(" ", "_")
    if not _TABLE_NAME_RE.match(safe):
        raise ValueError(f"Invalid table name: {name}")
    return safe


class PgvectorAdapter(VectorDBBase):
    def __init__(self, connection_string: str = ""):
        self._connection_string = connection_string
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    self._pool = await asyncpg.create_pool(self._connection_string, min_size=2, max_size=10)
                    async with self._pool.acquire() as conn:
                        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        return self._pool

    async def create_collection(self, name: str, dimension: int, **kwargs) -> dict:
        try:
            if not isinstance(dimension, int) or dimension < 1 or dimension > 32768:
                return {"success": False, "data": None, "error": f"Invalid dimension: {dimension}. Must be integer in range [1, 32768]"}
            pool = await self._get_pool()
            safe_name = _validate_table_name(name)
            async with pool.acquire() as conn:
                exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)", safe_name)
                if exists:
                    return {"success": False, "data": None, "error": f"Table '{safe_name}' already exists. Use drop_collection first if you want to recreate."}
                await conn.execute(
                    f'CREATE TABLE "{safe_name}" (id TEXT PRIMARY KEY, vector vector({dimension}), payload JSONB)'
                )
            return {"success": True, "data": f"Created table '{safe_name}' with dim={dimension}", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def drop_collection(self, name: str) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(name)
            async with pool.acquire() as conn:
                await conn.execute(f'DROP TABLE IF EXISTS "{safe_name}"')
            return {"success": True, "data": f"Dropped table '{safe_name}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def insert(self, collection: str, data: list[dict], **kwargs) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(collection)
            inserted = 0
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for item in data:
                        vector = item.get("vector")
                        item_id = str(item.get("id", inserted))
                        payload = {k: v for k, v in item.items() if k not in ("vector", "id")}
                        if vector:
                            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
                            await conn.execute(
                                f'INSERT INTO "{safe_name}" (id, vector, payload) VALUES ($1, $2::vector, $3)',
                                item_id, vector_str, payload,
                            )
                        else:
                            await conn.execute(
                                f'INSERT INTO "{safe_name}" (id, payload) VALUES ($1, $2)',
                                item_id, payload,
                            )
                        inserted += 1
            return {"success": True, "data": {"insert_count": inserted}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def search(self, collection: str, vector: list[float], top_k: int = 10, **kwargs) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(collection)
            metric = kwargs.get("metric_type", "L2")
            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
            if metric == "IP":
                order_expr = f'("{safe_name}".vector <#> $1::vector)'
            elif metric == "Cosine":
                order_expr = f'("{safe_name}".vector <=> $1::vector)'
            else:
                order_expr = f'("{safe_name}".vector <-> $1::vector)'
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f'SELECT id, payload, {order_expr} AS distance FROM "{safe_name}" ORDER BY {order_expr} LIMIT $2',
                    vector_str, top_k,
                )
            results = [{"id": r["id"], "distance": float(r["distance"]) if r["distance"] is not None else None, "payload": r["payload"]} for r in rows]
            return {"success": True, "data": {"result_count": len(results), "results": results}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def query(self, collection: str, filter_expr: str, **kwargs) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(collection)
            limit = kwargs.get("limit", 100)
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f'SELECT id, payload FROM "{safe_name}" WHERE payload::text @> $1::text LIMIT $2',
                    filter_expr, limit,
                )
            items = [{"id": r["id"], "payload": r["payload"]} for r in rows]
            return {"success": True, "data": {"result_count": len(items), "sample": items[:10]}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def delete(self, collection: str, ids: list[str], **kwargs) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(collection)
            async with pool.acquire() as conn:
                await conn.execute(
                    f'DELETE FROM "{safe_name}" WHERE id = ANY($1)',
                    ids,
                )
            return {"success": True, "data": f"Deleted {len(ids)} records from '{collection}'", "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def upsert(self, collection: str, data: list[dict], **kwargs) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(collection)
            upserted = 0
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for item in data:
                        vector = item.get("vector")
                        item_id = str(item.get("id", upserted))
                        payload = {k: v for k, v in item.items() if k not in ("vector", "id")}
                        if vector:
                            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
                            await conn.execute(
                                f'INSERT INTO "{safe_name}" (id, vector, payload) VALUES ($1, $2::vector, $3) ON CONFLICT (id) DO UPDATE SET vector = $2::vector, payload = $3',
                                item_id, vector_str, payload,
                            )
                        else:
                            await conn.execute(
                                f'INSERT INTO "{safe_name}" (id, payload) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET payload = $2',
                                item_id, payload,
                            )
                        upserted += 1
            return {"success": True, "data": {"upsert_count": upserted}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def flush(self, collection: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by pgvector"}

    async def load_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by pgvector"}

    async def release_collection(self, name: str) -> dict:
        return {"success": False, "data": None, "error": "Not supported by pgvector"}

    async def get_collection_info(self, name: str) -> dict:
        try:
            pool = await self._get_pool()
            safe_name = _validate_table_name(name)
            async with pool.acquire() as conn:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{safe_name}"')
            return {"success": True, "data": {"name": safe_name, "row_count": count}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def list_collections(self) -> list[str]:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            return [r["tablename"] for r in rows]
        except Exception:
            return []

    async def health_check(self) -> dict:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
            return {"success": True, "data": {"version": version}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def close(self) -> None:
        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
