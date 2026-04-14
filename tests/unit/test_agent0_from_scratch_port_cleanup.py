import subprocess
from pathlib import Path
from unittest.mock import patch

from src.agents.agent0_env_recon import DBInfo, EnvReconAgent


class _DummySocket:
    def __init__(self, connect_result: int):
        self._connect_result = connect_result

    def connect_ex(self, *_args, **_kwargs):
        return self._connect_result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_cleanup_containers_by_port_without_name_prefix():
    agent = EnvReconAgent()

    ps_out = "cid_1\tlegacy-container\ncid_2\tother-project-api\n"

    with patch(
        "src.agents.agent0_env_recon.subprocess.run",
        side_effect=[
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout=ps_out, stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr=""),
        ],
    ) as mock_run:
        removed = agent._cleanup_containers_publishing_port(8081)

    assert removed == 2
    rm_calls = [c for c in mock_run.call_args_list if c.args and c.args[0][:3] == ["docker", "rm", "-f"]]
    assert len(rm_calls) == 2
    removed_ids = {c.args[0][3] for c in rm_calls}
    assert removed_ids == {"cid_1", "cid_2"}


def test_spin_up_sandbox_from_scratch_retries_after_port_conflict():
    agent = EnvReconAgent()
    db_info = DBInfo(db_name="weaviate", version="1.36.9")
    compose_file = str(Path("C:/tmp/fake-run/docker-compose.yml"))

    port_conflict = subprocess.CalledProcessError(
        returncode=1,
        cmd=["docker", "compose", "up", "-d"],
        stderr="Bind for 0.0.0.0:8081 failed: port is already allocated",
    )

    with patch("socket.socket", return_value=_DummySocket(connect_result=111)), patch(
        "src.agents.agent0_env_recon.subprocess.run",
        side_effect=[
            port_conflict,
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="abc123\tforeign-weaviate\n", stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="started", stderr=""),
        ],
    ) as mock_run, patch("time.sleep", return_value=None):
        ok = agent._spin_up_sandbox(
            db_info=db_info,
            compose_file=compose_file,
            endpoint="localhost:8081",
            from_scratch=True,
        )

    assert ok is True
    compose_calls = [
        c
        for c in mock_run.call_args_list
        if c.args and c.args[0][:4] == ["docker", "compose", "--ansi", "never"]
    ]
    assert len(compose_calls) == 2
