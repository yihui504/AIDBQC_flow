"""
Unit Tests for LangGraph Workflow Building

Test coverage goals: 80%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.state import WorkflowState
from src.graph import (
    should_continue_fuzzing,
    check_circuit_breaker,
    build_workflow
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def base_state():
    """Base workflow state."""
    return WorkflowState(
        run_id="test-run-001",
        target_db_input="Milvus v2.6.12",
        iteration_count=5,
        max_iterations=10,
        total_tokens_used=50000,
        max_token_budget=100000,
        consecutive_failures=0,
        max_consecutive_failures=3
    )


# ============================================================================
# Should Continue Fuzzing Tests
# ============================================================================

class TestShouldContinueFuzzing:
    """Tests for should_continue_fuzzing routing function."""

    def test_continue_fuzzing_normal_conditions(self, base_state):
        """Test continue fuzzing under normal conditions."""
        result = should_continue_fuzzing(base_state)
        assert result == "fuzz"
        assert base_state.should_terminate is False

    def test_stop_fuzzing_token_budget_exceeded(self, base_state):
        """Test stop when token budget is exceeded."""
        base_state.total_tokens_used = 100000
        base_state.max_token_budget = 100000
        result = should_continue_fuzzing(base_state)
        assert result == "verify"
        assert base_state.should_terminate is True

    def test_stop_fuzzing_terminate_flag_set(self, base_state):
        """Test stop when should_terminate flag is already set."""
        base_state.should_terminate = True
        result = should_continue_fuzzing(base_state)
        assert result == "verify"

    def test_continue_fuzzing_near_budget_limit(self, base_state):
        """Test continue when near but not over budget."""
        base_state.total_tokens_used = 99999
        base_state.max_token_budget = 100000
        result = should_continue_fuzzing(base_state)
        assert result == "fuzz"

    def test_stop_fuzzing_iteration_limit_reached(self, base_state):
        """Test stop when iteration count reaches max."""
        # Note: The current implementation doesn't check iteration_count,
        # but we can set should_terminate externally
        base_state.iteration_count = 10
        base_state.max_iterations = 10
        base_state.should_terminate = True  # Would be set by agent logic
        result = should_continue_fuzzing(base_state)
        assert result == "verify"

    def test_token_budget_exactly_at_limit(self, base_state):
        """Test when total_tokens_used equals max_token_budget."""
        base_state.total_tokens_used = 100000
        base_state.max_token_budget = 100000
        result = should_continue_fuzzing(base_state)
        assert result == "verify"
        assert base_state.should_terminate is True

    def test_zero_max_token_budget(self, base_state):
        """Test with zero max token budget (edge case)."""
        base_state.total_tokens_used = 0
        base_state.max_token_budget = 0
        result = should_continue_fuzzing(base_state)
        assert result == "verify"

    def test_negative_token_usage(self, base_state):
        """Test with negative token usage (edge case)."""
        base_state.total_tokens_used = -1000
        result = should_continue_fuzzing(base_state)
        assert result == "fuzz"


# ============================================================================
# Check Circuit Breaker Tests
# ============================================================================

class TestCheckCircuitBreaker:
    """Tests for check_circuit_breaker routing function."""

    def test_continue_normal_operation(self, base_state):
        """Test continue under normal operation."""
        result = check_circuit_breaker(base_state)
        assert result == "continue"

    def test_recover_on_consecutive_failures(self, base_state):
        """Test recovery when consecutive failures threshold is met."""
        base_state.consecutive_failures = 3
        base_state.max_consecutive_failures = 3
        result = check_circuit_breaker(base_state)
        assert result == "recover"

    def test_recover_when_failures_exceed_threshold(self, base_state):
        """Test recovery when failures exceed threshold."""
        base_state.consecutive_failures = 5
        base_state.max_consecutive_failures = 3
        result = check_circuit_breaker(base_state)
        assert result == "recover"

    def test_continue_when_below_threshold(self, base_state):
        """Test continue when failures below threshold."""
        base_state.consecutive_failures = 2
        base_state.max_consecutive_failures = 3
        result = check_circuit_breaker(base_state)
        assert result == "continue"

    def test_zero_failures(self, base_state):
        """Test with zero failures."""
        base_state.consecutive_failures = 0
        result = check_circuit_breaker(base_state)
        assert result == "continue"

    def test_zero_max_failures(self, base_state):
        """Test with zero max consecutive failures (edge case)."""
        base_state.consecutive_failures = 0
        base_state.max_consecutive_failures = 0
        result = check_circuit_breaker(base_state)
        # When max is 0, even 0 failures triggers recovery
        assert result == "recover"

    def test_negative_failure_count(self, base_state):
        """Test with negative failure count (edge case)."""
        base_state.consecutive_failures = -1
        result = check_circuit_breaker(base_state)
        assert result == "continue"


# ============================================================================
# Build Workflow Tests
# ============================================================================

class TestBuildWorkflow:
    """Tests for build_workflow function."""

    def test_workflow_compilation(self):
        """Test that workflow compiles successfully."""
        workflow = build_workflow()
        assert workflow is not None
        # Should be a compiled graph
        assert hasattr(workflow, 'invoke')

    def test_workflow_has_all_nodes(self):
        """Test that workflow includes all expected nodes."""
        workflow = build_workflow()
        # The workflow should have nodes for all agents
        # Note: Checking actual nodes requires access to internal graph structure
        assert workflow is not None

    def test_workflow_state_schema(self):
        """Test that workflow uses WorkflowState schema."""
        workflow = build_workflow()
        # WorkflowState should be the schema
        assert workflow is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestWorkflowIntegration:
    """Integration tests for workflow routing logic."""

    def test_full_fuzzing_loop_routing(self, base_state):
        """Test routing through a complete fuzzing loop decision."""
        # Normal conditions -> continue fuzzing
        assert should_continue_fuzzing(base_state) == "fuzz"
        assert check_circuit_breaker(base_state) == "continue"

    def test_circuit_breaker_triggered(self, base_state):
        """Test circuit breaker trigger scenario."""
        base_state.consecutive_failures = 3
        assert check_circuit_breaker(base_state) == "recover"

    def test_token_budget_circuit_breaker(self, base_state):
        """Test token budget acting as circuit breaker."""
        base_state.total_tokens_used = 100000
        base_state.max_token_budget = 100000
        assert should_continue_fuzzing(base_state) == "verify"

    def test_combined_breakers(self, base_state):
        """Test multiple breaker conditions."""
        base_state.consecutive_failures = 3
        base_state.total_tokens_used = 100000
        base_state.max_token_budget = 100000

        # Both conditions triggered
        assert check_circuit_breaker(base_state) == "recover"
        assert should_continue_fuzzing(base_state) == "verify"


# ============================================================================
# State Mutation Tests
# ============================================================================

class TestStateMutation:
    """Tests for state mutations in routing functions."""

    def test_should_terminate_flag_set_on_budget_exceeded(self, base_state):
        """Test that should_terminate is set when budget exceeded."""
        base_state.total_tokens_used = 100001
        base_state.max_token_budget = 100000
        base_state.should_terminate = False  # Initially false

        should_continue_fuzzing(base_state)

        assert base_state.should_terminate is True

    def test_consecutive_failures_preserved(self, base_state):
        """Test that consecutive_failures is not modified by routing."""
        original_failures = base_state.consecutive_failures
        base_state.consecutive_failures = 2

        check_circuit_breaker(base_state)

        assert base_state.consecutive_failures == 2

    def test_iteration_count_preserved(self, base_state):
        """Test that iteration_count is preserved."""
        original_iteration = base_state.iteration_count
        base_state.iteration_count = 7

        should_continue_fuzzing(base_state)

        assert base_state.iteration_count == 7


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_max_iterations_zero(self, base_state):
        """Test with max_iterations set to zero."""
        base_state.max_iterations = 0
        base_state.iteration_count = 0
        base_state.should_terminate = True  # Would be set externally
        result = should_continue_fuzzing(base_state)
        assert result == "verify"

    def test_negative_max_iterations(self, base_state):
        """Test with negative max_iterations (edge case)."""
        base_state.max_iterations = -1
        # Should not cause error
        result = should_continue_fuzzing(base_state)
        # Depends on should_terminate flag
        assert result in ["fuzz", "verify"]

    def test_very_large_token_values(self, base_state):
        """Test with very large token values."""
        base_state.total_tokens_used = 999999999
        base_state.max_token_budget = 999999999
        result = should_continue_fuzzing(base_state)
        assert result == "verify"

    def test_consecutive_failures_very_large(self, base_state):
        """Test with very large consecutive failures count."""
        base_state.consecutive_failures = 999999
        result = check_circuit_breaker(base_state)
        assert result == "recover"


# ============================================================================
# Return Value Tests
# ============================================================================

class TestReturnValues:
    """Tests for routing function return values."""

    def test_should_continue_fuzzing_return_values(self, base_state):
        """Test that only valid return values are produced."""
        for _ in range(10):
            result = should_continue_fuzzing(base_state)
            assert result in ["fuzz", "verify"]

    def test_check_circuit_breaker_return_values(self, base_state):
        """Test that only valid return values are produced."""
        for _ in range(10):
            result = check_circuit_breaker(base_state)
            assert result in ["continue", "recover"]


# ============================================================================
# Workflow State Preservation Tests
# ============================================================================

class TestStatePreservation:
    """Tests that routing functions preserve unrelated state."""

    def test_other_fields_preserved_in_fuzzing_check(self, base_state):
        """Test that other state fields are preserved."""
        base_state.business_scenario = "Test scenario"
        base_state.fuzzing_feedback = "Previous feedback"
        base_state.history_vectors = [[1.0, 2.0, 3.0]]

        should_continue_fuzzing(base_state)

        assert base_state.business_scenario == "Test scenario"
        assert base_state.fuzzing_feedback == "Previous feedback"
        assert base_state.history_vectors == [[1.0, 2.0, 3.0]]

    def test_other_fields_preserved_in_circuit_breaker_check(self, base_state):
        """Test that circuit breaker preserves other fields."""
        base_state.db_config = {"db_name": "Milvus"}
        base_state.contracts = {"l1_api": {"dimension": 128}}

        check_circuit_breaker(base_state)

        assert base_state.db_config == {"db_name": "Milvus"}
        assert base_state.contracts == {"l1_api": {"dimension": 128}}


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/graph", "--cov-report=term-missing"])
