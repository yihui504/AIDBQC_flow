import subprocess

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.agents.agent6_verifier import DefectVerifierAgent


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_verify_mre_illegal_success_exit0_is_success(monkeypatch):
    agent = DefectVerifierAgent()

    def fake_run(*args, **kwargs):
        return _FakeCompletedProcess(returncode=0, stdout="MRE_EXECUTION_SUCCESS\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    status, _log = agent._verify_mre("print('ok')", "case-001", "Type-1 (Illegal Success)")
    assert status == "SUCCESS"


def test_verify_mre_illegal_success_rejection_is_expected_rejection(monkeypatch):
    agent = DefectVerifierAgent()

    def fake_run(*args, **kwargs):
        return _FakeCompletedProcess(
            returncode=1,
            stdout="",
            stderr="MRE_EXECUTION_FAILED: MilvusException: invalid dimension\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status, _log = agent._verify_mre("raise Exception('x')", "case-002", "Type-1 (Illegal Success)")
    assert status == "EXPECTED_REJECTION"


def test_verify_mre_non_illegal_success_rejection_is_success(monkeypatch):
    agent = DefectVerifierAgent()

    def fake_run(*args, **kwargs):
        return _FakeCompletedProcess(
            returncode=1,
            stdout="",
            stderr="MRE_EXECUTION_FAILED: MilvusException: crash\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status, _log = agent._verify_mre("raise Exception('x')", "case-003", "Type-1 (L1 Crash/Error)")
    assert status == "SUCCESS"

