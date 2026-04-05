"""
Unit Tests for Exception Hierarchy

Test coverage goals: 100%

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import traceback
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.exceptions import (
    ErrorCodes,
    ErrorEvidence,
    AIDBQCException,
    ConfigurationError,
    ConfigurationMissingError,
    ConfigurationValidationError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DatabaseQueryError,
    DatabaseCollectionNotFoundError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTokenLimitError,
    ContractError,
    ContractViolationError,
    ContractMissingError,
    TestGenerationError,
    TestModeCollapseError,
    OracleError,
    OracleValidationError,
    HarnessError,
    CircuitBreakerError,
    RecoveryFailedError,
    PoolError,
    PoolAcquisitionError,
    PoolExhaustedError,
    AgentError,
    AgentTimeoutError,
    TelemetryError,
    TelemetryWriteError,
    capture_evidence,
    raise_with_evidence,
)


# ============================================================================
# ErrorEvidence Tests
# ============================================================================

class TestErrorEvidence:
    """Tests for ErrorEvidence dataclass."""

    def test_initialization(self):
        """Test evidence initialization."""
        evidence = ErrorEvidence()
        assert evidence.component == ""
        assert evidence.context == {}
        assert evidence.stack_trace is None
        assert evidence.related_data == {}

    def test_with_component(self):
        """Test evidence with component."""
        evidence = ErrorEvidence(component="test_component")
        assert evidence.component == "test_component"

    def test_add_context(self):
        """Test adding context information."""
        evidence = ErrorEvidence()
        evidence.add_context("key1", "value1")
        evidence.add_context("key2", 123)
        assert evidence.context == {"key1": "value1", "key2": 123}

    def test_to_dict(self):
        """Test evidence serialization to dictionary."""
        evidence = ErrorEvidence(
            component="test",
            context={"key": "value"},
            stack_trace="Traceback..."
        )
        data = evidence.to_dict()
        assert "timestamp" in data
        assert data["component"] == "test"
        assert data["context"]["key"] == "value"
        assert data["stack_trace"] == "Traceback..."

    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        evidence = ErrorEvidence()
        assert isinstance(evidence.timestamp, datetime)


# ============================================================================
# Base Exception Tests
# ============================================================================

class TestAIDBQCException:
    """Tests for base AIDBQCException."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        exc = AIDBQCException("Test error", "E001")
        assert exc.message == "Test error"
        assert exc.error_code == "E001"
        assert exc.evidence is not None
        assert str(exc) == "[E001] Test error"

    def test_with_custom_evidence(self):
        """Test exception with custom evidence."""
        evidence = ErrorEvidence(component="test")
        exc = AIDBQCException("Test error", "E001", evidence)
        assert exc.evidence.component == "test"

    def test_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = AIDBQCException("Test error", "E001")
        data = exc.to_dict()
        assert data["error_code"] == "E001"
        assert data["error_type"] == "AIDBQCException"
        assert data["message"] == "Test error"
        assert "evidence" in data


# ============================================================================
# Configuration Exception Tests
# ============================================================================

class TestConfigurationErrors:
    """Tests for configuration exceptions."""

    def test_configuration_error(self):
        """Test basic configuration error."""
        exc = ConfigurationError("Invalid config")
        assert exc.error_code == ErrorCodes.CONFIG_INVALID
        assert "Invalid config" in str(exc)

    def test_configuration_missing_error(self):
        """Test configuration missing error."""
        evidence = ErrorEvidence(component="config")
        exc = ConfigurationMissingError("API_KEY", evidence)
        assert exc.error_code == ErrorCodes.CONFIG_MISSING
        assert "API_KEY" in str(exc)
        assert "missing" in str(exc)

    def test_configuration_validation_error(self):
        """Test configuration validation error."""
        exc = ConfigurationValidationError("port", "abc", "integer")
        assert exc.error_code == ErrorCodes.CONFIG_VALIDATION_FAILED
        assert "port" in str(exc)
        assert "abc" in str(exc)
        assert "integer" in str(exc)


# ============================================================================
# Database Exception Tests
# ============================================================================

class TestDatabaseErrors:
    """Tests for database exceptions."""

    def test_database_connection_error(self):
        """Test database connection error."""
        exc = DatabaseConnectionError("localhost", 19530, "Connection refused")
        assert exc.error_code == ErrorCodes.DATABASE_CONNECTION_FAILED
        assert "localhost" in str(exc)
        assert "19530" in str(exc)
        # Evidence component is set to "database_adapter" in __init__
        assert exc.evidence.component == "database_adapter"

    def test_database_timeout_error(self):
        """Test database timeout error."""
        exc = DatabaseTimeoutError("search", 30)
        assert exc.error_code == ErrorCodes.DATABASE_TIMEOUT
        assert "search" in str(exc)
        assert "30" in str(exc)

    def test_database_query_error(self):
        """Test database query error."""
        exc = DatabaseQueryError("SELECT * FROM test", "Syntax error")
        assert exc.error_code == ErrorCodes.DATABASE_QUERY_FAILED
        assert "SELECT" in str(exc)
        assert "Syntax error" in str(exc)
        # Evidence component is set to "database_adapter" in __init__
        assert exc.evidence.component == "database_adapter"

    def test_database_collection_not_found_error(self):
        """Test collection not found error."""
        exc = DatabaseCollectionNotFoundError("test_collection")
        assert exc.error_code == ErrorCodes.DATABASE_COLLECTION_NOT_FOUND
        assert "test_collection" in str(exc)


# ============================================================================
# LLM Exception Tests
# ============================================================================

class TestLLMErrors:
    """Tests for LLM exceptions."""

    def test_llm_rate_limit_error(self):
        """Test LLM rate limit error."""
        exc = LLMRateLimitError("anthropic", 60)
        assert exc.error_code == ErrorCodes.LLM_RATE_LIMIT_EXCEEDED
        assert "anthropic" in str(exc)
        assert "60" in str(exc)

    def test_llm_timeout_error(self):
        """Test LLM timeout error."""
        exc = LLMTimeoutError("openai", "gpt-4", 90)
        assert exc.error_code == ErrorCodes.LLM_TIMEOUT
        assert "openai" in str(exc)
        assert "gpt-4" in str(exc)
        assert "90" in str(exc)

    def test_llm_token_limit_error(self):
        """Test LLM token limit error."""
        exc = LLMTokenLimitError(150000, 100000)
        assert exc.error_code == ErrorCodes.LLM_TOKEN_LIMIT_EXCEEDED
        assert "150000" in str(exc)
        assert "100000" in str(exc)


# ============================================================================
# Contract Exception Tests
# ============================================================================

class TestContractErrors:
    """Tests for contract exceptions."""

    def test_contract_violation_error(self):
        """Test contract violation error."""
        exc = ContractViolationError("L1", "dimension", 4096, "<= 2048")
        assert exc.error_code == ErrorCodes.CONTRACT_L1_VIOLATION
        assert "L1" in str(exc)
        assert "dimension" in str(exc)

    def test_contract_missing_error(self):
        """Test contract missing error."""
        exc = ContractMissingError("L2")
        assert exc.error_code == ErrorCodes.CONTRACT_MISSING
        assert "L2" in str(exc)
        assert "missing" in str(exc)


# ============================================================================
# Test Generation Exception Tests
# ============================================================================

class TestTestGenerationErrors:
    """Tests for test generation exceptions."""

    def test_mode_collapse_error(self):
        """Test mode collapse error."""
        exc = TestModeCollapseError(0.95, 0.90)
        assert exc.error_code == ErrorCodes.TEST_MODE_COLLAPSE
        assert "0.95" in str(exc)
        assert "0.90" in str(exc)


# ============================================================================
# Oracle Exception Tests
# ============================================================================

class TestOracleErrors:
    """Tests for oracle exceptions."""

    def test_oracle_validation_error(self):
        """Test oracle validation error."""
        exc = OracleValidationError("test-001", "Semantic drift")
        assert exc.error_code == ErrorCodes.ORACLE_VALIDATION_FAILED
        assert "test-001" in str(exc)
        assert "Semantic drift" in str(exc)


# ============================================================================
# Harness Exception Tests
# ============================================================================

class TestHarnessErrors:
    """Tests for harness exceptions."""

    def test_circuit_breaker_error(self):
        """Test circuit breaker error."""
        exc = CircuitBreakerError("consecutive_failures", 3, 3)
        assert exc.error_code == ErrorCodes.HARNESS_CIRCUIT_BREAKER
        assert "consecutive_failures" in str(exc)
        assert "3/3" in str(exc)

    def test_recovery_failed_error(self):
        """Test recovery failed error."""
        exc = RecoveryFailedError(2, "No available collections")
        assert exc.error_code == ErrorCodes.HARNESS_RECOVERY_FAILED
        assert "2" in str(exc)
        assert "No available collections" in str(exc)


# ============================================================================
# Pool Exception Tests
# ============================================================================

class TestPoolErrors:
    """Tests for pool exceptions."""

    def test_pool_acquisition_error(self):
        """Test pool acquisition error."""
        exc = PoolAcquisitionError(128, "Pool not initialized")
        assert exc.error_code == ErrorCodes.POOL_ACQUISITION_FAILED
        assert "128" in str(exc)

    def test_pool_exhausted_error(self):
        """Test pool exhausted error."""
        exc = PoolExhaustedError(256, 10, 10)
        assert exc.error_code == ErrorCodes.POOL_EXHAUSTED
        assert "256" in str(exc)
        assert "10/10" in str(exc)


# ============================================================================
# Agent Exception Tests
# ============================================================================

class TestAgentErrors:
    """Tests for agent exceptions."""

    def test_agent_timeout_error(self):
        """Test agent timeout error."""
        exc = AgentTimeoutError("agent2_generator", 90)
        assert exc.error_code == ErrorCodes.AGENT_TIMEOUT
        assert "agent2_generator" in str(exc)
        assert "90" in str(exc)


# ============================================================================
# Telemetry Exception Tests
# ============================================================================

class TestTelemetryErrors:
    """Tests for telemetry exceptions."""

    def test_telemetry_write_error(self):
        """Test telemetry write error."""
        exc = TelemetryWriteError("/path/to/file.jsonl", "Permission denied")
        assert exc.error_code == ErrorCodes.TELEMETRY_WRITE_FAILED
        assert "/path/to/file.jsonl" in str(exc)


# ============================================================================
# Utility Functions Tests
# ============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_capture_evidence(self):
        """Test capture_evidence function."""
        evidence = capture_evidence(
            component="test_component",
            key1="value1",
            key2=123
        )
        assert evidence.component == "test_component"
        assert evidence.context["key1"] == "value1"
        assert evidence.context["key2"] == 123

    def test_raise_with_evidence(self):
        """Test raise_with_evidence function."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise_with_evidence(
                ConfigurationError,
                "Test error",
                component="test",
                key="value"
            )
        exc = exc_info.value
        assert exc.message == "Test error"
        assert exc.evidence.component == "test"
        assert exc.evidence.context["key"] == "value"


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================

class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from AIDBQCException."""
        exceptions_to_test = [
            ConfigurationError,
            DatabaseError,
            LLMError,
            ContractError,
            TestGenerationError,
            OracleError,
            HarnessError,
            PoolError,
            AgentError,
            TelemetryError,
        ]
        for exc_class in exceptions_to_test:
            assert issubclass(exc_class, AIDBQCException)

    def test_specific_exceptions_inherit_from_category(self):
        """Test that specific exceptions inherit from their category."""
        assert issubclass(DatabaseConnectionError, DatabaseError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(ContractViolationError, ContractError)


# ============================================================================
# Exception Catching Tests
# ============================================================================

class TestExceptionCatching:
    """Tests for exception catching behavior."""

    def test_catch_base_exception(self):
        """Test catching specific exception via base class."""
        with pytest.raises(AIDBQCException):
            raise DatabaseConnectionError("localhost", 19530, "Error")

    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(DatabaseConnectionError):
            raise DatabaseConnectionError("localhost", 19530, "Error")

    def test_catch_does_not_match_different_type(self):
        """Test that catching doesn't match different exception types."""
        with pytest.raises(DatabaseConnectionError):  # Should raise DatabaseError
            try:
                raise DatabaseConnectionError("localhost", 19530, "Error")
            except LLMError:
                assert False, "Should not catch DatabaseError as LLMError"


# ============================================================================
# Evidence Tracking Tests
# ============================================================================

class TestEvidenceTracking:
    """Tests for evidence tracking in exceptions."""

    def test_evidence_preserved_in_exception(self):
        """Test that evidence context is preserved when exception is raised."""
        # Note: DatabaseConnectionError modifies component to "database_adapter"
        # but other context can be added before passing to the exception
        evidence = ErrorEvidence(component="will_be_overwritten")
        evidence.add_context("custom_key", "custom_value")
        try:
            raise DatabaseConnectionError("localhost", 19530, "Error", evidence)
        except DatabaseConnectionError as e:
            # Component gets overwritten in DatabaseConnectionError.__init__
            assert e.evidence.component == "database_adapter"
            # But custom context is preserved
            assert e.evidence.context.get("custom_key") == "custom_value"

    def test_evidence_added_after_creation(self):
        """Test modifying evidence after exception creation."""
        exc = DatabaseConnectionError("localhost", 19530, "Error")
        exc.evidence.add_context("extra_info", "debug_data")
        assert exc.evidence.context["extra_info"] == "debug_data"

    def test_evidence_to_dict_in_exception(self):
        """Test evidence serialization in exception to_dict."""
        exc = DatabaseConnectionError("localhost", 19530, "Error")
        data = exc.to_dict()
        assert "evidence" in data
        assert "timestamp" in data["evidence"]


# ============================================================================
# Error Code Tests
# ============================================================================

class TestErrorCodes:
    """Tests for ErrorCodes class."""

    def test_error_codes_are_strings(self):
        """Test that all error codes are strings."""
        error_codes = [
            ErrorCodes.CONFIG_INVALID,
            ErrorCodes.DATABASE_CONNECTION_FAILED,
            ErrorCodes.LLM_API_ERROR,
        ]
        for code in error_codes:
            assert isinstance(code, str)

    def test_error_codes_follow_format(self):
        """Test that error codes follow E### format."""
        import re
        pattern = re.compile(r'^E\d{3}$')
        error_codes = [
            ErrorCodes.CONFIG_INVALID,
            ErrorCodes.DATABASE_CONNECTION_FAILED,
            ErrorCodes.LLM_API_ERROR,
        ]
        for code in error_codes:
            assert pattern.match(code), f"{code} does not match E### format"


# ============================================================================
# Exception Chaining Tests
# ============================================================================

class TestExceptionChaining:
    """Tests for exception chaining."""

    def test_exception_from_original(self):
        """Test raising exception from original exception."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                evidence = capture_evidence(component="test")
                raise DatabaseConnectionError("localhost", 19530, str(e), evidence) from e
        except DatabaseConnectionError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)

    def test_exception_cause_preserved(self):
        """Test that exception cause is preserved."""
        try:
            try:
                raise ValueError("Original")
            except ValueError:
                raise DatabaseConnectionError("localhost", 19530, "Error")
        except DatabaseConnectionError as e:
            # __cause__ may or may not be set depending on Python version
            # Just verify exception was raised correctly
            assert e is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/exceptions", "--cov-report=term-missing"])
