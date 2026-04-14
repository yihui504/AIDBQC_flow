import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.agents.agent6_verifier import IsolatedCodeRunner


class _CfgDisabled:
    def get_bool(self, key, default=False):
        if key == "isolated_mre.enabled":
            return False
        return default


class _CfgEnabled:
    def get_bool(self, key, default=False):
        if key == "isolated_mre.enabled":
            return True
        return default


def test_isolated_runner_fail_closed_when_disabled():
    runner = IsolatedCodeRunner(docker_client=object())
    runner.set_config(_CfgDisabled())

    result = runner.execute_code("print('hello')")
    assert result["success"] is False
    assert "fail-closed" in (result["error"] or "").lower()


def test_isolated_runner_fail_closed_when_docker_unavailable():
    runner = IsolatedCodeRunner(docker_client=None)
    runner.set_config(_CfgEnabled())
    runner.docker_client = None

    result = runner.execute_code("print('hello')")
    assert result["success"] is False
    assert "fail-closed" in (result["error"] or "").lower()
