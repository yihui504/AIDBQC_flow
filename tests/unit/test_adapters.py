from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.base import VectorDBBase
from src.adapters.factory import AdapterFactory
from src.config import DBInstanceConfig


def _make_milvus_adapter():
    from src.adapters.milvus import MilvusAdapter
    adapter = MilvusAdapter(host="localhost", port=19530)
    mock_client = MagicMock()
    mock_client.get_server_version.return_value = "2.6.11"
    mock_client.list_collections.return_value = []
    mock_client.has_collection.return_value = False
    mock_client.create_schema.return_value = MagicMock()
    mock_client.prepare_index_params.return_value = MagicMock()
    mock_client.describe_collection.return_value = {"name": "test", "dimension": 8}
    mock_client.insert.return_value = {"insert_count": 1}
    mock_client.upsert.return_value = {"upsert_count": 1}
    mock_client.search.return_value = [[]]
    mock_client.query.return_value = []
    mock_client.flush.return_value = None
    mock_client.load_collection.return_value = None
    mock_client.release_collection.return_value = None
    adapter._client = mock_client
    return adapter, mock_client


class TestMilvusAdapterCreateCollection:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.create_collection("test_col", 8)
        )
        assert result["success"] is True
        assert "test_col" in result["data"]
        mock_client.create_collection.assert_called_once()

    def test_already_exists(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.has_collection.return_value = True
        result = asyncio.get_event_loop().run_until_complete(
            adapter.create_collection("test_col", 8)
        )
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_exception_returns_error(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.create_collection.side_effect = Exception("RPC error")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.create_collection("test_col", 8)
        )
        assert result["success"] is False
        assert "RPC error" in result["error"]


class TestMilvusAdapterInsert:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.insert("test_col", [{"vector": [0.1, 0.2]}])
        )
        assert result["success"] is True
        assert result["data"]["insert_count"] == 1

    def test_exception_returns_error(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.insert.side_effect = Exception("dimension mismatch")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.insert("test_col", [{"vector": [0.1]}])
        )
        assert result["success"] is False


class TestMilvusAdapterSearch:
    def test_success_empty_results(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.search("test_col", [0.1, 0.2], top_k=5)
        )
        assert result["success"] is True
        assert result["data"]["result_count"] == 0

    def test_success_with_results(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_hit = MagicMock()
        mock_hit.id = 1
        mock_hit.distance = 0.5
        mock_client.search.return_value = [[mock_hit]]
        result = asyncio.get_event_loop().run_until_complete(
            adapter.search("test_col", [0.1, 0.2], top_k=5)
        )
        assert result["success"] is True
        assert result["data"]["result_count"] == 1
        assert result["data"]["results"][0]["id"] == 1

    def test_with_filter_expr(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.search("test_col", [0.1, 0.2], top_k=5, filter_expr="id > 0")
        )
        assert result["success"] is True


class TestMilvusAdapterQuery:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.query.return_value = [{"id": 1}, {"id": 2}]
        result = asyncio.get_event_loop().run_until_complete(
            adapter.query("test_col", "id >= 0")
        )
        assert result["success"] is True
        assert result["data"]["result_count"] == 2


class TestMilvusAdapterDelete:
    def test_by_ids(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.delete("test_col", ids=["1", "2"])
        )
        assert result["success"] is True

    def test_by_filter(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.delete("test_col", ids=[], filter_expr="id > 100")
        )
        assert result["success"] is True

    def test_no_ids_no_filter(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.delete("test_col", ids=[])
        )
        assert result["success"] is False
        assert "Must provide" in result["error"]


class TestMilvusAdapterHealthCheck:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.health_check()
        )
        assert result["success"] is True
        assert result["data"]["version"] == "2.6.11"

    def test_failure(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.get_server_version.side_effect = Exception("connection refused")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.health_check()
        )
        assert result["success"] is False


class TestMilvusAdapterListCollections:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.list_collections.return_value = ["col1", "col2"]
        result = asyncio.get_event_loop().run_until_complete(
            adapter.list_collections()
        )
        assert result == ["col1", "col2"]

    def test_failure_returns_empty(self):
        adapter, mock_client = _make_milvus_adapter()
        mock_client.list_collections.side_effect = Exception("fail")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.list_collections()
        )
        assert result == []


class TestMilvusAdapterClose:
    def test_close_resets_client(self):
        adapter, mock_client = _make_milvus_adapter()
        assert adapter._client is not None
        asyncio.get_event_loop().run_until_complete(adapter.close())
        assert adapter._client is None
        mock_client.close.assert_called_once()


class TestMilvusAdapterUpsert:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.upsert("test_col", [{"id": 1, "vector": [0.1, 0.2]}])
        )
        assert result["success"] is True
        assert result["data"]["upsert_count"] == 1


class TestMilvusAdapterFlush:
    def test_success(self):
        adapter, mock_client = _make_milvus_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.flush("test_col")
        )
        assert result["success"] is True


class TestAdapterFactory:
    def test_create_milvus(self):
        config = DBInstanceConfig(type="milvus", host="localhost", port=19530)
        adapter = AdapterFactory.create(config)
        from src.adapters.milvus import MilvusAdapter
        assert isinstance(adapter, MilvusAdapter)

    def test_create_qdrant(self):
        config = DBInstanceConfig(type="qdrant", host="localhost", port=6333)
        adapter = AdapterFactory.create(config)
        from src.adapters.qdrant import QdrantAdapter
        assert isinstance(adapter, QdrantAdapter)

    def test_unsupported_type(self):
        mock_config = MagicMock()
        mock_config.type = "redis"
        with pytest.raises(ValueError, match="Unsupported"):
            AdapterFactory.create(mock_config)

    def test_milvus_config_passthrough(self):
        config = DBInstanceConfig(type="milvus", host="10.0.0.1", port=19531)
        adapter = AdapterFactory.create(config)
        assert adapter._host == "10.0.0.1"
        assert adapter._port == 19531


class TestQdrantAdapter:
    def _make_qdrant_adapter(self):
        from src.adapters.qdrant import QdrantAdapter
        adapter = QdrantAdapter(host="localhost", port=6333)
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = None
        mock_client.delete_collection.return_value = None
        mock_client.upsert.return_value = MagicMock(operation_id=1)
        mock_client.query_points.return_value = MagicMock(points=[])
        mock_client.scroll.return_value = ([], None)
        mock_client.delete.return_value = None
        mock_client.get_collection.return_value = MagicMock(
            points_count=0, vectors_count=0, status="green"
        )
        adapter._client = mock_client
        return adapter, mock_client

    def test_create_collection_success(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.create_collection("test_col", 8)
        )
        assert result["success"] is True

    def test_create_collection_already_exists(self):
        adapter, mock_client = self._make_qdrant_adapter()
        mock_client.collection_exists.return_value = True
        result = asyncio.get_event_loop().run_until_complete(
            adapter.create_collection("test_col", 8)
        )
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_insert_success(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.insert("test_col", [{"id": 1, "vector": [0.1, 0.2]}])
        )
        assert result["success"] is True

    def test_insert_missing_vector(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.insert("test_col", [{"id": 1}])
        )
        assert result["success"] is False
        assert "Missing" in result["error"]

    def test_search_success(self):
        adapter, mock_client = self._make_qdrant_adapter()
        mock_point = MagicMock(id=1, score=0.9, payload={"name": "test"})
        mock_client.query_points.return_value = MagicMock(points=[mock_point])
        result = asyncio.get_event_loop().run_until_complete(
            adapter.search("test_col", [0.1, 0.2], top_k=5)
        )
        assert result["success"] is True
        assert result["data"]["result_count"] == 1

    def test_delete_success(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.delete("test_col", ids=["1", "2"])
        )
        assert result["success"] is True

    def test_upsert_delegates_to_insert(self):
        adapter, mock_client = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.upsert("test_col", [{"id": 1, "vector": [0.1, 0.2]}])
        )
        assert result["success"] is True

    def test_flush_not_supported(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.flush("test_col")
        )
        assert result["success"] is False
        assert "Not supported" in result["error"]

    def test_load_collection_not_supported(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.load_collection("test_col")
        )
        assert result["success"] is False

    def test_health_check_success(self):
        adapter, _ = self._make_qdrant_adapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.health_check()
        )
        assert result["success"] is True

    def test_health_check_failure(self):
        adapter, mock_client = self._make_qdrant_adapter()
        mock_client.get_collections.side_effect = Exception("connection refused")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.health_check()
        )
        assert result["success"] is False

    def test_list_collections_failure_returns_empty(self):
        adapter, mock_client = self._make_qdrant_adapter()
        mock_client.get_collections.side_effect = Exception("fail")
        result = asyncio.get_event_loop().run_until_complete(
            adapter.list_collections()
        )
        assert result == []

    def test_close_resets_client(self):
        adapter, mock_client = self._make_qdrant_adapter()
        assert adapter._client is not None
        asyncio.get_event_loop().run_until_complete(adapter.close())
        assert adapter._client is None


class TestVectorDBBaseAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            VectorDBBase()

    def test_has_all_abstract_methods(self):
        expected = {
            "create_collection", "drop_collection", "insert", "search",
            "query", "delete", "upsert", "flush", "load_collection",
            "release_collection", "get_collection_info", "list_collections",
            "health_check", "close",
        }
        actual = {m for m in dir(VectorDBBase) if getattr(getattr(VectorDBBase, m, None), "__isabstractmethod__", False)}
        assert expected == actual
