# Exception Handling Guide for AI-DB-QC

**Version**: 1.0.0
**Date**: 2026-03-30
**Author**: AI-DB-QC Team

---

## Overview

AI-DB-QC uses a structured exception hierarchy with:
- **Clear categorization** of error types
- **Evidence tracking** for debugging
- **Error codes** for programmatic handling
- **Human-readable messages**

---

## Exception Hierarchy

```
AIDBQCException (Base)
├── ConfigurationError
│   ├── ConfigurationMissingError
│   └── ConfigurationValidationError
├── DatabaseError
│   ├── DatabaseConnectionError
│   ├── DatabaseTimeoutError
│   ├── DatabaseQueryError
│   └── DatabaseCollectionNotFoundError
├── LLMError
│   ├── LLMRateLimitError
│   ├── LLMTimeoutError
│   └── LLMTokenLimitError
├── ContractError
│   ├── ContractViolationError (L1/L2/L3)
│   ├── ContractMissingError
│   └── ContractInvalidError
├── TestGenerationError
│   └── TestModeCollapseError
├── OracleError
│   └── OracleValidationError
├── HarnessError
│   ├── CircuitBreakerError
│   └── RecoveryFailedError
├── PoolError
│   ├── PoolAcquisitionError
│   └── PoolExhaustedError
├── AgentError
│   └── AgentTimeoutError
└── TelemetryError
    └── TelemetryWriteError
```

---

## Usage Examples

### Basic Exception Raising

```python
from src.exceptions import DatabaseConnectionError, capture_evidence

# Create evidence
evidence = capture_evidence(
    component="milvus_adapter",
    host="localhost",
    port=19530
)

# Raise exception with evidence
raise DatabaseConnectionError("localhost", 19530, "Connection refused", evidence)
```

### Catching Specific Exceptions

```python
from src.exceptions import DatabaseError, DatabaseConnectionError

try:
    adapter.connect()
except DatabaseConnectionError as e:
    # Handle connection error specifically
    logger.error(f"Failed to connect: {e.to_dict()}")
    raise
except DatabaseError as e:
    # Handle any database error
    logger.error(f"Database error: {e.error_code}")
    raise
```

### Using raise_with_evidence

```python
from src.exceptions import raise_with_evidence, ConfigurationError

# Automatically creates evidence with context
raise_with_evidence(
    ConfigurationError,
    "Invalid configuration value",
    config_key="MAX_TOKENS",
    invalid_value=999999,
    expected="<= 100000"
)
```

### Exception Chaining

```python
try:
    # Some operation that might fail
    risky_operation()
except Exception as e:
    # Preserve original exception as cause
    from src.exceptions import DatabaseQueryError, capture_evidence
    evidence = capture_evidence(component="executor", original_error=str(e))
    raise DatabaseQueryError("SELECT * FROM test", str(e), evidence) from e
```

---

## Error Evidence

### Creating Evidence

```python
from src.exceptions import ErrorEvidence

evidence = ErrorEvidence(component="my_component")

# Add context
evidence.add_context("user_id", 12345)
evidence.add_context("action", "search")

# Add stack trace
import traceback
evidence.stack_trace = traceback.format_exc()

# Convert to dict for logging
data = evidence.to_dict()
```

### Evidence Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | datetime | When the error occurred |
| `component` | str | Which component raised the error |
| `context` | dict | Key-value context information |
| `stack_trace` | str | Python stack trace |
| `related_data` | dict | Additional diagnostic data |

---

## Error Codes

### Format: `Ennn`

- `E001-E099`: Configuration Errors
- `E100-E199`: Database Errors
- `E200-E299`: LLM Errors
- `E300-E399`: Contract Errors
- `E400-E499`: Test Generation Errors
- `E500-E599`: Oracle Errors
- `E600-E699`: Harness/Workflow Errors
- `E700-E799`: Pool Errors
- `E800-E899`: Agent Errors
- `E900-E999`: Telemetry Errors

See `docs/error_codes.md` for complete listing.

---

## Best Practices

### 1. Always Use Specific Exception Types

**❌ Bad:**
```python
raise Exception("Database error")
```

**✅ Good:**
```python
from src.exceptions import DatabaseConnectionError
raise DatabaseConnectionError("localhost", 19530, "Connection refused")
```

### 2. Include Evidence for Debugging

**❌ Bad:**
```python
raise DatabaseError("Query failed")
```

**✅ Good:**
```python
evidence = capture_evidence(
    component="executor",
    query="SELECT * FROM test",
    error_code="Syntax error"
)
raise DatabaseQueryError("SELECT * FROM test", "Syntax error", evidence)
```

### 3. Use Error Codes for Programmatic Handling

```python
from src.exceptions import ErrorCodes, LLMRateLimitError

try:
    llm_client.generate(prompt)
except LLMRateLimitError as e:
    if e.error_code == ErrorCodes.LLM_RATE_LIMIT_EXCEEDED:
        # Implement retry with backoff
        time.sleep(60)
        retry()
```

### 4. Log Exception Details

```python
import logging

try:
    adapter.search(query)
except DatabaseError as e:
    # Log full exception details
    logging.error(f"Database error: {e.to_dict()}", exc_info=True)
    raise
```

### 5. Provide Context in Evidence

```python
from src.exceptions import capture_evidence

evidence = capture_evidence(
    component="agent2_generator",
    agent_name="Test Generator",
    iteration=5,
    current_state={"tokens_used": 50000}
)
raise TestGenerationError("Generation failed", evidence=evidence)
```

---

## Common Patterns

### Pattern 1: Database Operation with Retry

```python
from src.exceptions import DatabaseConnectionError, DatabaseTimeoutError

MAX_RETRIES = 3

def execute_with_retry(query):
    for attempt in range(MAX_RETRIES):
        try:
            return adapter.execute(query)
        except DatabaseConnectionError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

### Pattern 2: LLM Call with Token Budget

```python
from src.exceptions import LLMTokenLimitError, capture_evidence

def llm_call_with_budget_check(prompt):
    config = get_config()
    current_tokens = get_token_usage()

    if current_tokens >= config.harness.max_token_budget:
        evidence = capture_evidence(
            component="harness",
            tokens_used=current_tokens,
            max_tokens=config.harness.max_token_budget
        )
        raise LLMTokenLimitError(current_tokens, config.harness.max_token_budget, evidence)

    return llm_client.generate(prompt)
```

### Pattern 3: Contract Validation

```python
from src.exceptions import ContractViolationError, capture_evidence

def validate_dimension(dimension):
    MAX_DIMENSION = 2048

    if dimension > MAX_DIMENSION:
        evidence = capture_evidence(
            component="contract_validator",
            test_case_id="test-001",
            provided_value=dimension
        )
        raise ContractViolationError(
            "L1", "dimension", dimension, f"<= {MAX_DIMENSION}", evidence
        )
```

### Pattern 4: Pool Acquisition with Timeout

```python
from src.exceptions import PoolAcquisitionError, PoolExhaustedError, capture_evidence
import asyncio

async def acquire_with_timeout(pool, dimension, timeout=30):
    try:
        return await asyncio.wait_for(
            pool.acquire(dimension),
            timeout=timeout
        )
    except asyncio.TimeoutError as e:
        evidence = capture_evidence(
            component="collection_pool",
            dimension=dimension,
            timeout=timeout
        )
        raise PoolAcquisitionError(dimension, "Acquisition timeout", evidence)
```

---

## Integration with Logging

### Structured Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

try:
    adapter.connect()
except DatabaseConnectionError as e:
    # Log structured error
    logger.error(
        "Database connection failed",
        extra={
            "error_code": e.error_code,
            "component": e.evidence.component,
            "context": e.evidence.context
        }
    )
```

### Exception to Dict Conversion

```python
try:
    risky_operation()
except AIDBQCException as e:
    # Convert to dict for JSON logging
    error_dict = e.to_dict()
    print(json.dumps(error_dict, indent=2))
```

---

## Testing with Exceptions

### Testing Exception Raising

```python
import pytest
from src.exceptions import DatabaseConnectionError

def test_database_connection_failure():
    with pytest.raises(DatabaseConnectionError) as exc_info:
        raise DatabaseConnectionError("localhost", 19530, "Connection refused")

    assert exc_info.value.error_code == "E100"
    assert "localhost" in str(exc_info.value)
```

### Testing Evidence

```python
def test_evidence_tracking():
    evidence = ErrorEvidence(component="test")
    evidence.add_context("key", "value")

    exc = DatabaseConnectionError("localhost", 19530, "Error", evidence)

    assert exc.evidence.component == "test"
    assert exc.evidence.context["key"] == "value"
```

---

## Migration Guide

### From Generic Exceptions

**Before:**
```python
# Old code with generic exceptions
try:
    result = database.search(query)
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

**After:**
```python
# New code with specific exceptions
from src.exceptions import DatabaseQueryError, capture_evidence

try:
    result = database.search(query)
except DatabaseQueryError as e:
    logger.error(f"Database error: {e.to_dict()}")
    raise
except Exception as e:
    # Catch-all for unexpected errors
    logger.error(f"Unexpected error: {e}")
    raise
```

---

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `AIDBQCException` | Base exception for all AI-DB-QC errors |
| `ErrorEvidence` | Structured evidence for error diagnosis |
| `ErrorCodes` | Central registry of error codes |

### Category Base Classes

| Class | Category |
|-------|----------|
| `ConfigurationError` | Configuration errors (E001-E099) |
| `DatabaseError` | Database errors (E100-E199) |
| `LLMError` | LLM errors (E200-E299) |
| `ContractError` | Contract errors (E300-E399) |
| `TestGenerationError` | Test generation errors (E400-E499) |
| `OracleError` | Oracle errors (E500-E599) |
| `HarnessError` | Harness/workflow errors (E600-E699) |
| `PoolError` | Pool errors (E700-E799) |
| `AgentError` | Agent errors (E800-E899) |
| `TelemetryError` | Telemetry errors (E900-E999) |

### Utility Functions

| Function | Description |
|----------|-------------|
| `capture_evidence(component, **context)` | Create ErrorEvidence with context |
| `raise_with_evidence(exc_class, message, **context)` | Raise exception with automatic evidence capture |

---

## Changelog

### Version 1.0.0 (2026-03-30)
- Initial exception hierarchy
- Evidence tracking support
- Error codes registry
- Complete documentation
