import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pytest
from src.models.state import UnifiedState, FocusMode, FuzzingFeedback, FocusTransition


class TestUnifiedStateCreation:
    def test_default_state(self):
        state = UnifiedState()
        assert state.current_focus == FocusMode.UNDERSTANDING
        assert state.round_number == 1
        assert state.max_rounds == 4
        assert state.token_usage == 0
        assert state.max_token_budget == 800000
        assert state.consecutive_failures == 0
        assert state.max_consecutive_failures == 5
        assert state.should_terminate is False
        assert state.coverage_score == 0.0
        assert state.defect_counter == 0
        assert state.execution_log == []
        assert state.tool_call_history == []
        assert state.focus_history == []
        assert state.target_db == "milvus"
        assert state.target_version == "2.6.12"


class TestSwitchFocus:
    def test_switch_records_history(self):
        state = UnifiedState()
        state.switch_focus(FocusMode.GENERATION, "ready to generate")
        assert state.current_focus == FocusMode.GENERATION
        assert len(state.focus_history) == 1
        assert state.focus_history[0].from_focus == FocusMode.UNDERSTANDING
        assert state.focus_history[0].to_focus == FocusMode.GENERATION
        assert state.focus_history[0].reason == "ready to generate"

    def test_same_focus_no_history(self):
        state = UnifiedState(current_focus=FocusMode.EXECUTION)
        history_len_before = len(state.focus_history)
        state.switch_focus(FocusMode.EXECUTION)
        assert state.current_focus == FocusMode.EXECUTION
        assert len(state.focus_history) == history_len_before


class TestAdvanceRound:
    def test_advance_round(self):
        state = UnifiedState(round_number=2)
        state.advance_round()
        assert state.round_number == 3


class TestShouldStop:
    def test_should_terminate(self):
        state = UnifiedState(should_terminate=True)
        assert state.should_stop() is True

    def test_max_rounds_reached(self):
        state = UnifiedState(round_number=4, max_rounds=4)
        assert state.should_stop() is True

    def test_budget_exhausted(self):
        state = UnifiedState(token_usage=800000, max_token_budget=800000)
        assert state.should_stop() is True

    def test_consecutive_failures_limit(self):
        state = UnifiedState(consecutive_failures=5, max_consecutive_failures=5)
        assert state.should_stop() is True

    def test_normal_returns_false(self):
        state = UnifiedState(round_number=1, max_rounds=4, token_usage=0, max_token_budget=800000, consecutive_failures=0, max_consecutive_failures=5)
        assert state.should_stop() is False


class TestAddExecutionLog:
    def test_append_log(self):
        state = UnifiedState()
        state.add_execution_log("step1")
        assert len(state.execution_log) == 1
        assert "step1" in state.execution_log[0]

    def test_truncate_log(self):
        state = UnifiedState()
        for i in range(502):
            state.add_execution_log(f"entry_{i}")
        assert len(state.execution_log) == 500


class TestAddToolCall:
    def test_append_tool_call(self):
        state = UnifiedState()
        state.add_tool_call("search", {"q": "test"}, "found 3 results")
        assert len(state.tool_call_history) == 1
        assert state.tool_call_history[0]["tool"] == "search"

    def test_truncate_tool_call(self):
        state = UnifiedState()
        for i in range(202):
            state.add_tool_call("tool", {"i": i}, "ok")
        assert len(state.tool_call_history) == 200


class TestDefectCounter:
    def test_increment(self):
        state = UnifiedState(defect_counter=3)
        state.defect_counter += 1
        assert state.defect_counter == 4


class TestComputedFields:
    def test_current_focus(self):
        state = UnifiedState(current_focus=FocusMode.VERIFICATION)
        assert state.current_focus == FocusMode.VERIFICATION

    def test_round_number(self):
        state = UnifiedState(round_number=7)
        assert state.round_number == 7


class TestFromLegacy:
    def test_from_legacy_core_dict(self):
        core = {
            "run_id": "legacy-001",
            "target_db": "milvus",
            "scenario": "search",
            "coverage_score": 0.5,
            "token_usage": 1000,
            "max_token_budget": 800000,
            "consecutive_failures": 2,
            "max_consecutive_failures": 5,
            "should_terminate": False,
            "current_stage": "generation",
            "current_round": 3,
        }
        state = UnifiedState.from_legacy(core)
        assert state.run_id == "legacy-001"
        assert state.current_focus == FocusMode.GENERATION
        assert state.round_number == 3
        assert state.coverage_score == 0.5

    def test_from_legacy_with_context(self):
        core = {"run_id": "legacy-002"}
        context = {
            "execution_log": ["log1"],
            "tool_call_history": [{"tool": "t1"}],
            "source_analysis": "analyzed",
        }
        state = UnifiedState.from_legacy(core, context)
        assert state.execution_log == ["log1"]
        assert state.tool_call_history == [{"tool": "t1"}]
        assert state.source_analysis == "analyzed"

    def test_from_legacy_invalid_stage(self):
        core = {"current_stage": "invalid_mode"}
        state = UnifiedState.from_legacy(core)
        assert state.current_focus == FocusMode.UNDERSTANDING


class TestBudgetAndRounds:
    def test_is_budget_exhausted(self):
        state = UnifiedState(token_usage=900000, max_token_budget=800000)
        assert state.is_budget_exhausted() is True

    def test_is_budget_not_exhausted(self):
        state = UnifiedState(token_usage=100, max_token_budget=800000)
        assert state.is_budget_exhausted() is False

    def test_is_max_rounds_reached(self):
        state = UnifiedState(round_number=4, max_rounds=4)
        assert state.is_max_rounds_reached() is True

    def test_is_max_rounds_not_reached(self):
        state = UnifiedState(round_number=2, max_rounds=4)
        assert state.is_max_rounds_reached() is False
