"""
Unit Tests for State Compression and Optimization

Test coverage goals: 90%+
Tests compression algorithms, incremental updates, and storage optimization.

Author: AI-DB-QC Team
Version: 2.0.0
Date: 2026-04-02
"""

import pytest
import tempfile
import shutil
from pathlib import Path
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
    StateManager,
    CompressionUtils
)


# ============================================================================
# CompressionUtils Tests
# ============================================================================

class TestCompressionUtils:
    """Tests for CompressionUtils class."""

    def test_compress_decompress_gzip(self):
        """Test gzip compression and decompression."""
        original_data = b"This is test data for compression testing" * 100
        compressed = CompressionUtils.compress_data(original_data, algorithm="gzip")
        decompressed = CompressionUtils.decompress_data(compressed, algorithm="gzip")

        assert decompressed == original_data
        assert len(compressed) < len(original_data)

    def test_compress_decompress_zlib(self):
        """Test zlib compression and decompression."""
        original_data = b"This is test data for compression testing" * 100
        compressed = CompressionUtils.compress_data(original_data, algorithm="zlib")
        decompressed = CompressionUtils.decompress_data(compressed, algorithm="zlib")

        assert decompressed == original_data
        assert len(compressed) < len(original_data)

    def test_compress_vectors_empty(self):
        """Test compressing empty vector list."""
        vectors = []
        compressed = CompressionUtils.compress_vectors(vectors)
        assert compressed == b""

    def test_compress_decompress_vectors(self):
        """Test vector compression and decompression."""
        vectors = [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 0.7, 0.8],
            [0.9, 1.0, 1.1, 1.2]
        ]

        compressed = CompressionUtils.compress_vectors(vectors)
        decompressed = CompressionUtils.decompress_vectors(compressed)

        assert len(decompressed) == len(vectors)
        for i, vec in enumerate(decompressed):
            assert len(vec) == len(vectors[i])
            for j, val in enumerate(vec):
                assert abs(val - vectors[i][j]) < 1e-6  # Float precision tolerance

    def test_compress_vectors_large_dataset(self):
        """Test compression of large vector dataset."""
        # Create 1000 vectors of 128 dimensions each
        vectors = [[float(i * 128 + j) / 1000.0 for j in range(128)] for i in range(1000)]

        compressed = CompressionUtils.compress_vectors(vectors)
        decompressed = CompressionUtils.decompress_vectors(compressed)

        assert len(decompressed) == 1000
        assert len(decompressed[0]) == 128

        # Check compression ratio
        original_size = len(str(vectors))
        compression_ratio = (1 - len(compressed) / original_size) * 100
        assert compression_ratio > 50  # Should achieve at least 50% compression

    def test_compress_vectors_mixed_dimensions_error(self):
        """Test that vectors with mixed dimensions raise error."""
        vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5]  # Different dimension
        ]

        with pytest.raises(ValueError, match="All vectors must have the same dimension"):
            CompressionUtils.compress_vectors(vectors)

    def test_calculate_hash(self):
        """Test hash calculation."""
        data = b"Test data for hashing"
        hash1 = CompressionUtils.calculate_hash(data)
        hash2 = CompressionUtils.calculate_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_calculate_hash_different_data(self):
        """Test that different data produces different hashes."""
        data1 = b"Test data 1"
        data2 = b"Test data 2"

        hash1 = CompressionUtils.calculate_hash(data1)
        hash2 = CompressionUtils.calculate_hash(data2)

        assert hash1 != hash2


# ============================================================================
# StateManager Compression Tests
# ============================================================================

class TestStateManagerCompression:
    """Tests for StateManager compression functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = StateManager(base_dir=self.temp_dir, compression_algorithm="gzip")

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_load_compressed_state(self):
        """Test saving and loading compressed state."""
        state = WorkflowState(
            run_id="test-run-001",
            target_db_input="Milvus v2.6.12",
            business_scenario="Test scenario"
        )

        # Save state
        stats = self.manager.save_state("test-run-001", state)

        # Verify compression stats
        assert stats["compressed_size"] > 0
        assert stats["original_size"] > 0
        assert stats["compression_ratio"] > 0

        # Load state
        loaded_state = self.manager.load_state("test-run-001")

        # Verify state integrity
        assert loaded_state.run_id == state.run_id
        assert loaded_state.target_db_input == state.target_db_input
        assert loaded_state.business_scenario == state.business_scenario

    def test_save_load_state_with_vectors(self):
        """Test saving and loading state with compressed vectors."""
        # Create state with large vector history
        state = WorkflowState(
            run_id="test-run-002",
            target_db_input="Milvus"
        )

        # Add 500 vectors of 128 dimensions
        state.history_vectors = [[float(i * 128 + j) / 500.0 for j in range(128)] for i in range(500)]

        # Save state
        stats = self.manager.save_state("test-run-002", state)

        # Verify compression
        assert stats["compression_ratio"] > 50  # Should achieve at least 50% compression

        # Load state
        loaded_state = self.manager.load_state("test-run-002")

        # Verify vectors are correctly decompressed
        assert len(loaded_state.history_vectors) == 500
        assert len(loaded_state.history_vectors[0]) == 128

        # Verify vector values
        for i, vec in enumerate(loaded_state.history_vectors):
            for j, val in enumerate(vec):
                expected = float(i * 128 + j) / 500.0
                assert abs(val - expected) < 1e-6

    def test_save_state_with_mixed_dimension_history_vectors_normalizes_before_compress(self):
        """Mixed dimensions should be normalized before vector compression."""
        state = WorkflowState(
            run_id="test-run-mixed-dims",
            target_db_input="Milvus"
        )
        state.history_vectors = [
            [1.0, 2.0, 3.0, 4.0],      # dim=4
            [5.0, 6.0],                # dim=2 -> pad
            [7.0, 8.0, 9.0, 10.0],     # dim=4
            [11.0, 12.0, 13.0, 14.0, 15.0]  # dim=5 -> truncate (mode dim=4)
        ]

        # Should not raise "All vectors must have the same dimension"
        stats = self.manager.save_state("test-run-mixed-dims", state)
        assert stats["compressed_size"] > 0

        loaded_state = self.manager.load_state("test-run-mixed-dims")
        assert loaded_state is not None
        assert len(loaded_state.history_vectors) == 4
        assert all(len(v) == 4 for v in loaded_state.history_vectors)

        # Verify pad/truncate behavior
        assert loaded_state.history_vectors[1] == [5.0, 6.0, 0.0, 0.0]  # padded
        assert loaded_state.history_vectors[3] == [11.0, 12.0, 13.0, 14.0]  # truncated

    def test_save_state_mixed_dimensions_keeps_main_flow_final_save_safe(self):
        """Simulate main final save path: save should succeed even with mixed dimensions."""
        state = WorkflowState(
            run_id="test-run-final-save-safe",
            target_db_input="Weaviate"
        )
        state.iteration_count = 3
        state.total_tokens_used = 12345
        state.history_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6, 0.7],
            [0.8],
        ]

        # Equivalent to main.py finally block save_state(...), should not throw.
        stats = self.manager.save_state("test-run-final-save-safe", state)
        assert stats["compressed_size"] > 0

        reloaded = self.manager.load_state("test-run-final-save-safe")
        assert reloaded is not None
        assert reloaded.iteration_count == 3
        assert reloaded.total_tokens_used == 12345
        assert len(reloaded.history_vectors) == 3

    def test_save_load_state_with_large_datasets(self):
        """Test compression with large datasets."""
        state = WorkflowState(
            run_id="test-run-003",
            target_db_input="Qdrant"
        )

        # Add large datasets
        state.current_test_cases = [
            TestCase(
                case_id=f"test-{i:04d}",
                dimension=128,
                query_vector=[float(j) / 128.0 for j in range(128)]
            ) for i in range(100)
        ]

        state.execution_results = [
            ExecutionResult(
                case_id=f"test-{i:04d}",
                success=True,
                l1_passed=True,
                l2_passed=True,
                execution_time_ms=50.0 + i
            ) for i in range(100)
        ]

        state.oracle_results = [
            OracleValidation(
                case_id=f"test-{i:04d}",
                passed=True,
                anomalies=[],
                explanation=f"Validation {i}"
            ) for i in range(100)
        ]

        # Save state
        stats = self.manager.save_state("test-run-003", state)

        # Verify compression
        assert stats["compression_ratio"] > 50

        # Load and verify
        loaded_state = self.manager.load_state("test-run-003")
        assert len(loaded_state.current_test_cases) == 100
        assert len(loaded_state.execution_results) == 100
        assert len(loaded_state.oracle_results) == 100

    def test_get_compression_stats(self):
        """Test getting compression statistics."""
        state = WorkflowState(
            run_id="test-run-004",
            target_db_input="Milvus"
        )

        self.manager.save_state("test-run-004", state)

        stats = self.manager.get_compression_stats("test-run-004")

        assert stats is not None
        assert stats["original_size"] > 0
        assert stats["compressed_size"] > 0
        assert stats["compression_ratio"] > 0
        assert stats["algorithm"] == "gzip"
        assert "timestamp" in stats

    def test_get_compression_stats_nonexistent(self):
        """Test getting stats for non-existent run."""
        stats = self.manager.get_compression_stats("nonexistent-run")
        assert stats is None

    def test_incremental_update(self):
        """Test incremental state update."""
        # Create initial state
        state = WorkflowState(
            run_id="test-run-005",
            target_db_input="Milvus",
            iteration_count=0
        )

        self.manager.save_state("test-run-005", state)

        # Perform incremental update
        updates = {
            "iteration_count": 5,
            "total_tokens_used": 10000,
            "should_terminate": False
        }

        update_stats = self.manager.incremental_update("test-run-005", updates)

        assert update_stats["updated"] is True
        assert "iteration_count" in update_stats["fields_updated"]
        assert "total_tokens_used" in update_stats["fields_updated"]

        # Verify update
        loaded_state = self.manager.load_state("test-run-005")
        assert loaded_state.iteration_count == 5
        assert loaded_state.total_tokens_used == 10000

    def test_incremental_update_nonexistent(self):
        """Test incremental update on non-existent run."""
        with pytest.raises(ValueError, match="Run nonexistent-run not found"):
            self.manager.incremental_update("nonexistent-run", {"iteration_count": 1})

    def test_optimize_storage(self):
        """Test storage optimization."""
        state = WorkflowState(
            run_id="test-run-006",
            target_db_input="Milvus"
        )

        # Add vectors
        state.history_vectors = [[float(i * 128 + j) / 100.0 for j in range(128)] for i in range(100)]

        # Save initial state
        self.manager.save_state("test-run-006", state)

        # Optimize storage
        opt_stats = self.manager.optimize_storage("test-run-006")

        assert opt_stats["optimized"] is True
        assert opt_stats["new_size"] > 0

        # Verify state still loads correctly
        loaded_state = self.manager.load_state("test-run-006")
        assert len(loaded_state.history_vectors) == 100

    def test_cleanup_old_versions(self):
        """Test cleanup of old state versions."""
        state = WorkflowState(
            run_id="test-run-007",
            target_db_input="Milvus"
        )

        # Save multiple versions
        for i in range(5):
            state.iteration_count = i
            self.manager.save_state("test-run-007", state)

        # Cleanup, keeping only 3 versions
        deleted_count = self.manager.cleanup_old_versions("test-run-007", keep_versions=3)

        assert deleted_count >= 0

        # Verify state still loads
        loaded_state = self.manager.load_state("test-run-007")
        assert loaded_state is not None

    def test_compression_algorithm_zlib(self):
        """Test using zlib compression algorithm."""
        manager_zlib = StateManager(base_dir=self.temp_dir, compression_algorithm="zlib")

        state = WorkflowState(
            run_id="test-run-008",
            target_db_input="Milvus"
        )

        stats = manager_zlib.save_state("test-run-008", state)

        assert stats["algorithm"] == "zlib"
        assert stats["compression_ratio"] > 0

        # Verify load works
        loaded_state = manager_zlib.load_state("test-run-008")
        assert loaded_state.run_id == state.run_id

    def test_backward_compatibility_uncompressed(self):
        """Test loading uncompressed JSON files (backward compatibility)."""
        state = WorkflowState(
            run_id="test-run-009",
            target_db_input="Milvus"
        )

        # Manually save uncompressed JSON
        import json
        run_dir = Path(self.temp_dir) / "test-run-009"
        run_dir.mkdir(parents=True, exist_ok=True)

        state_file = run_dir / "state.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.model_dump(), f, indent=2)

        # Load using StateManager
        loaded_state = self.manager.load_state("test-run-009")

        assert loaded_state.run_id == state.run_id
        assert loaded_state.target_db_input == state.target_db_input


# ============================================================================
# Compression Performance Tests
# ============================================================================

class TestCompressionPerformance:
    """Tests for compression performance and efficiency."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = StateManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_compression_ratio_target_50_percent(self):
        """Test that compression achieves at least 50% reduction."""
        state = WorkflowState(
            run_id="perf-test-001",
            target_db_input="Milvus"
        )

        # Add substantial data
        state.history_vectors = [[float(i * 128 + j) / 1000.0 for j in range(128)] for i in range(1000)]
        state.current_test_cases = [
            TestCase(
                case_id=f"test-{i:04d}",
                dimension=128,
                query_vector=[float(j) / 128.0 for j in range(128)]
            ) for i in range(100)
        ]

        stats = self.manager.save_state("perf-test-001", state)

        # Verify compression ratio meets target
        assert stats["compression_ratio"] >= 50.0, \
            f"Compression ratio {stats['compression_ratio']}% is below 50% target"

    def test_compression_with_defect_reports(self):
        """Test compression with defect reports."""
        state = WorkflowState(
            run_id="perf-test-002",
            target_db_input="Milvus"
        )

        # Add defect reports with detailed information
        state.defect_reports = [
            DefectReport(
                case_id=f"bug-{i:04d}",
                bug_type="TYPE_1",
                evidence_level="L1",
                root_cause_analysis=f"Root cause analysis for bug {i} with detailed explanation",
                title=f"Bug title {i}",
                operation="search",
                error_message=f"Error message {i}",
                database="Milvus v2.6.12",
                verification_log="Detailed verification log with multiple lines of information"
            ) for i in range(50)
        ]

        stats = self.manager.save_state("perf-test-002", state)

        # Verify compression
        assert stats["compression_ratio"] > 30  # Text data should still compress well

    def test_load_performance(self):
        """Test that loading compressed state is efficient."""
        state = WorkflowState(
            run_id="perf-test-003",
            target_db_input="Milvus"
        )

        # Add large dataset
        state.history_vectors = [[float(i * 128 + j) / 500.0 for j in range(128)] for i in range(500)]
        state.current_test_cases = [
            TestCase(
                case_id=f"test-{i:04d}",
                dimension=128,
                query_vector=[float(j) / 128.0 for j in range(128)]
            ) for i in range(200)
        ]

        # Save state
        self.manager.save_state("perf-test-003", state)

        # Load and verify
        loaded_state = self.manager.load_state("perf-test-003")

        assert loaded_state is not None
        assert len(loaded_state.history_vectors) == 500
        assert len(loaded_state.current_test_cases) == 200


# ============================================================================
# Integration Tests
# ============================================================================

class TestStateCompressionIntegration:
    """Integration tests for state compression."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = StateManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_full_workflow_with_compression(self):
        """Test complete workflow with compression."""
        # Create initial state
        state = WorkflowState(
            run_id="integration-test-001",
            target_db_input="Milvus v2.6.12",
            business_scenario="E-commerce search"
        )

        # Add database config
        state.db_config = DatabaseConfig(
            db_name="Milvus",
            version="2.6.12",
            endpoint="localhost:19530"
        )

        # Add contracts
        state.contracts = Contract(
            l1_api={"dimension": 128},
            l2_semantic={"metric": "cosine"}
        )

        # Save initial state
        stats1 = self.manager.save_state("integration-test-001", state)
        assert stats1["compression_ratio"] > 0

        # Simulate iteration 1
        state.iteration_count = 1
        state.current_test_cases = [
            TestCase(
                case_id=f"test-{i:04d}",
                dimension=128,
                query_vector=[float(j) / 128.0 for j in range(128)]
            ) for i in range(10)
        ]

        # Incremental update
        update_stats = self.manager.incremental_update("integration-test-001", {
            "iteration_count": 1,
            "current_test_cases": state.current_test_cases
        })

        assert update_stats["updated"] is True

        # Simulate iteration 2 with execution results
        state.iteration_count = 2
        state.execution_results = [
            ExecutionResult(
                case_id=f"test-{i:04d}",
                success=True,
                l1_passed=True,
                l2_passed=True,
                execution_time_ms=50.0
            ) for i in range(10)
        ]

        # Another incremental update
        self.manager.incremental_update("integration-test-001", {
            "iteration_count": 2,
            "execution_results": state.execution_results
        })

        # Add vectors for coverage tracking
        state.history_vectors = [[float(i * 128 + j) / 100.0 for j in range(128)] for i in range(100)]

        # Save with vectors
        stats2 = self.manager.save_state("integration-test-001", state)
        assert stats2["compression_ratio"] > 50  # Vectors should compress well

        # Load final state
        final_state = self.manager.load_state("integration-test-001")

        # Verify all data is intact
        assert final_state.run_id == "integration-test-001"
        assert final_state.iteration_count == 2
        assert len(final_state.current_test_cases) == 10
        assert len(final_state.execution_results) == 10
        assert len(final_state.history_vectors) == 100
        assert final_state.db_config.db_name == "Milvus"
        assert final_state.contracts.l1_api["dimension"] == 128

    def test_multiple_runs_compression(self):
        """Test compression across multiple runs."""
        runs = []

        for i in range(5):
            state = WorkflowState(
                run_id=f"multi-run-{i:03d}",
                target_db_input="Milvus"
            )

            # Add varying amounts of data
            state.history_vectors = [
                [float(j * 128 + k) / ((i + 1) * 100.0) for k in range(128)]
                for j in range((i + 1) * 50)
            ]

            stats = self.manager.save_state(f"multi-run-{i:03d}", state)
            runs.append(stats)

            # Verify each run compresses well
            assert stats["compression_ratio"] > 30

        # Verify all runs can be loaded
        for i in range(5):
            loaded_state = self.manager.load_state(f"multi-run-{i:03d}")
            assert loaded_state is not None
            assert len(loaded_state.history_vectors) == (i + 1) * 50


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/state", "--cov-report=term-missing"])
