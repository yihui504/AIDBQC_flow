import pytest

pytestmark = pytest.mark.integration

DIMENSION = 8


class TestQdrantCRUD:
    async def test_create_and_drop_collection(self, qdrant_adapter, collection_prefix):
        name = f"{collection_prefix}_crud"
        r = await qdrant_adapter.create_collection(name, DIMENSION)
        assert r["success"], f"create failed: {r['error']}"

        collections = await qdrant_adapter.list_collections()
        assert name in collections

        r = await qdrant_adapter.drop_collection(name)
        assert r["success"], f"drop failed: {r['error']}"

    async def test_insert_and_search(self, qdrant_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_ins"
        await qdrant_adapter.create_collection(name, DIMENSION)

        data = [{"id": i, "vector": v} for i, v in enumerate(sample_vectors)]
        r = await qdrant_adapter.insert(name, data)
        assert r["success"], f"insert failed: {r['error']}"

        r = await qdrant_adapter.search(name, sample_vectors[0], top_k=3)
        assert r["success"], f"search failed: {r['error']}"
        assert r["data"]["result_count"] >= 1

        await qdrant_adapter.drop_collection(name)

    async def test_query(self, qdrant_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_query"
        await qdrant_adapter.create_collection(name, DIMENSION)

        data = [{"id": i, "vector": v} for i, v in enumerate(sample_vectors)]
        await qdrant_adapter.insert(name, data)

        r = await qdrant_adapter.query(name, "{}", limit=10)
        assert r["success"], f"query failed: {r['error']}"
        assert r["data"]["result_count"] >= 1

        await qdrant_adapter.drop_collection(name)

    async def test_delete(self, qdrant_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_del"
        await qdrant_adapter.create_collection(name, DIMENSION)

        data = [{"id": i, "vector": v} for i, v in enumerate(sample_vectors)]
        await qdrant_adapter.insert(name, data)

        r = await qdrant_adapter.delete(name, ids=["0", "1"])
        assert r["success"], f"delete failed: {r['error']}"

        await qdrant_adapter.drop_collection(name)

    async def test_upsert_delegates_to_insert(self, qdrant_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_upsert"
        await qdrant_adapter.create_collection(name, DIMENSION)

        data = [{"id": 0, "vector": sample_vectors[0]}]
        await qdrant_adapter.insert(name, data)

        updated = [{"id": 0, "vector": [0.9] * DIMENSION}]
        r = await qdrant_adapter.upsert(name, updated)
        assert r["success"], f"upsert failed: {r['error']}"

        await qdrant_adapter.drop_collection(name)

    async def test_get_collection_info(self, qdrant_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_info"
        await qdrant_adapter.create_collection(name, DIMENSION)

        data = [{"id": 0, "vector": sample_vectors[0]}]
        await qdrant_adapter.insert(name, data)

        r = await qdrant_adapter.get_collection_info(name)
        assert r["success"], f"get_collection_info failed: {r['error']}"
        assert r["data"]["points_count"] >= 1

        await qdrant_adapter.drop_collection(name)

    async def test_health_check(self, qdrant_adapter):
        r = await qdrant_adapter.health_check()
        assert r["success"], f"health_check failed: {r['error']}"

    async def test_unsupported_operations(self, qdrant_adapter, collection_prefix):
        name = f"{collection_prefix}_unsup"
        await qdrant_adapter.create_collection(name, DIMENSION)

        r = await qdrant_adapter.flush(name)
        assert not r["success"]
        assert "Not supported" in r["error"]

        r = await qdrant_adapter.load_collection(name)
        assert not r["success"]

        r = await qdrant_adapter.release_collection(name)
        assert not r["success"]

        await qdrant_adapter.drop_collection(name)

    async def test_duplicate_collection_error(self, qdrant_adapter, collection_prefix):
        name = f"{collection_prefix}_dup"
        r1 = await qdrant_adapter.create_collection(name, DIMENSION)
        assert r1["success"]

        r2 = await qdrant_adapter.create_collection(name, DIMENSION)
        assert not r2["success"]
        assert "already exists" in r2["error"]

        await qdrant_adapter.drop_collection(name)


class TestQdrantErrorInjection:
    async def test_search_nonexistent_collection(self, qdrant_adapter):
        r = await qdrant_adapter.search("nonexistent_col_99999", [0.1] * DIMENSION, top_k=3)
        assert not r["success"]

    async def test_insert_missing_vector(self, qdrant_adapter, collection_prefix):
        name = f"{collection_prefix}_novector"
        await qdrant_adapter.create_collection(name, DIMENSION)

        bad_data = [{"id": 0}]
        r = await qdrant_adapter.insert(name, bad_data)
        assert not r["success"]

        await qdrant_adapter.drop_collection(name)

    async def test_insert_empty_data(self, qdrant_adapter, collection_prefix):
        name = f"{collection_prefix}_empty"
        await qdrant_adapter.create_collection(name, DIMENSION)

        r = await qdrant_adapter.insert(name, [])
        assert not r["success"]

        await qdrant_adapter.drop_collection(name)
