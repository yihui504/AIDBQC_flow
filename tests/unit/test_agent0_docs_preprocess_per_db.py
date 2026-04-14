import pytest


def _mk_section(url: str, content: str, title: str = "T", depth: int = 0) -> str:
    return f"Source: {url}\nTitle: {title}\nDepth: {depth}\nContent:\n{content}\n"


def test_agent0_qdrant_docs_filter_keeps_documentation_path_and_rejects_milvus():
    from src.agents.agent0_env_recon import EnvReconAgent
    from src.config import get_config

    agent = EnvReconAgent()
    docs_cfg = get_config().docs
    policy = agent._docs_preprocess_policy("qdrant", docs_cfg)

    good = _mk_section(
        "https://qdrant.tech/documentation/concepts/collections/",
        "collection point vector filter " + ("x" * 600),
    )
    bad = _mk_section(
        "https://milvus.io/docs/v2.6.x/index.md",
        "milvus content " + ("y" * 800),
    )
    raw = "\n".join([good, bad])

    filtered, stats = agent._filter_docs(raw, policy)
    assert "qdrant.tech/documentation" in filtered
    assert "milvus.io/docs" not in filtered
    assert stats["filtered_in"] >= 1

    # Must not abort on a non-empty filtered corpus for this DB.
    agent._ensure_docs_non_empty_or_abort(
        filtered,
        "qdrant",
        where="unit-test.qdrant",
        min_docs=policy.hard_min_docs,
        min_chars=policy.hard_min_chars,
    )

    # Search fallback filter must not accept Milvus when targeting Qdrant.
    assert agent._is_official_docs_url("https://milvus.io/docs/", "qdrant") is False
    assert agent._is_official_docs_url("https://qdrant.tech/documentation/", "qdrant") is True


def test_agent0_weaviate_docs_filter_keeps_developers_path_and_rejects_milvus():
    from src.agents.agent0_env_recon import EnvReconAgent
    from src.config import get_config

    agent = EnvReconAgent()
    docs_cfg = get_config().docs
    policy = agent._docs_preprocess_policy("weaviate", docs_cfg)

    good = _mk_section(
        "https://weaviate.io/developers/weaviate/api/rest/schema",
        "schema class object graphql " + ("x" * 600),
    )
    bad = _mk_section(
        "https://milvus.io/docs/v2.6.x/index.md",
        "milvus content " + ("y" * 800),
    )
    raw = "\n".join([good, bad])

    filtered, stats = agent._filter_docs(raw, policy)
    assert "weaviate.io/developers/weaviate" in filtered
    assert "milvus.io/docs" not in filtered
    assert stats["filtered_in"] >= 1

    agent._ensure_docs_non_empty_or_abort(
        filtered,
        "weaviate",
        where="unit-test.weaviate",
        min_docs=policy.hard_min_docs,
        min_chars=policy.hard_min_chars,
    )

    assert agent._is_official_docs_url("https://milvus.io/docs/", "weaviate") is False
    assert agent._is_official_docs_url("https://weaviate.io/developers/weaviate", "weaviate") is True

