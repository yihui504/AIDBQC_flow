# Context Reset Strategy for AI-DB-QC

**Version**: 1.0.0
**Date**: 2026-03-30
**Author**: AI-DB-QC Team

---

## Overview

AI-DB-QC implements a context reset strategy based on Anthropic's best practices for long-running LLM workflows. The strategy addresses "context anxiety" - the degradation in performance when context grows too large.

---

## Problem: Context Anxiety

As LLM workflows execute over many iterations, the context window grows with:
- Test case history
- Execution results
- Oracle validation outputs
- Feedback messages
- Vector embeddings for coverage tracking

This leads to:
1. **Performance degradation** - More tokens = slower responses
2. **Quality decline** - Model may lose focus on current task
3. **Cost increase** - More tokens consumed per iteration

---

## Solution: Periodic Context Reset

The solution combines two approaches:

### 1. ResetManager - When to Reset

Triggers automatic context reset based on:

| Trigger | Condition | Config |
|--------|-----------|--------|
| **Iteration Count** | Every N iterations | `reset_interval: 5` |
| **Token Threshold** | When tokens exceed threshold | `token_threshold: 60000` |
| **Context Anxiety** | High semantic similarity in history | Automatic detection |
| **Coverage Stagnation** | Low test diversity growth | Automatic detection |

### 2. HandoffManager - What to Preserve

Uses structured artifacts to maintain continuity:

| Priority | Content | Preserved on Reset |
|----------|---------|-------------------|
| **CRITICAL** | run_id, db_config | Always |
| **HIGH** | contracts, defect_reports | Yes |
| **MEDIUM** | history_sample, iteration_count | Optional |
| **LOW** | fuzzing_feedback, external_knowledge | No |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WorkflowState                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Runtime Data (Cleared on Reset)                   │ │
│  │  - current_test_cases                              │ │
│  │  - execution_results                               │ │
│  │  - oracle_results                                  │ │
│  │  - fuzzing_feedback                                │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Preserved State (Restored via HandoffManager)      │ │
│  │  - run_id, db_config, contracts                    │ │
│  │  - defect_reports                                  │ │
│  │  - history_sample (20 vectors)                     │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    ResetManager                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  should_reset(state) → (bool, trigger)            │ │
│  │  - Checks triggers                                 │ │
│  │  - Enforces min_iterations_between_resets          │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  reset(state, trigger) → ResetMetrics             │ │
│  │  1. Create preserved snapshot                      │ │
│  │  2. Clear runtime data                             │ │
│  │  3. Restore preserved state                        │ │
│  │  4. Log telemetry                                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   HandoffManager                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  create_from_workflow_state(state)                 │ │
│  │  → List[HandoffArtifact]                          │ │
│  │                                                    │ │
│  │  Extracts state into prioritized artifacts:         │ │
│  │  - CRITICAL: run_id, db_config                     │ │
│  │  - HIGH: contracts, defect_reports                 │ │
│  │  - MEDIUM: history_sample, iteration_count         │ │
│  │  - LOW: feedback, external_knowledge               │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  restore_to_workflow_state(state, priority)        │ │
│  │  → int (count of artifacts restored)              │ │
│  │                                                    │ │
│  │  Restores artifacts at or above priority threshold │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Basic Reset Usage

```python
from src.context.reset_manager import ResetManager, ResetConfig, ResetTrigger
from src.state import WorkflowState

# Configure reset behavior
config = ResetConfig(
    reset_interval=5,           # Reset every 5 iterations
    token_threshold=60000,      # Or at 60k tokens
    keep_defect_reports=True,   # Preserve discoveries
    keep_history_sample=20,     # Keep 20 vectors for continuity
)

manager = ResetManager(config)
state = WorkflowState(run_id="test-123", iteration_count=5, ...)

# Check if reset needed
should_reset, trigger = manager.should_reset(state)
if should_reset:
    metrics = await manager.reset(state, trigger)
    print(f"Reset completed, saved {metrics.tokens_saved} tokens")
```

### Handoff Integration

```python
from src.context.handoff import HandoffManager, HandoffPriority

handoff = HandoffManager()

# Before reset: capture state as artifacts
handoff.create_from_workflow_state(state, source_agent="agent2")

# After reset: restore critical artifacts
restored = handoff.restore_to_workflow_state(
    state,
    priority_threshold=HandoffPriority.CRITICAL
)
print(f"Restored {restored} artifacts")
```

### Complete Reset Cycle

```python
async def run_iteration_with_reset(state: WorkflowState):
    reset_manager = ResetManager()
    handoff_manager = HandoffManager()

    # Check for reset
    should_reset, trigger = reset_manager.should_reset(state)

    if should_reset:
        # 1. Create handoff artifacts
        handoff_manager.create_from_workflow_state(state)

        # 2. Perform reset
        metrics = await reset_manager.reset(state, trigger)

        # 3. Restore preserved state
        handoff_manager.restore_to_workflow_state(
            state,
            priority_threshold=HandoffPriority.HIGH
        )

        print(f"Reset: saved {metrics.tokens_saved} tokens")

    # Continue with iteration...
```

---

## Configuration

### ResetConfig Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `reset_interval` | 5 | Iterations between automatic resets |
| `token_threshold` | 60000 | Reset when tokens exceed this |
| `token_budget_ratio` | 0.6 | Reset at 60% of max budget |
| `keep_defect_reports` | true | Preserve defect discoveries |
| `keep_contracts` | true | Preserve parsed contracts |
| `keep_db_config` | true | Preserve database config |
| `keep_history_sample` | 20 | Vectors to keep for coverage |
| `min_iterations_between_resets` | 2 | Minimum iterations between resets |
| `max_resets_per_session` | 10 | Safety limit |

### HandoffConfig Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `preserve_critical_artifacts` | true | Always preserve CRITICAL |
| `preserve_high_artifacts` | true | Preserve HIGH on reset |
| `preserve_medium_artifacts` | false | Preserve MEDIUM on reset |
| `preserve_low_artifacts` | false | Preserve LOW on reset |
| `compress_artifacts` | true | Compress artifact data |
| `max_artifact_size_bytes` | 10240 | Max size per artifact |
| `validate_on_handoff` | true | Validate before storage |
| `validate_on_restore` | true | Validate after restore |

---

## Metrics and Observability

### Reset Metrics

Each reset operation captures:

```python
@dataclass
class ResetMetrics:
    timestamp: datetime
    trigger: ResetTrigger
    iteration_count: int
    tokens_before_reset: int
    tokens_saved: int          # ← Token efficiency
    state_size_bytes: int
    history_vector_count: int
    reset_duration_seconds: float
    success: bool
```

### Telemetry Events

Reset operations are logged to telemetry:

```json
{
  "trace_id": "run-123",
  "timestamp": "2026-03-30T18:00:00Z",
  "node_name": "reset_manager",
  "event_type": "context_reset",
  "state_delta": {
    "trigger": "iteration_count",
    "iteration": 5,
    "tokens_before": 65000,
    "tokens_saved": 65000,
    "duration_seconds": 0.15,
    "reset_count": 1,
    "success": true
  }
}
```

### Summary Statistics

```python
summary = reset_manager.get_reset_summary()
# {
#     "total_resets": 5,
#     "successful_resets": 5,
#     "total_tokens_saved": 285000,
#     "average_duration": 0.12,
#     "success_rate": 1.0,
#     "trigger_counts": {
#         "iteration_count": 4,
#         "token_threshold": 1,
#         ...
#     }
# }
```

---

## Best Practices

### 1. Choose Appropriate Reset Interval

- **Short intervals (3-5)**: For high-iteration workflows where context grows quickly
- **Long intervals (10+)**: For workflows where continuity is critical

### 2. Preserve the Right State

```python
# For bug hunting - keep discoveries
config = ResetConfig(
    keep_defect_reports=True,
    keep_history_sample=20  # Maintain coverage tracking
)

# For contract validation - keep contracts
config = ResetConfig(
    keep_contracts=True,
    keep_defect_reports=False  # Fresh discovery each cycle
)
```

### 3. Monitor Token Efficiency

```python
summary = reset_manager.get_reset_summary()
tokens_per_reset = summary["total_tokens_saved"] / summary["total_resets"]

if tokens_per_reset < 10000:
    # Resets not saving much - consider increasing interval
    config.reset_interval += 2
```

### 4. Handle Reset Failures

```python
try:
    metrics = await reset_manager.reset(state, trigger)
except ResetFailedError as e:
    logger.error(f"Reset failed: {e.reason}")
    # Decide whether to continue or abort
    if e.iteration < max_iterations:
        # Continue without reset
        pass
    else:
        # Abort - too risky
        raise
```

---

## Integration with LangGraph

The reset strategy integrates with the LangGraph workflow:

```python
from src.graph import should_continue, route_after_oracle

# In your graph nodes:
async def agent2_generator(state: WorkflowState):
    # Check for reset before generation
    reset_manager = state.metadata["reset_manager"]
    should_reset, trigger = reset_manager.should_reset(state)

    if should_reset:
        handoff = state.metadata["handoff_manager"]
        handoff.create_from_workflow_state(state)
        await reset_manager.reset(state, trigger)
        handoff.restore_to_workflow_state(state)

    # Continue with generation...
```

---

## Troubleshooting

### Reset Not Triggering

**Problem**: Reset not happening at expected interval.

**Check**:
```python
# Verify iteration delta
iteration_delta = state.iteration_count - reset_manager.last_reset_iteration
print(f"Iteration delta: {iteration_delta}")
print(f"Min required: {reset_manager.config.min_iterations_between_resets}")
```

### State Lost After Reset

**Problem**: Expected state not preserved.

**Check**:
```python
# Verify artifact creation
artifacts = handoff.create_from_workflow_state(state)
print(f"Created {len(artifacts)} artifacts")

# Verify restoration
restored = handoff.restore_to_workflow_state(state)
print(f"Restored {restored} artifacts")
```

### Token Savings Low

**Problem**: Resets not saving expected tokens.

**Check**:
- Token threshold may be too low
- Reset interval may be too short
- Check `tokens_saved` in metrics

---

## API Reference

### ResetManager

| Method | Description |
|--------|-------------|
| `should_reset(state, trigger=None)` | Check if reset needed |
| `reset(state, trigger)` | Perform context reset |
| `register_callback(callback)` | Register post-reset callback |
| `get_reset_summary()` | Get reset statistics |

### HandoffManager

| Method | Description |
|--------|-------------|
| `create_artifact(key, value, priority, ...)` | Create handoff artifact |
| `get_artifact(key)` | Retrieve artifact |
| `list_artifacts(priority, source_agent)` | List artifacts |
| `create_from_workflow_state(state)` | Extract artifacts from state |
| `restore_to_workflow_state(state, priority)` | Restore artifacts to state |
| `export_artifacts(priority_threshold)` | Export to JSON |
| `import_artifacts(json_data)` | Import from JSON |

---

## Changelog

### Version 1.0.0 (2026-03-30)
- Initial implementation
- ResetManager with multiple triggers
- HandoffManager with artifact prioritization
- Complete test coverage (29 tests)
- Telemetry integration
