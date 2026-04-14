import importlib
import os
import re
from pathlib import Path


def test_milvus_compose_uses_env_credentials_not_default_literal():
    repo_root = Path(__file__).resolve().parents[2]
    compose_file = repo_root / "docker-compose.milvus.yml"
    content = compose_file.read_text(encoding="utf-8")

    assert "minioadmin" not in content
    assert "MILVUS_MINIO_ACCESS_KEY" in content
    assert "MILVUS_MINIO_SECRET_KEY" in content


def test_agent_factory_no_global_proxy_pollution_by_default(monkeypatch):
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AGENT_FACTORY_ENABLE_GLOBAL_PROXY", "0")
    monkeypatch.setenv("AGENT_FACTORY_ENABLE_HF_OFFLINE", "0")

    import src.agents.agent_factory as agent_factory
    importlib.reload(agent_factory)
    agent_factory.configure_runtime_environment()

    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        assert os.getenv(key) in (None, "")


def test_env_recon_generated_milvus_compose_avoids_default_minio_creds(tmp_path):
    from src.agents.agent0_env_recon import EnvReconAgent, DBInfo

    # Avoid heavy __init__ path (LLM creation); only keep fields needed by _generate_docker_compose.
    agent = EnvReconAgent.__new__(EnvReconAgent)
    agent.runs_dir = str(tmp_path)
    agent._weaviate_fallback_version = "1.36.9"
    agent._docker_tag_for = lambda db_name, version: "2.6.12"

    compose_file, endpoint, credentials = agent._generate_docker_compose(
        DBInfo(db_name="milvus", version="2.6.12"),
        run_id="unit-test-run"
    )

    assert endpoint == "localhost:19530"
    assert credentials.get("minio_access_key")
    assert credentials.get("minio_secret_key")
    assert credentials["minio_access_key"] != "minioadmin"
    assert credentials["minio_secret_key"] != "minioadmin"

    content = Path(compose_file).read_text(encoding="utf-8")
    assert "minioadmin" not in content
    assert credentials["minio_access_key"] in content
    assert credentials["minio_secret_key"] in content


def test_no_bare_except_in_src_for_observability():
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / "src"

    bare_except_pattern = re.compile(r"^\s*except\s*:\s*$", re.MULTILINE)
    offenders = []
    for file in src_dir.rglob("*.py"):
        content = file.read_text(encoding="utf-8")
        if bare_except_pattern.search(content):
            offenders.append(str(file))

    assert offenders == []
