import pytest

from src.policy.engine import PolicyEngine
from src.policy.focus import FocusAdvisor
from src.policy.permission import PermissionEvaluator
from src.policy.safety import SafetyGuard
from src.models.state import FocusMode, ToolMeta


class TestFocusAdvisor:
    def test_register_and_is_out_of_focus(self):
        advisor = FocusAdvisor()
        advisor.register("db_search", ToolMeta(focus_modes=[FocusMode.EXECUTION], permission="read"))
        assert advisor.is_out_of_focus("db_search", FocusMode.UNDERSTANDING) is True
        assert advisor.is_out_of_focus("db_search", FocusMode.EXECUTION) is False

    def test_recommend_tools(self):
        advisor = FocusAdvisor()
        advisor.register("db_search", ToolMeta(focus_modes=[FocusMode.EXECUTION], permission="read"))
        advisor.register("db_schema", ToolMeta(focus_modes=[FocusMode.UNDERSTANDING], permission="read"))
        recommended = advisor.recommend_tools(FocusMode.EXECUTION)
        assert "db_search" in recommended
        assert "db_schema" not in recommended

    def test_unregistered_tool_not_out_of_focus(self):
        advisor = FocusAdvisor()
        assert advisor.is_out_of_focus("nonexistent_tool", FocusMode.UNDERSTANDING) is False


class TestPermissionEvaluator:
    def test_cautious_admin_denied(self):
        evaluator = PermissionEvaluator("cautious")
        result = evaluator.evaluate("db_drop_collection")
        assert result["allowed"] is False

    def test_cautious_write_denied(self):
        evaluator = PermissionEvaluator("cautious")
        result = evaluator.evaluate("db_delete_data")
        assert result["allowed"] is False

    def test_cautious_execute_allowed(self):
        evaluator = PermissionEvaluator("cautious")
        result = evaluator.evaluate("code_run_mre")
        assert result["allowed"] is True

    def test_aggressive_all_allowed(self):
        evaluator = PermissionEvaluator("aggressive")
        assert evaluator.evaluate("db_drop_collection")["allowed"] is True
        assert evaluator.evaluate("db_delete_data")["allowed"] is True
        assert evaluator.evaluate("code_run_mre")["allowed"] is True

    def test_unknown_tool_allowed(self):
        evaluator = PermissionEvaluator("cautious")
        result = evaluator.evaluate("some_safe_tool")
        assert result["allowed"] is True


class TestSafetyGuard:
    def test_cautious_delete_all_blocked(self):
        guard = SafetyGuard("cautious")
        result = guard.check_execution("db_tool", {"query": "DELETE ALL FROM users"})
        assert result["allowed"] is False
        assert "DELETE ALL" in result["reason"]

    def test_cautious_truncate_blocked(self):
        guard = SafetyGuard("cautious")
        result = guard.check_execution("db_tool", {"query": "TRUNCATE TABLE users"})
        assert result["allowed"] is False
        assert "TRUNCATE" in result["reason"]

    def test_aggressive_all_allowed(self):
        guard = SafetyGuard("aggressive")
        result = guard.check_execution("db_tool", {"query": "DELETE ALL FROM users"})
        assert result["allowed"] is True

    def test_normal_args_allowed(self):
        guard = SafetyGuard("cautious")
        result = guard.check_execution("db_tool", {"query": "SELECT * FROM users"})
        assert result["allowed"] is True


class TestPolicyEngine:
    def test_out_of_focus_blocks_execution(self):
        engine = PolicyEngine(safety_level="cautious")
        engine.focus_advisor.register("db_search", ToolMeta(focus_modes=[FocusMode.EXECUTION], permission="read"))
        result = engine.check_tool_execution("db_search", FocusMode.UNDERSTANDING, {})
        assert result["allowed"] is False
        assert result["out_of_focus"] is True

    def test_multiple_reasons_combined(self):
        engine = PolicyEngine(safety_level="cautious")
        engine.focus_advisor.register("db_drop_collection", ToolMeta(focus_modes=[FocusMode.EXECUTION], permission="admin"))
        result = engine.check_tool_execution("db_drop_collection", FocusMode.UNDERSTANDING, {"query": "DELETE ALL"})
        assert result["allowed"] is False
        assert result["out_of_focus"] is True
        assert len(result["reasons"]) >= 2

    def test_all_pass_allowed(self):
        engine = PolicyEngine(safety_level="cautious")
        engine.focus_advisor.register("db_search", ToolMeta(focus_modes=[FocusMode.EXECUTION], permission="read"))
        result = engine.check_tool_execution("db_search", FocusMode.EXECUTION, {"query": "SELECT * FROM users"})
        assert result["allowed"] is True
        assert result["out_of_focus"] is False
        assert result["reasons"] == []
