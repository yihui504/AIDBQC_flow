from __future__ import annotations

import json
import time
import logging
from typing import Optional

from pymilvus import MilvusClient, DataType
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import AppConfig
from src.models.probe import CollectionInfo, ProbeResult

logger = logging.getLogger(__name__)

TEST_COLLECTION_PREFIX = "qc_test_"


class DBOperationResult(BaseModel):
    success: bool
    operation: str
    collection_name: Optional[str] = None
    data: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    request_params: Optional[str] = None
    db_state_before: Optional[str] = None
    db_state_after: Optional[str] = None


def _ensure_test_prefix(name: str) -> str:
    if not name.startswith(TEST_COLLECTION_PREFIX):
        return f"{TEST_COLLECTION_PREFIX}{name}"
    return name


def _is_test_collection(name: str) -> bool:
    return name.startswith(TEST_COLLECTION_PREFIX)


class MilvusOperator:
    def __init__(self, config: AppConfig):
        self.config = config
        self._client: Optional[MilvusClient] = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _get_client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(
                uri=f"http://{next((i.host for i in self.config.database.instances if i.type == 'milvus'), 'localhost')}:{next((i.port for i in self.config.database.instances if i.type == 'milvus'), 19530)}",
            )
        return self._client

    def _snapshot_state(self, collection_name: Optional[str] = None) -> str:
        try:
            client = self._get_client()
            collections = client.list_collections()
            state = {"collections": collections}
            if collection_name and collection_name in collections:
                info = client.describe_collection(collection_name)
                state["target"] = {
                    "name": info.get("collection_name", ""),
                    "row_count": info.get("num_entities", 0),
                }
            return json.dumps(state, default=str)[:500]
        except Exception:
            return "state_unavailable"

    def create_collection(
        self,
        collection_name: str,
        dimension: int = 128,
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2",
        auto_id: bool = True,
        enable_dynamic_field: bool = True,
    ) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {
            "collection_name": safe_name,
            "dimension": dimension,
            "index_type": index_type,
            "metric_type": metric_type,
        }
        state_before = self._snapshot_state()
        try:
            client = self._get_client()
            if client.has_collection(safe_name):
                logger.warning(f"Dropping existing test collection: {safe_name}")
                client.drop_collection(safe_name)

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

            client.create_collection(
                collection_name=safe_name,
                schema=schema,
                index_params=index_params,
            )
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="create_collection",
                collection_name=safe_name,
                data=f"Created collection '{safe_name}' with dim={dimension}, index={index_type}, metric={metric_type}",
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="create_collection",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def insert_data(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: Optional[list[dict]] = None,
    ) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {"collection_name": safe_name, "vector_count": len(vectors), "dimension": len(vectors[0]) if vectors else 0}
        state_before = self._snapshot_state(safe_name)
        try:
            client = self._get_client()
            data = []
            for i, v in enumerate(vectors):
                row = {"vector": v}
                if payloads and i < len(payloads):
                    row.update(payloads[i])
                data.append(row)
            result = client.insert(collection_name=safe_name, data=data)
            insert_count = result.get("insert_count", 0) if isinstance(result, dict) else getattr(result, "insert_count", 0)
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="insert_data",
                collection_name=safe_name,
                data=f"Inserted {len(vectors)} vectors, insert_count={insert_count}",
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="insert_data",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        metric_type: str = "L2",
        search_params: Optional[dict] = None,
        output_fields: Optional[list[str]] = None,
        filter_expr: Optional[str] = None,
    ) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {
            "collection_name": safe_name,
            "top_k": top_k,
            "metric_type": metric_type,
            "query_dim": len(query_vector),
        }
        if search_params:
            params["search_params"] = search_params
        state_before = self._snapshot_state(safe_name)
        try:
            client = self._get_client()
            sp = search_params or {}
            if "metric_type" not in sp:
                sp["metric_type"] = metric_type
            if "params" not in sp:
                sp["params"] = {"nprobe": 10}

            kwargs = {
                "collection_name": safe_name,
                "data": [query_vector],
                "limit": top_k,
                "search_params": sp,
                "output_fields": output_fields or ["id"],
            }
            if filter_expr:
                kwargs["filter"] = filter_expr

            results = client.search(**kwargs)
            search_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    if isinstance(hit, dict):
                        search_results.append({
                            "id": hit.get("id", ""),
                            "distance": hit.get("distance", 0.0),
                        })
                    else:
                        search_results.append({
                            "id": getattr(hit, "id", ""),
                            "distance": getattr(hit, "distance", 0.0),
                        })
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="search",
                collection_name=safe_name,
                data=json.dumps({"result_count": len(search_results), "results": search_results[:5]}),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="search",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def query(
        self,
        collection_name: str,
        filter_expr: str,
        output_fields: Optional[list[str]] = None,
        limit: int = 100,
    ) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {"collection_name": safe_name, "filter": filter_expr, "limit": limit}
        state_before = self._snapshot_state(safe_name)
        try:
            client = self._get_client()
            results = client.query(
                collection_name=safe_name,
                filter=filter_expr,
                output_fields=output_fields or ["id"],
                limit=limit,
            )
            result_data = results[:10] if results else []
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="query",
                collection_name=safe_name,
                data=json.dumps({"result_count": len(results) if results else 0, "sample": result_data}, default=str)[:2000],
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="query",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def delete_data(self, collection_name: str, ids: Optional[list[int]] = None, filter_expr: Optional[str] = None) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {"collection_name": safe_name}
        if ids:
            params["ids_count"] = len(ids)
        if filter_expr:
            params["filter"] = filter_expr
        state_before = self._snapshot_state(safe_name)
        try:
            client = self._get_client()
            kwargs = {"collection_name": safe_name}
            if ids:
                kwargs["ids"] = ids
            elif filter_expr:
                kwargs["filter"] = filter_expr
            else:
                return DBOperationResult(
                    success=False, operation="delete_data",
                    collection_name=safe_name, error="Must provide ids or filter_expr",
                    duration_ms=0,
                )
            client.delete(**kwargs)
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="delete_data",
                collection_name=safe_name,
                data=f"Deleted records from '{safe_name}'",
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="delete_data",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def upsert_data(
        self,
        collection_name: str,
        vectors: list[list[float]],
        ids: list[int],
        payloads: Optional[list[dict]] = None,
    ) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        params = {"collection_name": safe_name, "vector_count": len(vectors)}
        state_before = self._snapshot_state(safe_name)
        try:
            client = self._get_client()
            data = []
            for i, v in enumerate(vectors):
                row = {"id": ids[i], "vector": v}
                if payloads and i < len(payloads):
                    row.update(payloads[i])
                data.append(row)
            result = client.upsert(collection_name=safe_name, data=data)
            upsert_count = result.get("upsert_count", 0) if isinstance(result, dict) else getattr(result, "upsert_count", 0)
            state_after = self._snapshot_state(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="upsert_data",
                collection_name=safe_name,
                data=f"Upserted {len(vectors)} vectors, upsert_count={upsert_count}",
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before, db_state_after=state_after,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="upsert_data",
                collection_name=safe_name, error=str(e),
                duration_ms=duration, request_params=json.dumps(params),
                db_state_before=state_before,
            )

    def flush(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.flush(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="flush",
                collection_name=safe_name,
                data=f"Flushed collection '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="flush",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def load_collection(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.load_collection(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="load_collection",
                collection_name=safe_name,
                data=f"Loaded collection '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="load_collection",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def release_collection(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.release_collection(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="release_collection",
                collection_name=safe_name,
                data=f"Released collection '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="release_collection",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def get_load_state(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            state = client.get_load_state(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="get_load_state",
                collection_name=safe_name,
                data=json.dumps(state, default=str) if isinstance(state, (dict, list)) else str(state),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="get_load_state",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def get_collection_info(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            info = client.describe_collection(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="get_collection_info",
                collection_name=safe_name,
                data=json.dumps(info, default=str)[:1000],
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="get_collection_info",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def list_collections(self) -> DBOperationResult:
        start = time.time()
        try:
            client = self._get_client()
            collections = client.list_collections()
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="list_collections",
                data=json.dumps(collections),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="list_collections",
                error=str(e), duration_ms=duration,
            )

    def drop_collection(self, collection_name: str, force: bool = False) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        if not _is_test_collection(safe_name) and not force:
            return DBOperationResult(
                success=False, operation="drop_collection",
                collection_name=safe_name,
                error=f"Refusing to drop non-test collection '{safe_name}'. Use force=True to override.",
                duration_ms=0,
            )
        try:
            client = self._get_client()
            client.drop_collection(safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="drop_collection",
                collection_name=safe_name,
                data=f"Dropped collection '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="drop_collection",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def create_partition(self, collection_name: str, partition_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.create_partition(collection_name=safe_name, partition_name=partition_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="create_partition",
                collection_name=safe_name,
                data=f"Created partition '{partition_name}' in '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="create_partition",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def drop_partition(self, collection_name: str, partition_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.drop_partition(collection_name=safe_name, partition_name=partition_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="drop_partition",
                collection_name=safe_name,
                data=f"Dropped partition '{partition_name}' from '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="drop_partition",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def compact(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            client.compact(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="compact",
                collection_name=safe_name,
                data=f"Compaction triggered for '{safe_name}'",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="compact",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def get_compaction_state(self, collection_name: str) -> DBOperationResult:
        start = time.time()
        safe_name = _ensure_test_prefix(collection_name)
        try:
            client = self._get_client()
            state = client.get_compaction_state(collection_name=safe_name)
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="get_compaction_state",
                collection_name=safe_name,
                data=json.dumps(state, default=str) if isinstance(state, (dict, list)) else str(state),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="get_compaction_state",
                collection_name=safe_name, error=str(e),
                duration_ms=duration,
            )

    def health_check(self) -> DBOperationResult:
        start = time.time()
        try:
            client = self._get_client()
            version = client.get_server_version()
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=True, operation="health_check",
                data=f"Milvus server version: {version}",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return DBOperationResult(
                success=False, operation="health_check",
                error=str(e), duration_ms=duration,
            )
