from pathlib import Path


def test_weaviate_compose_disables_anonymous_and_binds_localhost():
    compose_file = Path(__file__).resolve().parents[2] / "docker-compose.weaviate.yml"
    content = compose_file.read_text(encoding="utf-8")

    assert "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=false" in content
    assert '"127.0.0.1:8081:8080"' in content
    assert '"127.0.0.1:50051:50051"' in content
