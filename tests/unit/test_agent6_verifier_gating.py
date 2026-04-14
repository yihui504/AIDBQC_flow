import os

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.state import DefectReport, WorkflowState
from src.agents.agent6_verifier import DefectVerifierAgent, GitHubIssue
import src.agents.agent6_verifier as agent6_verifier_mod


def test_state_verifier_fields_defaults():
    defect = DefectReport(
        case_id="bug-001",
        bug_type="Type-1 (L1 Crash/Error)",
        evidence_level="L1",
        root_cause_analysis="Crash",
    )
    assert defect.verifier_verdict == "pending"
    assert defect.false_positive is False
    assert defect.reproduced_bug is False

    state = WorkflowState(run_id="run-001", target_db_input="Milvus")
    assert state.verified_defects == []


def test_agent6_only_writes_issue_when_reproduced(tmp_path, monkeypatch):
    state = WorkflowState(run_id="run-001", target_db_input="Milvus")
    state.defect_reports = [
        DefectReport(
            case_id="bug-001",
            bug_type="Type-1 (L1 Crash/Error)",
            evidence_level="L1",
            root_cause_analysis="Crash",
        )
    ]

    agent = DefectVerifierAgent()
    agent.runs_root = str(tmp_path)

    monkeypatch.setattr(agent, "_deduplicate", lambda defects: defects)

    def fake_generate(defect, env_context):
        issue = GitHubIssue(
            title="[Bug]: crash",
            body_markdown="```python\nprint('hello')\n```",
        )
        return issue, 10

    monkeypatch.setattr(agent, "_generate_issue_for_defect", fake_generate)
    monkeypatch.setattr(agent, "_verify_mre", lambda code, case_id, bug_type: ("SUCCESS", "ok"))

    out = agent.execute(state)

    assert len(out.verified_defects) == 1
    defect = out.defect_reports[0]
    assert defect.reproduced_bug is True
    assert defect.verifier_verdict == "reproduced_bug"
    assert defect.false_positive is False
    assert defect.issue_url is not None
    assert os.path.exists(defect.issue_url)


def test_agent6_skips_issue_when_not_reproduced(tmp_path, monkeypatch):
    state = WorkflowState(run_id="run-001", target_db_input="Milvus")
    state.defect_reports = [
        DefectReport(
            case_id="bug-001",
            bug_type="Type-1 (L1 Crash/Error)",
            evidence_level="L1",
            root_cause_analysis="Crash",
        )
    ]

    agent = DefectVerifierAgent()
    agent.runs_root = str(tmp_path)

    monkeypatch.setattr(agent, "_deduplicate", lambda defects: defects)

    def fake_generate(defect, env_context):
        issue = GitHubIssue(
            title="[Bug]: crash",
            body_markdown="```python\nprint('hello')\n```",
        )
        return issue, 10

    monkeypatch.setattr(agent, "_generate_issue_for_defect", fake_generate)
    monkeypatch.setattr(
        agent,
        "_verify_mre",
        lambda code, case_id, bug_type: ("FAILED", "Reproduction Failed: Code executed without error (did not reproduce the bug)."),
    )

    out = agent.execute(state)

    assert out.verified_defects == []
    defect = out.defect_reports[0]
    assert defect.reproduced_bug is False
    assert defect.verifier_verdict == "false_positive"
    assert defect.false_positive is True
    assert defect.issue_url is None


def test_agent6_expected_rejection_verdict_for_illegal_success(tmp_path, monkeypatch):
    state = WorkflowState(run_id="run-001", target_db_input="Milvus")
    state.defect_reports = [
        DefectReport(
            case_id="bug-001",
            bug_type="Type-1 (Illegal Success)",
            evidence_level="L1",
            root_cause_analysis="Bypass",
        )
    ]

    agent = DefectVerifierAgent()
    agent.runs_root = str(tmp_path)

    monkeypatch.setattr(agent, "_deduplicate", lambda defects: defects)

    def fake_generate(defect, env_context):
        issue = GitHubIssue(
            title="[Bug]: bypass",
            body_markdown="```python\nprint('hello')\n```",
        )
        return issue, 10

    monkeypatch.setattr(agent, "_generate_issue_for_defect", fake_generate)
    monkeypatch.setattr(
        agent,
        "_verify_mre",
        lambda code, case_id, bug_type: ("EXPECTED_REJECTION", "Request was rejected as expected."),
    )

    out = agent.execute(state)

    assert out.verified_defects == []
    defect = out.defect_reports[0]
    assert defect.reproduced_bug is False
    assert defect.verifier_verdict == "expected_rejection"
    assert defect.false_positive is True
    assert defect.issue_url is None


def test_generate_issue_for_defect_no_unboundlocal_on_target_doc(monkeypatch):
    """
    Regression test:
    agent6_verifier.DefectVerifierAgent._generate_issue_for_defect() used to raise UnboundLocalError
    because inner _invoke_with_retry() assigned to `target_doc` (closure scope bug).
    """
    agent = DefectVerifierAgent()

    # Avoid any external LLM / callbacks; keep this test fully offline.
    class _DummyCallback:
        total_tokens = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(agent6_verifier_mod, "get_openai_callback", lambda: _DummyCallback())

    class _DummyParser:
        def get_format_instructions(self):
            return "{}"

    class _DummyResp:
        def __init__(self, content: str):
            self.content = content

    class _DummyLLM:
        def invoke(self, _input_data):
            return _DummyResp('{"title":"[Bug]: t","body_markdown":"```python\\nprint(1)\\n```"}')

    class _DummyChain:
        def __init__(self, llm):
            self._llm = llm

        def invoke(self, input_data):
            return self._llm.invoke(input_data)

    class _DummyPrompt:
        def partial(self, **_kwargs):
            return self

        def __or__(self, llm):
            return _DummyChain(llm)

    agent.parser = _DummyParser()
    agent.prompt = _DummyPrompt()
    agent.llm = _DummyLLM()
    agent._current_db_fragments = agent._get_db_template_fragments("Milvus")
    agent._docs_map = {}
    agent._target_doc_by_case = {}

    defect = DefectReport(
        case_id="bug-001",
        bug_type="Type-1 (L1 Crash/Error)",
        evidence_level="L1",
        root_cause_analysis="Crash",
    )
    issue, tokens = agent._generate_issue_for_defect(defect, env_context={}, target_doc=None)

    assert issue is not None
    assert isinstance(issue, GitHubIssue)
    assert issue.title.startswith("[Bug]:")
    assert tokens == 0
