"""
Unit Tests for WorkflowState and State Models

Test coverage goals: 90%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.state import (
    WorkflowState,
    DatabaseConfig,
    Contract,
    TestCase,
    ExecutionResult,
    OracleValidation,
    DefectReport,
)


# ============================================================================
# DatabaseConfig Tests
# ============================================================================

class TestDatabaseConfig:
    """Tests for DatabaseConfig model."""

    def test_initialization(self):
        """Test DatabaseConfig initialization."""
        config = DatabaseConfig(
            db_name="Milvus",
            version="2.6.12",
            endpoint="localhost:19530",
            credentials={"token": "test"}
        )
        assert config.db_name == "Milvus"
        assert config.version == "2.6.12"
        assert config.endpoint == "localhost:19530"
        assert config.credentials == {"token": "test"}

    def test_defaults(self):
        """Test DatabaseConfig with default values."""
        config = DatabaseConfig(db_name="Qdrant", version="1.0.0")
        assert config.db_name == "Qdrant"
        assert config.version == "1.0.0"
        assert config.endpoint is None
        assert config.credentials is None
        assert config.docs_context == ""

    def test_serialization(self):
        """Test DatabaseConfig can be serialized."""
        config = DatabaseConfig(db_name="Milvus", version="2.6.12")
        data = config.model_dump()
        assert "db_name" in data
        assert data["db_name"] == "Milvus"


# ============================================================================
# Contract Tests
# ============================================================================

class TestContract:
    """Tests for Contract model."""

    def test_initialization(self):
        """Test Contract initialization."""
        contract = Contract(
            l3_application={"scenario": "search"},
            l2_semantic={"metric": "cosine"},
            l1_api={"dimension": 128}
        )
        assert contract.l3_application == {"scenario": "search"}
        assert contract.l2_semantic == {"metric": "cosine"}
        assert contract.l1_api == {"dimension": 128}

    def test_defaults(self):
        """Test Contract with default values."""
        contract = Contract()
        assert contract.l3_application == {}
        assert contract.l2_semantic == {}
        assert contract.l1_api == {}


# ============================================================================
# TestCase Tests
# ============================================================================

class TestTestCase:
    """Tests for TestCase model."""

    def test_full_initialization(self):
        """Test TestCase with all fields."""
        test_case = TestCase(
            case_id="test-001",
            query_vector=[0.1, 0.2, 0.3],
            query_text="test query",
            dimension=3,
            expected_l1_legal=True,
            expected_l2_ready=True,
            semantic_intent="search",
            is_adversarial=False
        )
        assert test_case.case_id == "test-001"
        assert test_case.query_vector == [0.1, 0.2, 0.3]
        assert test_case.dimension == 3

    def test_defaults(self):
        """Test TestCase with default values."""
        test_case = TestCase(
            case_id="test-001",
            dimension=128
        )
        assert test_case.query_vector is None
        assert test_case.query_text is None
        assert test_case.expected_l1_legal is True
        assert test_case.expected_l2_ready is True
        assert test_case.semantic_intent == ""
        assert test_case.is_adversarial is False

    def test_adversarial_flag(self):
        """Test adversarial test case."""
        test_case = TestCase(
            case_id="adv-001",
            dimension=128,
            is_adversarial=True
        )
        assert test_case.is_adversarial is True


# ============================================================================
# ExecutionResult Tests
# ============================================================================

class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_successful_execution(self):
        """Test successful execution result."""
        result = ExecutionResult(
            case_id="test-001",
            success=True,
            l1_passed=True,
            l2_passed=True,
            execution_time_ms=50.5
        )
        assert result.success is True
        assert result.l1_passed is True
        assert result.l2_passed is True
        assert result.execution_time_ms == 50.5
        assert result.error_message is None

    def test_failed_execution(self):
        """Test failed execution result."""
        result = ExecutionResult(
            case_id="test-002",
            success=False,
            l1_passed=False,
            l2_passed=False,
            error_message="Connection timeout"
        )
        assert result.success is False
        assert result.error_message == "Connection timeout"

    def test_with_raw_response(self):
        """Test execution with raw response."""
        result = ExecutionResult(
            case_id="test-003",
            success=True,
            l1_passed=True,
            l2_passed=True,
            raw_response={"hits": [{"id": 1, "score": 0.95}]}
        )
        assert result.raw_response is not None
        assert result.raw_response["hits"][0]["score"] == 0.95

    def test_with_underlying_logs(self):
        """Test execution with underlying logs."""
        result = ExecutionResult(
            case_id="test-004",
            success=True,
            l1_passed=True,
            l2_passed=True,
            underlying_logs="INFO: Processing query...\nDEBUG: Vector search complete"
        )
        assert "Processing query" in result.underlying_logs


# ============================================================================
# OracleValidation Tests
# ============================================================================

class TestOracleValidation:
    """Tests for OracleValidation model."""

    def test_passed_validation(self):
        """Test passed Oracle validation."""
        validation = OracleValidation(
            case_id="test-001",
            passed=True,
            anomalies=[],
            explanation="All checks passed"
        )
        assert validation.passed is True
        assert validation.anomalies == []
        assert validation.explanation == "All checks passed"

    def test_failed_validation_with_anomalies(self):
        """Test failed validation with anomalies."""
        validation = OracleValidation(
            case_id="test-002",
            passed=False,
            anomalies=[
                {"type": "semantic_drift", "severity": "high"},
                {"type": "performance", "severity": "medium"}
            ],
            explanation="Semantic drift detected in results"
        )
        assert validation.passed is False
        assert len(validation.anomalies) == 2
        assert validation.anomalies[0]["type"] == "semantic_drift"


# ============================================================================
# DefectReport Tests
# ============================================================================

class TestDefectReport:
    """Tests for DefectReport model."""

    def test_type_1_defect(self):
        """Test Type-1 defect (crash/exception)."""
        report = DefectReport(
            case_id="bug-001",
            bug_type="TYPE_1",
            evidence_level="L1",
            root_cause_analysis="Null pointer dereference",
            is_verified=True,
            mre_code="vec = None; vec.append(1)"
        )
        assert report.bug_type == "TYPE_1"
        assert report.evidence_level == "L1"
        assert report.is_verified is True

    def test_type_4_defect_with_issue_url(self):
        """Test Type-4 defect with GitHub issue."""
        report = DefectReport(
            case_id="bug-002",
            bug_type="TYPE_4",
            evidence_level="L3",
            root_cause_analysis="Semantic drift in vector similarity",
            is_verified=False,
            issue_url="https://github.com/example/repo/issues/123"
        )
        assert report.bug_type == "TYPE_4"
        assert report.issue_url == "https://github.com/example/repo/issues/123"
        assert report.is_verified is False


# ============================================================================
# WorkflowState Tests
# ============================================================================

class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_initialization(self):
        """Test WorkflowState initialization."""
        state = WorkflowState(
            run_id="run-001",
            target_db_input="Milvus v2.6.12",
            business_scenario="E-commerce product search"
        )
        assert state.run_id == "run-001"
        assert state.target_db_input == "Milvus v2.6.12"
        assert state.business_scenario == "E-commerce product search"
        assert state.iteration_count == 0
        assert state.max_iterations == 10

    def test_default_values(self):
        """Test WorkflowState with default values."""
        state = WorkflowState(
            run_id="run-002",
            target_db_input="Qdrant"
        )
        assert state.business_scenario == ""
        assert state.iteration_count == 0
        assert state.max_iterations == 10
        assert state.should_terminate is False
        assert state.total_tokens_used == 0
        assert state.max_token_budget == 100000
        assert state.consecutive_failures == 0
        assert state.max_consecutive_failures == 3

    def test_with_database_config(self):
        """Test WorkflowState with DatabaseConfig."""
        state = WorkflowState(
            run_id="run-003",
            target_db_input="Milvus"
        )
        state.db_config = DatabaseConfig(
            db_name="Milvus",
            version="2.6.12",
            endpoint="localhost:19530"
        )
        assert state.db_config.db_name == "Milvus"
        assert state.db_config.endpoint == "localhost:19530"

    def test_with_contracts(self):
        """Test WorkflowState with Contract."""
        state = WorkflowState(
            run_id="run-004",
            target_db_input="Milvus"
        )
        state.contracts = Contract(
            l1_api={"dimension": 128},
            l2_semantic={"metric": "L2"}
        )
        assert state.contracts.l1_api["dimension"] == 128
        assert state.contracts.l2_semantic["metric"] == "L2"

    def test_with_test_cases(self):
        """Test WorkflowState with test cases."""
        state = WorkflowState(
            run_id="run-005",
            target_db_input="Milvus"
        )
        state.current_test_cases = [
            TestCase(case_id="test-001", dimension=128, query_vector=[0.1] * 128),
            TestCase(case_id="test-002", dimension=128, query_vector=[0.2] * 128),
        ]
        assert len(state.current_test_cases) == 2
        assert state.current_test_cases[0].case_id == "test-001"

    def test_with_execution_results(self):
        """Test WorkflowState with execution results."""
        state = WorkflowState(
            run_id="run-006",
            target_db_input="Milvus"
        )
        state.execution_results = [
            ExecutionResult(case_id="test-001", success=True, l1_passed=True, l2_passed=True),
            ExecutionResult(case_id="test-002", success=False, l1_passed=False, l2_passed=False, error_message="Error")
        ]
        assert len(state.execution_results) == 2
        assert state.execution_results[0].success is True
        assert state.execution_results[1].success is False

    def test_with_oracle_results(self):
        """Test WorkflowState with oracle results."""
        state = WorkflowState(
            run_id="run-007",
            target_db_input="Milvus"
        )
        state.oracle_results = [
            OracleValidation(case_id="test-001", passed=True, anomalies=[]),
            OracleValidation(case_id="test-002", passed=False, anomalies=[{"type": "drift"}])
        ]
        assert len(state.oracle_results) == 2
        assert state.oracle_results[0].passed is True
        assert state.oracle_results[1].passed is False

    def test_with_defect_reports(self):
        """Test WorkflowState with defect reports."""
        state = WorkflowState(
            run_id="run-008",
            target_db_input="Milvus"
        )
        state.defect_reports = [
            DefectReport(
                case_id="bug-001",
                bug_type="TYPE_1",
                evidence_level="L1",
                root_cause_analysis="Null pointer"
            )
        ]
        assert len(state.defect_reports) == 1
        assert state.defect_reports[0].bug_type == "TYPE_1"

    def test_token_tracking(self):
        """Test token usage tracking."""
        state = WorkflowState(
            run_id="run-009",
            target_db_input="Milvus",
            total_tokens_used=50000
        )
        assert state.total_tokens_used == 50000
        assert state.total_tokens_used < state.max_token_budget

    def test_circuit_breaker_state(self):
        """Test circuit breaker state tracking."""
        state = WorkflowState(
            run_id="run-010",
            target_db_input="Milvus",
            consecutive_failures=2,
            max_consecutive_failures=3
        )
        assert state.consecutive_failures == 2
        assert state.consecutive_failures < state.max_consecutive_failures

    def test_termination_flag(self):
        """Test termination flag."""
        state = WorkflowState(
            run_id="run-011",
            target_db_input="Milvus",
            should_terminate=True
        )
        assert state.should_terminate is True

    def test_history_vectors(self):
        """Test history vectors for coverage monitoring."""
        state = WorkflowState(
            run_id="run-012",
            target_db_input="Milvus"
        )
        state.history_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        assert len(state.history_vectors) == 3

    def test_fuzzing_feedback(self):
        """Test fuzzing feedback."""
        state = WorkflowState(
            run_id="run-013",
            target_db_input="Milvus"
        )
        state.fuzzing_feedback = "Try more edge cases with sparse vectors"
        assert "sparse vectors" in state.fuzzing_feedback

    def test_external_knowledge(self):
        """Test external knowledge from web search."""
        state = WorkflowState(
            run_id="run-014",
            target_db_input="Milvus"
        )
        state.external_knowledge = "Milvus v2.6 has improved HNSW indexing"
        assert "HNSW" in state.external_knowledge


# ============================================================================
# Serialization Tests
# ============================================================================

class TestSerialization:
    """Tests for model serialization."""

    def test_workflow_state_serialization(self):
        """Test WorkflowState can be serialized."""
        state = WorkflowState(
            run_id="run-001",
            target_db_input="Milvus"
        )
        data = state.model_dump()
        assert "run_id" in data
        assert data["run_id"] == "run-001"

    def test_json_serialization(self):
        """Test JSON serialization of state."""
        state = WorkflowState(
            run_id="run-001",
            target_db_input="Milvus",
            current_test_cases=[
                TestCase(case_id="test-001", dimension=128)
            ]
        )
        import json
        json_str = json.dumps(
            {k: v for k, v in state.model_dump().items() if k != "current_test_cases"},
            default=str
        )
        assert "run_id" in json_str


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidation:
    """Tests for Pydantic validation."""

    def test_required_fields(self):
        """Test that required fields are validated."""
        # run_id and target_db_input are required
        with pytest.raises(Exception):
            WorkflowState()  # Missing required fields

    def test_invalid_types(self):
        """Test type validation."""
        # iteration_count should be int
        with pytest.raises(Exception):
            WorkflowState(
                run_id="run-001",
                target_db_input="Milvus",
                iteration_count="not_an_int"
            )


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/state", "--cov-report=term-missing"])
