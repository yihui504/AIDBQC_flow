# AI-DB-QC Error Codes Registry

**Version**: 1.0.0
**Date**: 2026-03-30
**Author**: AI-DB-QC Team

---

## Error Code Format

Error codes follow the format: `Ennn`
- `E`: Prefix for Error
- `nnn`: Three-digit number (001-999)

---

## Error Code Categories

### E001-E099: Configuration Errors

| Code | Name | Description |
|------|------|-------------|
| E001 | CONFIG_INVALID | Invalid configuration value |
| E002 | CONFIG_MISSING | Required configuration is missing |
| E003 | CONFIG_VALIDATION_FAILED | Configuration validation failed |

**Example:**
```
[E002] Required configuration key 'LLM_API_KEY' is missing
```

### E100-E199: Database Errors

| Code | Name | Description |
|------|------|-------------|
| E100 | DATABASE_CONNECTION_FAILED | Failed to connect to database |
| E101 | DATABASE_TIMEOUT | Database operation timed out |
| E102 | DATABASE_QUERY_FAILED | Database query execution failed |
| E103 | DATABASE_INSERT_FAILED | Data insertion failed |
| E104 | DATABASE_DELETE_FAILED | Data deletion failed |
| E105 | DATABASE_COLLECTION_NOT_FOUND | Collection not found |
| E106 | DATABASE_INDEX_ERROR | Index operation failed |

**Example:**
```
[E100] Failed to connect to database at localhost:19530. Reason: Connection refused
```

### E200-E299: LLM Errors

| Code | Name | Description |
|------|------|-------------|
| E200 | LLM_API_ERROR | LLM API returned an error |
| E201 | LLM_RATE_LIMIT_EXCEEDED | API rate limit exceeded |
| E202 | LLM_TIMEOUT | LLM request timed out |
| E203 | LLM_INVALID_RESPONSE | Invalid response from LLM |
| E204 | LLM_TOKEN_LIMIT_EXCEEDED | Token budget exceeded |

**Example:**
```
[E201] LLM rate limit exceeded for provider 'anthropic'. Retry after 60 seconds
```

### E300-E399: Contract Errors

| Code | Name | Description |
|------|------|-------------|
| E300 | CONTRACT_VIOLATION | General contract violation |
| E301 | CONTRACT_L1_VIOLATION | L1 (API) contract violation |
| E302 | CONTRACT_L2_VIOLATION | L2 (Semantic) contract violation |
| E303 | CONTRACT_MISSING | Contract is missing |
| E304 | CONTRACT_INVALID | Contract is invalid |

**Example:**
```
[E301] L1 contract violation: 'dimension'. Expected: int <= 2048, Got: 4096
```

### E400-E499: Test Generation Errors

| Code | Name | Description |
|------|------|-------------|
| E400 | TEST_GENERATION_FAILED | Test generation failed |
| E401 | TEST_VALIDATION_FAILED | Test validation failed |
| E402 | TEST_EXECUTION_FAILED | Test execution failed |
| E403 | TEST_MODE_COLLAPSE | Mode collapse detected |

**Example:**
```
[E403] Test mode collapse detected: similarity 0.95 exceeds threshold 0.90
```

### E500-E599: Oracle Errors

| Code | Name | Description |
|------|------|-------------|
| E500 | ORACLE_EVALUATION_FAILED | Oracle evaluation failed |
| E501 | ORACLE_VALIDATION_FAILED | Oracle validation failed |
| E502 | ORACLE_INCONCLUSIVE_RESULT | Oracle result inconclusive |

**Example:**
```
[E501] Oracle validation failed for test case 'test-001': Semantic drift detected
```

### E600-E699: Harness/Workflow Errors

| Code | Name | Description |
|------|------|-------------|
| E600 | HARNESS_CIRCUIT_BREAKER | Circuit breaker triggered |
| E601 | HARNESS_RECOVERY_FAILED | Recovery mechanism failed |
| E602 | HARNESS_STATE_CORRUPTION | Workflow state corruption |
| E603 | HARNESS_MAX_ITERATIONS_EXCEEDED | Max iterations exceeded |

**Example:**
```
[E600] Circuit breaker triggered: consecutive_failures (3/3)
```

### E700-E799: Pool Errors

| Code | Name | Description |
|------|------|-------------|
| E700 | POOL_INITIALIZATION_FAILED | Pool initialization failed |
| E701 | POOL_ACQUISITION_FAILED | Pool acquisition failed |
| E702 | POOL_RELEASE_FAILED | Pool release failed |
| E703 | POOL_EXHAUSTED | Pool exhausted (no available collections) |

**Example:**
```
[E703] Pool exhausted for dimension 128: 10/10 collections in use
```

### E800-E899: Agent Errors

| Code | Name | Description |
|------|------|-------------|
| E800 | AGENT_TIMEOUT | Agent execution timeout |
| E801 | AGENT_FAILURE | General agent failure |
| E802 | AGENT_INVALID_RESPONSE | Agent returned invalid response |

**Example:**
```
[E800] Agent 'agent2_generator' timed out after 90 seconds
```

### E900-E999: Telemetry Errors

| Code | Name | Description |
|------|------|-------------|
| E900 | TELEMETRY_WRITE_FAILED | Telemetry write failed |
| E901 | TELEMETRY_FILE_ERROR | Telemetry file error |

**Example:**
```
[E900] Failed to write telemetry to '.trae/runs/telemetry.jsonl': Permission denied
```

---

## Error Handling Best Practices

### 1. Always Include Evidence

```python
from src.exceptions import DatabaseConnectionError, capture_evidence

evidence = capture_evidence(
    component="milvus_adapter",
    host="localhost",
    port=19530,
    reason="Connection refused"
)
raise DatabaseConnectionError("localhost", 19530, "Connection refused", evidence)
```

### 2. Use Specific Exception Types

```python
# ❌ Bad: Generic exception
raise Exception("Database error")

# ✅ Good: Specific exception
from src.exceptions import DatabaseQueryError
raise DatabaseQueryError("SELECT * FROM test", "Syntax error", evidence)
```

### 3. Chain Exceptions

```python
try:
    adapter.connect()
except Exception as e:
    from src.exceptions import DatabaseConnectionError, capture_evidence
    evidence = capture_evidence(component="adapter", original_error=str(e))
    raise DatabaseConnectionError("localhost", 19530, str(e), evidence) from e
```

### 4. Log Exception Details

```python
import logging

try:
    result = adapter.search(query)
except DatabaseQueryError as e:
    logging.error(f"Database error: {e.to_dict()}")
    raise
```

---

## Adding New Error Codes

To add a new error code:

1. **Define the code in ErrorCodes class:**
   ```python
   class ErrorCodes:
       YOUR_NEW_ERROR = "E999"
   ```

2. **Create corresponding exception class:**
   ```python
   class YourNewError(AIDBQCException):
       def __init__(self, message, evidence=None):
           super().__init__(message, ErrorCodes.YOUR_NEW_ERROR, evidence)
   ```

3. **Update this registry document**

---

## Error Code Assignment Guidelines

- **001-099**: Generic/framework errors
- **100-199**: External system integrations (database, APIs)
- **200-299**: AI/ML model interactions
- **300-399**: Contract and validation
- **400-499**: Test generation and execution
- **500-599**: Analysis and oracles
- **600-699**: Workflow and orchestration
- **700-799**: Resource management (pools, connections)
- **800-899**: Agent operations
- **900-999**: Observability and telemetry
