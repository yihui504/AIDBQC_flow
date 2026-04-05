"""
Exception Hierarchy for AI-DB-QC

This module defines a structured exception hierarchy with:
- Clear categorization of error types
- Evidence tracking for debugging
- Error codes for programmatic handling
- Human-readable messages

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field


# ============================================================================
# Error Codes Registry
# ============================================================================

class ErrorCodes:
    """Central registry of error codes for AI-DB-QC."""

    # Configuration Errors (E001-E099)
    CONFIG_INVALID = "E001"
    CONFIG_MISSING = "E002"
    CONFIG_VALIDATION_FAILED = "E003"

    # Database Errors (E100-E199)
    DATABASE_CONNECTION_FAILED = "E100"
    DATABASE_TIMEOUT = "E101"
    DATABASE_QUERY_FAILED = "E102"
    DATABASE_INSERT_FAILED = "E103"
    DATABASE_DELETE_FAILED = "E104"
    DATABASE_COLLECTION_NOT_FOUND = "E105"
    DATABASE_INDEX_ERROR = "E106"

    # LLM Errors (E200-E299)
    LLM_API_ERROR = "E200"
    LLM_RATE_LIMIT_EXCEEDED = "E201"
    LLM_TIMEOUT = "E202"
    LLM_INVALID_RESPONSE = "E203"
    LLM_TOKEN_LIMIT_EXCEEDED = "E204"

    # Contract Errors (E300-E399)
    CONTRACT_VIOLATION = "E300"
    CONTRACT_L1_VIOLATION = "E301"
    CONTRACT_L2_VIOLATION = "E302"
    CONTRACT_MISSING = "E303"
    CONTRACT_INVALID = "E304"

    # Test Generation Errors (E400-E499)
    TEST_GENERATION_FAILED = "E400"
    TEST_VALIDATION_FAILED = "E401"
    TEST_EXECUTION_FAILED = "E402"
    TEST_MODE_COLLAPSE = "E403"

    # Oracle Errors (E500-E599)
    ORACLE_EVALUATION_FAILED = "E500"
    ORACLE_VALIDATION_FAILED = "E501"
    ORACLE_INCONCLUSIVE_RESULT = "E502"

    # Harness/Workflow Errors (E600-E699)
    HARNESS_CIRCUIT_BREAKER = "E600"
    HARNESS_RECOVERY_FAILED = "E601"
    HARNESS_STATE_CORRUPTION = "E602"
    HARNESS_MAX_ITERATIONS_EXCEEDED = "E603"

    # Pool Errors (E700-E799)
    POOL_INITIALIZATION_FAILED = "E700"
    POOL_ACQUISITION_FAILED = "E701"
    POOL_RELEASE_FAILED = "E702"
    POOL_EXHAUSTED = "E703"

    # Agent Errors (E800-E899)
    AGENT_TIMEOUT = "E800"
    AGENT_FAILURE = "E801"
    AGENT_INVALID_RESPONSE = "E802"

    # Telemetry Errors (E900-E999)
    TELEMETRY_WRITE_FAILED = "E900"
    TELEMETRY_FILE_ERROR = "E901"


# ============================================================================
# Evidence Tracking
# ============================================================================

@dataclass
class ErrorEvidence:
    """
    Structured evidence for error diagnosis.

    Attributes:
        timestamp: When the error occurred
        component: Which component raised the error
        context: Relevant contextual information
        stack_trace: Python stack trace (if available)
        related_data: Additional diagnostic data
    """
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    related_data: Dict[str, Any] = field(default_factory=dict)

    def add_context(self, key: str, value: Any) -> None:
        """Add context information."""
        self.context[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "context": self.context,
            "stack_trace": self.stack_trace,
            "related_data": self.related_data
        }


# ============================================================================
# Base Exception
# ============================================================================

class AIDBQCException(Exception):
    """
    Base exception for all AI-DB-QC errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "E000",
        evidence: Optional[ErrorEvidence] = None
    ):
        self.message = message
        self.error_code = error_code
        self.evidence = evidence or ErrorEvidence()
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_code": self.error_code,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "evidence": self.evidence.to_dict()
        }


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(AIDBQCException):
    """Base class for configuration errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.CONFIG_INVALID,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class ConfigurationMissingError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(
        self,
        config_key: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Required configuration key '{config_key}' is missing"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "config"
        super().__init__(message, ErrorCodes.CONFIG_MISSING, evidence)


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        config_key: str,
        value: Any,
        expected: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Configuration key '{config_key}' has invalid value '{value}'. Expected: {expected}"
        if evidence:
            evidence.add_context("config_key", config_key)
            evidence.add_context("invalid_value", value)
            evidence.add_context("expected", expected)
        super().__init__(message, ErrorCodes.CONFIG_VALIDATION_FAILED, evidence)


# ============================================================================
# Database Exceptions
# ============================================================================

class DatabaseError(AIDBQCException):
    """Base class for database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.DATABASE_CONNECTION_FAILED,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(
        self,
        host: str,
        port: int,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Failed to connect to database at {host}:{port}. Reason: {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "database_adapter"
        evidence.add_context("host", host)
        evidence.add_context("port", port)
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.DATABASE_CONNECTION_FAILED, evidence)


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Database operation '{operation}' timed out after {timeout_seconds} seconds"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "database_adapter"
        evidence.add_context("operation", operation)
        evidence.add_context("timeout", timeout_seconds)
        super().__init__(message, ErrorCodes.DATABASE_TIMEOUT, evidence)


class DatabaseQueryError(DatabaseError):
    """Raised when database query fails."""

    def __init__(
        self,
        query: str,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Database query failed: '{query[:100]}...'. Reason: {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "database_adapter"
        evidence.add_context("query", query[:200])  # Truncate long queries
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.DATABASE_QUERY_FAILED, evidence)


class DatabaseCollectionNotFoundError(DatabaseError):
    """Raised when specified collection is not found."""

    def __init__(
        self,
        collection_name: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Collection '{collection_name}' not found in database"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "database_adapter"
        evidence.add_context("collection_name", collection_name)
        super().__init__(message, ErrorCodes.DATABASE_COLLECTION_NOT_FOUND, evidence)


# ============================================================================
# LLM Exceptions
# ============================================================================

class LLMError(AIDBQCException):
    """Base class for LLM-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.LLM_API_ERROR,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after_seconds: Optional[int] = None,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"LLM rate limit exceeded for provider '{provider}'"
        if retry_after_seconds:
            message += f". Retry after {retry_after_seconds} seconds"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "llm_client"
        evidence.add_context("provider", provider)
        evidence.add_context("retry_after", retry_after_seconds)
        super().__init__(message, ErrorCodes.LLM_RATE_LIMIT_EXCEEDED, evidence)


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(
        self,
        provider: str,
        model: str,
        timeout_seconds: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"LLM request to {provider}/{model} timed out after {timeout_seconds} seconds"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "llm_client"
        evidence.add_context("provider", provider)
        evidence.add_context("model", model)
        evidence.add_context("timeout", timeout_seconds)
        super().__init__(message, ErrorCodes.LLM_TIMEOUT, evidence)


class LLMTokenLimitError(LLMError):
    """Raised when LLM token budget is exceeded."""

    def __init__(
        self,
        tokens_used: int,
        max_tokens: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"LLM token limit exceeded: {tokens_used}/{max_tokens} tokens used"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "harness"
        evidence.add_context("tokens_used", tokens_used)
        evidence.add_context("max_tokens", max_tokens)
        super().__init__(message, ErrorCodes.LLM_TOKEN_LIMIT_EXCEEDED, evidence)


# ============================================================================
# Contract Exceptions
# ============================================================================

class ContractError(AIDBQCException):
    """Base class for contract-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.CONTRACT_VIOLATION,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class ContractViolationError(ContractError):
    """Raised when a contract constraint is violated."""

    def __init__(
        self,
        contract_level: str,  # L1, L2, or L3
        constraint: str,
        actual_value: Any,
        expected: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"{contract_level} contract violation: '{constraint}'. Expected: {expected}, Got: {actual_value}"
        error_code = {
            "L1": ErrorCodes.CONTRACT_L1_VIOLATION,
            "L2": ErrorCodes.CONTRACT_L2_VIOLATION,
        }.get(contract_level, ErrorCodes.CONTRACT_VIOLATION)

        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "contract_validator"
        evidence.add_context("contract_level", contract_level)
        evidence.add_context("constraint", constraint)
        evidence.add_context("actual_value", str(actual_value))
        evidence.add_context("expected", expected)

        super().__init__(message, error_code, evidence)


class ContractMissingError(ContractError):
    """Raised when required contract is missing."""

    def __init__(
        self,
        contract_level: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"{contract_level} contract is missing"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "contract_analyst"
        evidence.add_context("contract_level", contract_level)
        super().__init__(message, ErrorCodes.CONTRACT_MISSING, evidence)


# ============================================================================
# Test Generation Exceptions
# ============================================================================

class TestGenerationError(AIDBQCException):
    """Base class for test generation errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.TEST_GENERATION_FAILED,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class TestModeCollapseError(TestGenerationError):
    """Raised when test generation enters mode collapse."""

    def __init__(
        self,
        similarity_score: float,
        threshold: float,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Test mode collapse detected: similarity {similarity_score:.2f} exceeds threshold {threshold:.2f}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "coverage_monitor"
        evidence.add_context("similarity_score", similarity_score)
        evidence.add_context("threshold", threshold)
        super().__init__(message, ErrorCodes.TEST_MODE_COLLAPSE, evidence)


# ============================================================================
# Oracle Exceptions
# ============================================================================

class OracleError(AIDBQCException):
    """Base class for oracle-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.ORACLE_EVALUATION_FAILED,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class OracleValidationError(OracleError):
    """Raised when oracle validation fails."""

    def __init__(
        self,
        test_case_id: str,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Oracle validation failed for test case '{test_case_id}': {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "oracle"
        evidence.add_context("test_case_id", test_case_id)
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.ORACLE_VALIDATION_FAILED, evidence)


# ============================================================================
# Harness/Workflow Exceptions
# ============================================================================

class HarnessError(AIDBQCException):
    """Base class for harness/workflow errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.HARNESS_CIRCUIT_BREAKER,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class CircuitBreakerError(HarnessError):
    """Raised when circuit breaker is triggered."""

    def __init__(
        self,
        failure_type: str,  # "consecutive_failures" or "token_budget"
        current_value: int,
        threshold: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Circuit breaker triggered: {failure_type} ({current_value}/{threshold})"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "harness"
        evidence.add_context("failure_type", failure_type)
        evidence.add_context("current_value", current_value)
        evidence.add_context("threshold", threshold)
        super().__init__(message, ErrorCodes.HARNESS_CIRCUIT_BREAKER, evidence)


class RecoveryFailedError(HarnessError):
    """Raised when recovery mechanism fails."""

    def __init__(
        self,
        recovery_attempt: int,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Recovery attempt {recovery_attempt} failed: {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "agent_recovery"
        evidence.add_context("recovery_attempt", recovery_attempt)
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.HARNESS_RECOVERY_FAILED, evidence)


# ============================================================================
# Pool Exceptions
# ============================================================================

class PoolError(AIDBQCException):
    """Base class for pool-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.POOL_INITIALIZATION_FAILED,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class PoolAcquisitionError(PoolError):
    """Raised when pool acquisition fails."""

    def __init__(
        self,
        dimension: int,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Failed to acquire collection from pool for dimension {dimension}: {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "collection_pool"
        evidence.add_context("dimension", dimension)
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.POOL_ACQUISITION_FAILED, evidence)


class PoolExhaustedError(PoolError):
    """Raised when pool has no available collections."""

    def __init__(
        self,
        dimension: int,
        pool_size: int,
        in_use_count: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Pool exhausted for dimension {dimension}: {in_use_count}/{pool_size} collections in use"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "collection_pool"
        evidence.add_context("dimension", dimension)
        evidence.add_context("pool_size", pool_size)
        evidence.add_context("in_use_count", in_use_count)
        super().__init__(message, ErrorCodes.POOL_EXHAUSTED, evidence)


# ============================================================================
# Agent Exceptions
# ============================================================================

class AgentError(AIDBQCException):
    """Base class for agent-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.AGENT_FAILURE,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""

    def __init__(
        self,
        agent_name: str,
        timeout_seconds: int,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Agent '{agent_name}' timed out after {timeout_seconds} seconds"
        if evidence:
            evidence.component = f"agent_{agent_name}"
            evidence.add_context("agent_name", agent_name)
            evidence.add_context("timeout", timeout_seconds)
        super().__init__(message, ErrorCodes.AGENT_TIMEOUT, evidence)


# ============================================================================
# Telemetry Exceptions
# ============================================================================

class TelemetryError(AIDBQCException):
    """Base class for telemetry errors."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCodes.TELEMETRY_WRITE_FAILED,
        evidence: Optional[ErrorEvidence] = None
    ):
        super().__init__(message, error_code, evidence)


class TelemetryWriteError(TelemetryError):
    """Raised when telemetry write fails."""

    def __init__(
        self,
        filepath: str,
        reason: str,
        evidence: Optional[ErrorEvidence] = None
    ):
        message = f"Failed to write telemetry to '{filepath}': {reason}"
        if evidence is None:
            evidence = ErrorEvidence()
        evidence.component = "telemetry"
        evidence.add_context("filepath", filepath)
        evidence.add_context("reason", reason)
        super().__init__(message, ErrorCodes.TELEMETRY_WRITE_FAILED, evidence)


# ============================================================================
# Utility Functions
# ============================================================================

def capture_evidence(component: str = "", **context) -> ErrorEvidence:
    """
    Create ErrorEvidence with pre-populated context.

    Args:
        component: Component name
        **context: Additional context key-value pairs

    Returns:
        ErrorEvidence instance
    """
    evidence = ErrorEvidence(component=component)
    for key, value in context.items():
        evidence.add_context(key, value)
    return evidence


def raise_with_evidence(
    exception_class: type,
    message: str,
    **context
) -> None:
    """
    Raise an exception with automatic evidence capture.

    Args:
        exception_class: Exception class to raise
        message: Error message
        **context: Context key-value pairs for evidence
    """
    evidence = capture_evidence(**context)
    raise exception_class(message, evidence=evidence)
