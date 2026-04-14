import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.agents.agent6_verifier import DefectVerifierAgent


def _runner_result(exit_code: int, stdout: str = "", stderr: str = ""):
    error = None
    if exit_code != 0:
        error = stderr or f"Exit code: {exit_code}"
    return {
        "success": exit_code == 0,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timeout": False,
        "error": error,
    }


def test_verify_mre_illegal_success_exit0_is_success(monkeypatch):
    agent = DefectVerifierAgent()

    monkeypatch.setattr(
        agent.isolated_runner,
        "execute_code",
        lambda _code: _runner_result(0, stdout="MRE_EXECUTION_SUCCESS\n"),
    )

    status, _log = agent._verify_mre("print('ok')", "case-001", "Type-1 (Illegal Success)")
    assert status == "SUCCESS"


def test_verify_mre_illegal_success_rejection_is_expected_rejection(monkeypatch):
    agent = DefectVerifierAgent()

    monkeypatch.setattr(
        agent.isolated_runner,
        "execute_code",
        lambda _code: _runner_result(
            1,
            stderr="MRE_EXECUTION_FAILED: MilvusException: invalid dimension\n",
        ),
    )

    status, _log = agent._verify_mre("raise Exception('x')", "case-002", "Type-1 (Illegal Success)")
    assert status == "EXPECTED_REJECTION"


def test_verify_mre_non_illegal_success_rejection_is_success(monkeypatch):
    agent = DefectVerifierAgent()

    monkeypatch.setattr(
        agent.isolated_runner,
        "execute_code",
        lambda _code: _runner_result(
            1,
            stderr="MRE_EXECUTION_FAILED: MilvusException: crash\n",
        ),
    )

    status, _log = agent._verify_mre("raise Exception('x')", "case-003", "Type-1 (L1 Crash/Error)")
    assert status == "SUCCESS"


def test_verify_mre_fail_closed_when_isolated_execution_unavailable(monkeypatch):
    agent = DefectVerifierAgent()
    monkeypatch.setattr(
        agent.isolated_runner,
        "execute_code",
        lambda _code: _runner_result(
            -1,
            stderr="Docker client unavailable; host fallback is forbidden (fail-closed).",
        ),
    )

    status, log = agent._verify_mre("print('x')", "case-004", "Type-1 (L1 Crash/Error)")
    assert status == "FAILED"
    assert "fail-closed" in log.lower()

