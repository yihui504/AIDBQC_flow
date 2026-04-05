"""
Unit Tests for Context Reset Manager

Test coverage goals: 90%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import asyncio
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.context.reset_manager import (
    ResetManager,
    ResetStrategy,
    ResetTrigger,
    ResetConfig,
    ResetMetrics,
)
from src.context.handoff import (
    HandoffManager,
    HandoffArtifact,
    HandoffPriority,
    HandoffConfig,
)
from src.state import WorkflowState, DatabaseConfig, Contract, DefectReport


# ============================================================================
# ResetManager Tests
# ============================================================================

class TestResetConfig:
    """Tests for ResetConfig configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ResetConfig()
        assert config.reset_interval == 5
        assert config.token_threshold == 60000
        assert config.token_budget_ratio == 0.6
        assert config.keep_defect_reports is True
        assert config.keep_contracts is True
        assert config.keep_db_config is True
        assert config.keep_history_sample == 20

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ResetConfig(
            reset_interval=10,
            token_threshold=80000,
            keep_history_sample=50
        )
        assert config.reset_interval == 10
        assert config.token_threshold == 80000
        assert config.keep_history_sample == 50


class TestResetManager:
    """Tests for ResetManager functionality."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = ResetManager()
        assert manager.reset_count == 0
        assert manager.last_reset_iteration == 0
        assert len(manager.reset_history) == 0

    def test_should_reset_by_iteration_count(self):
        """Test reset triggered by iteration count."""
        manager = ResetManager(ResetConfig(reset_interval=5))
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        should_reset, trigger = manager.should_reset(state)
        assert should_reset is True
        assert trigger == ResetTrigger.ITERATION_COUNT

    def test_should_not_reset_below_threshold(self):
        """Test no reset when below iteration threshold."""
        manager = ResetManager(ResetConfig(reset_interval=5))
        state = WorkflowState(
            run_id="test-run",
            iteration_count=3,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        should_reset, trigger = manager.should_reset(state)
        assert should_reset is False

    def test_should_reset_by_token_threshold(self):
        """Test reset triggered by token usage."""
        manager = ResetManager(ResetConfig(token_threshold=50000))
        state = WorkflowState(
            run_id="test-run",
            iteration_count=3,
            max_iterations=10,
            target_db_input="Milvus v2.6.12",
            total_tokens_used=60000
        )

        should_reset, trigger = manager.should_reset(state)
        assert should_reset is True
        assert trigger == ResetTrigger.TOKEN_THRESHOLD

    def test_min_iterations_between_resets(self):
        """Test minimum iterations between resets."""
        manager = ResetManager(
            ResetConfig(
                reset_interval=3,
                min_iterations_between_resets=2
            )
        )

        # First reset at iteration 3
        state = WorkflowState(
            run_id="test-run",
            iteration_count=3,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )
        should_reset, _ = manager.should_reset(state)
        assert should_reset is True

        # Immediately after, should not reset
        should_reset, _ = manager.should_reset(state)
        assert should_reset is False

    def test_context_reset_preserves_defect_reports(self):
        """Test that defect reports are preserved across reset."""
        manager = ResetManager(ResetConfig(keep_defect_reports=True))
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        # Add defect reports
        state.defect_reports = [
            DefectReport(
                case_id="test-001",
                bug_type="Type-1",
                evidence_level="L1",
                root_cause_analysis="Test analysis"
            )
        ]

        # Perform reset
        metrics = asyncio.run(manager.reset(state, ResetTrigger.ITERATION_COUNT))

        # Verify defect reports preserved
        assert len(state.defect_reports) == 1
        assert state.defect_reports[0].case_id == "test-001"

    def test_context_reset_clears_runtime_data(self):
        """Test that runtime data is cleared on reset."""
        manager = ResetManager()
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12",
            total_tokens_used=50000,
            consecutive_failures=2
        )

        # Add runtime data
        state.current_test_cases = []
        state.execution_results = []
        state.oracle_results = []
        state.history_vectors = [[1.0] * 128]

        # Perform reset
        asyncio.run(manager.reset(state, ResetTrigger.ITERATION_COUNT))

        # Verify runtime data cleared
        assert len(state.current_test_cases) == 0
        assert len(state.execution_results) == 0
        assert len(state.oracle_results) == 0
        assert len(state.history_vectors) <= 20  # May keep sample
        assert state.total_tokens_used == 0
        assert state.consecutive_failures == 0

    def test_reset_metrics(self):
        """Test that reset metrics are recorded correctly."""
        manager = ResetManager()
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12",
            total_tokens_used=50000
        )

        metrics = asyncio.run(manager.reset(state, ResetTrigger.ITERATION_COUNT))

        assert metrics.success is True
        assert metrics.trigger == ResetTrigger.ITERATION_COUNT
        assert metrics.iteration_count == 5
        assert metrics.tokens_before_reset == 50000
        assert metrics.tokens_saved == 50000  # All tokens saved on reset

    def test_reset_callback(self):
        """Test reset callback functionality."""
        manager = ResetManager()
        callback_called = []

        def callback(state, metrics):
            callback_called.append((state, metrics))

        manager.register_callback(callback)

        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        asyncio.run(manager.reset(state, ResetTrigger.ITERATION_COUNT))

        assert len(callback_called) == 1
        assert callback_called[0][1].success is True

    def test_get_reset_summary(self):
        """Test reset summary generation."""
        manager = ResetManager()
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        asyncio.run(manager.reset(state, ResetTrigger.ITERATION_COUNT))
        asyncio.run(manager.reset(state, ResetTrigger.TOKEN_THRESHOLD))

        summary = manager.get_reset_summary()
        assert summary["total_resets"] == 2
        assert summary["successful_resets"] == 2
        assert summary["success_rate"] == 1.0


# ============================================================================
# HandoffManager Tests
# ============================================================================

class TestHandoffArtifact:
    """Tests for HandoffArtifact."""

    def test_artifact_creation(self):
        """Test creating a handoff artifact."""
        artifact = HandoffArtifact(
            key="test_key",
            value="test_value",
            priority=HandoffPriority.HIGH,
            description="Test artifact"
        )

        assert artifact.key == "test_key"
        assert artifact.value == "test_value"
        assert artifact.priority == HandoffPriority.HIGH
        assert artifact.description == "Test artifact"

    def test_artifact_serialization(self):
        """Test artifact to_dict conversion."""
        artifact = HandoffArtifact(
            key="test_key",
            value={"nested": "data"},
            priority=HandoffPriority.CRITICAL,
            source_agent="agent1"
        )

        data = artifact.to_dict()
        assert data["key"] == "test_key"
        assert data["value"]["nested"] == "data"
        assert data["priority"] == "critical"
        assert data["source_agent"] == "agent1"

    def test_artifact_deserialization(self):
        """Test artifact from_dict creation."""
        data = {
            "key": "test_key",
            "value": [1, 2, 3],
            "priority": "high",
            "description": "Test",
            "source_agent": "agent2",
            "timestamp": datetime.now().isoformat(),
            "metadata": {}
        }

        artifact = HandoffArtifact.from_dict(data)
        assert artifact.key == "test_key"
        assert artifact.value == [1, 2, 3]
        assert artifact.priority == HandoffPriority.HIGH


class TestHandoffManager:
    """Tests for HandoffManager functionality."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = HandoffManager()
        assert len(manager._artifacts) == 0
        assert len(manager._handoff_history) == 0

    def test_create_artifact(self):
        """Test artifact creation."""
        manager = HandoffManager()
        artifact = manager.create_artifact(
            key="test",
            value="value",
            priority=HandoffPriority.HIGH,
            source_agent="agent1"
        )

        assert artifact.key == "test"
        assert manager.has_artifact("test")

    def test_get_artifact(self):
        """Test retrieving artifacts."""
        manager = HandoffManager()
        created = manager.create_artifact("key1", "value1")

        retrieved = manager.get_artifact("key1")
        assert retrieved is not None
        assert retrieved.key == "key1"

    def test_remove_artifact(self):
        """Test artifact removal."""
        manager = HandoffManager()
        manager.create_artifact("key1", "value1")

        assert manager.has_artifact("key1") is True
        assert manager.remove_artifact("key1") is True
        assert manager.has_artifact("key1") is False

    def test_list_artifacts_by_priority(self):
        """Test filtering artifacts by priority."""
        manager = HandoffManager()
        manager.create_artifact("critical", "val1", HandoffPriority.CRITICAL)
        manager.create_artifact("high", "val2", HandoffPriority.HIGH)
        manager.create_artifact("low", "val3", HandoffPriority.LOW)

        critical = manager.list_artifacts(priority=HandoffPriority.CRITICAL)
        assert len(critical) == 1
        assert critical[0].key == "critical"

    def test_list_artifacts_by_source(self):
        """Test filtering artifacts by source agent."""
        manager = HandoffManager()
        manager.create_artifact("key1", "val1", source_agent="agent1")
        manager.create_artifact("key2", "val2", source_agent="agent2")

        agent1_artifacts = manager.list_artifacts(source_agent="agent1")
        assert len(agent1_artifacts) == 1
        assert agent1_artifacts[0].source_agent == "agent1"

    def test_create_from_workflow_state(self):
        """Test creating artifacts from workflow state."""
        manager = HandoffManager()
        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12",
            db_config=DatabaseConfig(
                db_name="milvus",
                version="2.6.12"
            )
        )

        artifacts = manager.create_from_workflow_state(state, source_agent="agent1")

        # Should have created multiple artifacts
        assert len(artifacts) > 0

        # Check for expected artifacts
        keys = [a.key for a in artifacts]
        assert "run_id" in keys
        assert "db_config" in keys
        assert "target_db_input" in keys

    def test_restore_to_workflow_state(self):
        """Test restoring artifacts to workflow state."""
        manager = HandoffManager()
        state = WorkflowState(
            run_id="",
            iteration_count=0,
            max_iterations=10,
            target_db_input=""
        )

        # Create artifacts
        manager.create_artifact("run_id", "test-run-123", HandoffPriority.CRITICAL)
        manager.create_artifact("iteration_count", 7, HandoffPriority.HIGH)
        manager.create_artifact("target_db_input", "Milvus v2.6.12", HandoffPriority.HIGH)

        # Restore
        restored = manager.restore_to_workflow_state(state)

        assert restored == 3
        assert state.run_id == "test-run-123"
        assert state.iteration_count == 7
        assert state.target_db_input == "Milvus v2.6.12"

    def test_filter_for_reset(self):
        """Test filtering artifacts for context reset."""
        config = HandoffConfig(
            preserve_critical_artifacts=True,
            preserve_high_artifacts=True,
            preserve_medium_artifacts=False
        )
        manager = HandoffManager(config)

        manager.create_artifact("critical", "val1", HandoffPriority.CRITICAL)
        manager.create_artifact("high", "val2", HandoffPriority.HIGH)
        manager.create_artifact("medium", "val3", HandoffPriority.MEDIUM)

        preserved = manager.filter_for_reset()
        keys = [a.key for a in preserved]

        assert "critical" in keys
        assert "high" in keys
        assert "medium" not in keys

    def test_clear_except_preserved(self):
        """Test clearing non-preserved artifacts."""
        config = HandoffConfig(
            preserve_critical_artifacts=True,
            preserve_high_artifacts=False
        )
        manager = HandoffManager(config)

        manager.create_artifact("critical", "val1", HandoffPriority.CRITICAL)
        manager.create_artifact("high", "val2", HandoffPriority.HIGH)

        manager.clear_except_preserved()

        assert manager.has_artifact("critical") is True
        assert manager.has_artifact("high") is False

    def test_export_import_artifacts(self):
        """Test exporting and importing artifacts."""
        manager = HandoffManager()
        manager.create_artifact("key1", "value1", HandoffPriority.HIGH)
        manager.create_artifact("key2", "value2", HandoffPriority.MEDIUM)

        # Export
        json_data = manager.export_artifacts(priority_threshold=HandoffPriority.MEDIUM)
        assert '"key": "key1"' in json_data
        assert '"key": "key2"' in json_data

        # Import to new manager
        new_manager = HandoffManager()
        count = new_manager.import_artifacts(json_data)
        assert count == 2
        assert new_manager.has_artifact("key1")
        assert new_manager.has_artifact("key2")

    def test_record_handoff(self):
        """Test recording handoff events."""
        manager = HandoffManager()
        manager.record_handoff("agent1", "agent2", 5)

        history = manager.get_handoff_history()
        assert len(history) == 1
        assert history[0]["from_agent"] == "agent1"
        assert history[0]["to_agent"] == "agent2"
        assert history[0]["artifact_count"] == 5


# ============================================================================
# Integration Tests
# ============================================================================

class TestContextResetIntegration:
    """Integration tests for context reset with handoff."""

    def test_reset_with_handoff_preservation(self):
        """Test that context reset preserves handoff artifacts."""
        reset_manager = ResetManager()
        handoff_manager = HandoffManager()

        state = WorkflowState(
            run_id="test-run",
            iteration_count=5,
            max_iterations=10,
            target_db_input="Milvus v2.6.12",
            db_config=DatabaseConfig(db_name="milvus", version="2.6.12"),
            total_tokens_used=50000
        )

        # Create handoff artifacts from state
        handoff_manager.create_from_workflow_state(state, source_agent="agent1")

        # Perform reset
        asyncio.run(reset_manager.reset(state, ResetTrigger.ITERATION_COUNT))

        # Restore critical artifacts
        handoff_manager.restore_to_workflow_state(state, HandoffPriority.CRITICAL)

        # Verify critical state preserved
        assert state.run_id == "test-run"
        assert state.db_config is not None
        assert state.db_config.db_name == "milvus"

    def test_full_reset_cycle(self):
        """Test complete reset cycle with handoff."""
        reset_config = ResetConfig(
            reset_interval=3,
            keep_defect_reports=True,
            keep_history_sample=10
        )
        reset_manager = ResetManager(reset_config)
        # Use a larger artifact size limit for this test
        handoff_config = HandoffConfig(max_artifact_size_bytes=50000)
        handoff_manager = HandoffManager(handoff_config)

        # Simulate workflow iterations
        state = WorkflowState(
            run_id="test-run",
            iteration_count=0,
            max_iterations=10,
            target_db_input="Milvus v2.6.12"
        )

        # Iteration 1-3: Build up state
        for i in range(1, 4):
            state.iteration_count = i
            state.history_vectors.extend([[float(i)] * 128 for _ in range(10)])
            state.total_tokens_used += 10000

        # Create artifacts before reset
        handoff_manager.create_from_workflow_state(state)

        # Reset at iteration 3
        asyncio.run(reset_manager.reset(state, ResetTrigger.ITERATION_COUNT))

        # Verify reset
        assert state.total_tokens_used == 0
        assert len(state.history_vectors) <= 10  # Sample preserved

        # Restore artifacts
        handoff_manager.restore_to_workflow_state(state)

        # Verify continuity
        assert state.run_id == "test-run"
        assert state.iteration_count == 3  # Progress preserved


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
