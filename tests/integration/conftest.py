import os
import uuid

import pytest

from src.adapters.milvus import MilvusAdapter
from src.adapters.qdrant import QdrantAdapter


def _unique_prefix() -> str:
    return f"e2e_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def collection_prefix() -> str:
    return _unique_prefix()


@pytest.fixture
async def milvus_adapter():
    host = os.environ.get("MILVUS_HOST", "localhost")
    port = int(os.environ.get("MILVUS_PORT", "19530"))
    adapter = MilvusAdapter(host=host, port=port, timeout=30)
    try:
        r = await adapter.health_check()
        if not r.get("success", False):
            pytest.skip(f"Milvus not available: {r.get('error', 'unknown')}")
    except Exception as e:
        pytest.skip(f"Milvus not available: {e}")
    yield adapter
    await adapter.close()


@pytest.fixture
async def qdrant_adapter():
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    adapter = QdrantAdapter(host=host, port=port)
    try:
        r = await adapter.health_check()
        if not r.get("success", False):
            pytest.skip(f"Qdrant not available: {r.get('error', 'unknown')}")
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")
    yield adapter
    await adapter.close()


@pytest.fixture
def sample_vectors() -> list[list[float]]:
    return [
        [0.1 * i] * 8 for i in range(1, 6)
    ]
