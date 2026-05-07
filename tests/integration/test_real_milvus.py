import pytest

pytestmark = pytest.mark.integration

DIMENSION = 8


class TestMilvusCRUD:
    async def test_create_and_drop_collection(self, milvus_adapter, collection_prefix):
        name = f"{collection_prefix}_crud"
        r = await milvus_adapter.create_collection(name, DIMENSION)
        assert r["success"], f"create failed: {r['error']}"

        collections = await milvus_adapter.list_collections()
        assert name in collections

        r = await milvus_adapter.drop_collection(name)
        assert r["success"], f"drop failed: {r['error']}"

    async def test_insert_and_search(self, milvus_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_ins"
        await milvus_adapter.create_collection(name, DIMENSION)

        data = [{"vector": v} for v in sample_vectors]
        r = await milvus_adapter.insert(name, data)
        assert r["success"], f"insert failed: {r['error']}"
        assert r["data"]["insert_count"] == len(sample_vectors)

        await milvus_adapter.flush(name)

        r = await milvus_adapter.search(name, sample_vectors[0], top_k=3)
        assert r["success"], f"search failed: {r['error']}"
        assert r["data"]["result_count"] >= 1

        await milvus_adapter.drop_collection(name)

    async def test_query(self, milvus_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_query"
        await milvus_adapter.create_collection(name, DIMENSION)

        data = [{"vector": v} for v in sample_vectors]
        await milvus_adapter.insert(name, data)
        await milvus_adapter.flush(name)

        r = await milvus_adapter.query(name, "id >= 0", output_fields=["id"], limit=10)
        assert r["success"], f"query failed: {r['error']}"
        assert r["data"]["result_count"] >= 1

        await milvus_adapter.drop_collection(name)

    async def test_delete(self, milvus_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_del"
        await milvus_adapter.create_collection(name, DIMENSION, auto_id=False)

        data = [{"id": i + 1, "vector": v} for i, v in enumerate(sample_vectors)]
        await milvus_adapter.insert(name, data)
        await milvus_adapter.flush(name)

        r = await milvus_adapter.delete(name, ids=["1", "2"])
        assert r["success"], f"delete failed: {r['error']}"

        await milvus_adapter.drop_collection(name)

    async def test_upsert(self, milvus_adapter, collection_prefix, sample_vectors):
        name = f"{collection_prefix}_upsert"
        await milvus_adapter.create_collection(name, DIMENSION, auto_id=False)

        data = [{"id": i + 1, "vector": v} for i, v in enumerate(sample_vectors)]
        await milvus_adapter.insert(name, data)
        await milvus_adapter.flush(name)

        updated = [{"id": 1, "vector": [0.9] * DIMENSION}]
        r = await milvus_adapter.upsert(name, updated)
        assert r["success"], f"upsert failed: {r['error']}"

        await milvus_adapter.drop_collection(name)

    async def test_get_collection_info(self, milvus_adapter, collection_prefix):
        name = f"{collection_prefix}_info"
        await milvus_adapter.create_collection(name, DIMENSION)

        r = await milvus_adapter.get_collection_info(name)
        assert r["success"], f"get_collection_info failed: {r['error']}"

        await milvus_adapter.drop_collection(name)

    async def test_health_check(self, milvus_adapter):
        r = await milvus_adapter.health_check()
        assert r["success"], f"health_check failed: {r['error']}"
        assert "version" in r["data"]

    async def test_duplicate_collection_error(self, milvus_adapter, collection_prefix):
        name = f"{collection_prefix}_dup"
        r1 = await milvus_adapter.create_collection(name, DIMENSION)
        assert r1["success"]

        r2 = await milvus_adapter.create_collection(name, DIMENSION)
        assert not r2["success"]
        assert "already exists" in r2["error"]

        await milvus_adapter.drop_collection(name)


class TestMilvusErrorInjection:
    async def test_search_nonexistent_collection(self, milvus_adapter):
        r = await milvus_adapter.search("nonexistent_col_99999", [0.1] * DIMENSION, top_k=3)
        assert not r["success"]

    async def test_insert_invalid_dimension(self, milvus_adapter, collection_prefix):
        name = f"{collection_prefix}_dimerr"
        await milvus_adapter.create_collection(name, DIMENSION)

        bad_data = [{"vector": [0.1] * 4}]
        r = await milvus_adapter.insert(name, bad_data)
        assert not r["success"]

        await milvus_adapter.drop_collection(name)

    async def test_insert_empty_data(self, milvus_adapter, collection_prefix):
        name = f"{collection_prefix}_empty"
        await milvus_adapter.create_collection(name, DIMENSION)

        r = await milvus_adapter.insert(name, [])
        assert r["success"]
        assert r["data"]["insert_count"] == 0

        await milvus_adapter.drop_collection(name)
