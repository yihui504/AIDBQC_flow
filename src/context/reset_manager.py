"""
Context Reset Manager for AI-DB-QC

Implements periodic context reset strategy based on Anthropic's best practices:
- Reset every N iterations to prevent "context anxiety"
- Token-based thresholds for efficiency
- State preservation across resets

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.state import WorkflowState
from src.exceptions import ErrorCodes, capture_evidence
from src.telemetry import TelemetryLogger, TelemetryEvent


class ResetStrategy(str, Enum):
    """Context reset strategies."""

    PERIODIC = "periodic"  # Reset every N iterations
    TOKEN_BASED = "token_based"  # Reset when token threshold reached
    ADAPTIVE = "adaptive"  # Reset based on context health metrics
    MANUAL = "manual"  # Manual reset trigger


class ResetTrigger(str, Enum):
    """Events that can trigger a context reset."""

    ITERATION_COUNT = "iteration_count"
    TOKEN_THRESHOLD = "token_threshold"
    CONTEXT_ANXIETY = "context_anxiety"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MANUAL_REQUEST = "manual_request"
    COVERAGE_STAGNATION = "coverage_stagnation"


@dataclass
class ResetMetrics:
    """Metrics collected before and after reset."""

    timestamp: datetime = field(default_factory=datetime.now)
    trigger: ResetTrigger = ResetTrigger.MANUAL_REQUEST
    iteration_count: int = 0
    tokens_before_reset: int = 0
    tokens_saved: int = 0
    state_size_bytes: int = 0
    history_vector_count: int = 0
    test_case_count: int = 0
    reset_duration_seconds: float = 0.0
    success: bool = True
    error_message: str = ""


class ResetConfig(BaseModel):
    """Configuration for context reset behavior."""

    # Reset triggers
    reset_interval: int = Field(default=5, description="Reset every N iterations")
    token_threshold: int = Field(default=60000, description="Reset when tokens exceed this threshold")
    token_budget_ratio: float = Field(default=0.6, description="Reset at 60% of max budget")

    # State preservation
    keep_defect_reports: bool = Field(default=True, description="Preserve defect reports across resets")
    keep_contracts: bool = Field(default=True, description="Preserve parsed contracts")
    keep_db_config: bool = Field(default=True, description="Preserve database configuration")
    keep_history_sample: int = Field(default=20, description="Number of history vectors to keep")

    # Adaptive thresholds
    context_anxiety_threshold: float = Field(default=0.85, description="Context similarity threshold for anxiety")
    coverage_stagnation_iterations: int = Field(default=3, description="Iterations without new coverage")

    # Safety limits
    min_iterations_between_resets: int = Field(default=2, description="Minimum iterations before allowing reset")
    max_resets_per_session: int = Field(default=10, description="Maximum resets in a single session")


class ResetManager:
    """
    Manages context reset operations for the AI-DB-QC workflow.

    Based on Anthropic's harness design principles:
    1. Reset context periodically to maintain performance
    2. Use structured state (WorkflowState) for handoff
    3. Track token efficiency
    4. Preserve critical state across resets
    """

    def __init__(
        self,
        config: Optional[ResetConfig] = None,
        telemetry_logger: Optional[TelemetryLogger] = None
    ):
        self.config = config or ResetConfig()
        self.telemetry = telemetry_logger or TelemetryLogger()
        self.reset_count = 0
        self.last_reset_iteration = 0
        self.reset_history: List[ResetMetrics] = []
        self._reset_callbacks: List[Callable[[WorkflowState, ResetMetrics], None]] = []

    def should_reset(
        self,
        state: WorkflowState,
        trigger_check: Optional[ResetTrigger] = None
    ) -> Tuple[bool, Optional[ResetTrigger]]:
        """
        Check if a context reset should be triggered.

        Args:
            state: Current workflow state
            trigger_check: Specific trigger to check, or None to check all

        Returns:
            (should_reset, trigger) tuple
        """
        iteration_delta = state.iteration_count - self.last_reset_iteration

        # Check minimum iterations between resets
        if iteration_delta < self.config.min_iterations_between_resets:
            return False, None

        # Check max resets per session
        if self.reset_count >= self.config.max_resets_per_session:
            return False, None

        # Check specific trigger or all triggers
        triggers_to_check = [trigger_check] if trigger_check else [
            ResetTrigger.ITERATION_COUNT,
            ResetTrigger.TOKEN_THRESHOLD,
            ResetTrigger.CONTEXT_ANXIETY,
            ResetTrigger.COVERAGE_STAGNATION,
        ]

        for trigger in triggers_to_check:
            if self._check_trigger(state, trigger, iteration_delta):
                # Mark this iteration as having been checked for reset
                # This prevents repeated detections without calling reset()
                self.last_reset_iteration = state.iteration_count
                return True, trigger

        return False, None

    def _check_trigger(
        self,
        state: WorkflowState,
        trigger: ResetTrigger,
        iteration_delta: int
    ) -> bool:
        """Check if a specific trigger condition is met."""

        if trigger == ResetTrigger.ITERATION_COUNT:
            return iteration_delta >= self.config.reset_interval

        elif trigger == ResetTrigger.TOKEN_THRESHOLD:
            token_budget_trigger = state.max_token_budget * self.config.token_budget_ratio
            return state.total_tokens_used >= max(
                self.config.token_threshold,
                token_budget_trigger
            )

        elif trigger == ResetTrigger.CONTEXT_ANXIETY:
            return self._detect_context_anxiety(state)

        elif trigger == ResetTrigger.COVERAGE_STAGNATION:
            return self._detect_coverage_stagnation(state)

        return False

    def _detect_context_anxiety(self, state: WorkflowState) -> bool:
        """Detect context anxiety through semantic similarity of history vectors."""
        if len(state.history_vectors) < 10:
            return False

        # Simple heuristic: if many vectors are very similar, we have anxiety
        # In production, this would use actual cosine similarity
        # For now, use history vector count as a proxy
        return len(state.history_vectors) > 100

    def _detect_coverage_stagnation(self, state: WorkflowState) -> bool:
        """Detect if test coverage has stagnated."""
        # Check if we're generating similar tests (using history vector growth)
        # Only check after we've done enough iterations to establish a pattern
        if state.iteration_count <= self.config.coverage_stagnation_iterations:
            return False

        # Simple heuristic: if iteration_count is high but history hasn't grown much
        expected_min_history = state.iteration_count * 5
        return len(state.history_vectors) < expected_min_history

    async def reset(
        self,
        state: WorkflowState,
        trigger: ResetTrigger = ResetTrigger.MANUAL_REQUEST
    ) -> ResetMetrics:
        """
        Perform a context reset operation.

        Args:
            state: Current workflow state to reset
            trigger: What triggered this reset

        Returns:
            ResetMetrics with details of the reset operation
        """
        start_time = datetime.now()
        metrics = ResetMetrics(
            trigger=trigger,
            iteration_count=state.iteration_count,
            tokens_before_reset=state.total_tokens_used,
            history_vector_count=len(state.history_vectors),
            test_case_count=len(state.current_test_cases)
        )

        try:
            # Create preserved state snapshot
            preserved = self._create_preserved_state(state)

            # Perform the reset
            self._do_reset(state)

            # Restore preserved state
            self._restore_preserved_state(state, preserved)

            # Calculate metrics
            metrics.tokens_saved = metrics.tokens_before_reset - state.total_tokens_used
            metrics.reset_duration_seconds = (datetime.now() - start_time).total_seconds()
            metrics.success = True

            # Update tracking
            self.reset_count += 1
            self.last_reset_iteration = state.iteration_count
            self.reset_history.append(metrics)

            # Log telemetry
            await self._log_reset_event(state, metrics)

            # Notify callbacks
            self._notify_callbacks(state, metrics)

            return metrics

        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            metrics.reset_duration_seconds = (datetime.now() - start_time).total_seconds()

            evidence = capture_evidence(
                component="reset_manager",
                trigger=trigger.value,
                iteration=state.iteration_count
            )
            raise ResetFailedError(
                iteration=state.iteration_count,
                reason=str(e),
                evidence=evidence
            )

    def _create_preserved_state(self, state: WorkflowState) -> Dict[str, Any]:
        """Create snapshot of state to preserve across reset."""
        preserved: Dict[str, Any] = {}

        if self.config.keep_defect_reports:
            preserved["defect_reports"] = state.defect_reports.copy()

        if self.config.keep_contracts:
            preserved["contracts"] = state.contracts

        if self.config.keep_db_config:
            preserved["db_config"] = state.db_config

        # Keep sample of history vectors for coverage continuity
        if state.history_vectors:
            sample_size = min(self.config.keep_history_sample, len(state.history_vectors))
            preserved["history_sample"] = state.history_vectors[-sample_size:]

        # Preserve critical metadata
        preserved["run_id"] = state.run_id
        preserved["iteration_count"] = state.iteration_count
        preserved["max_iterations"] = state.max_iterations
        preserved["target_db_input"] = state.target_db_input

        return preserved

    def _do_reset(self, state: WorkflowState):
        """Perform the actual reset operation."""
        # Clear verbose runtime data
        state.current_test_cases.clear()
        state.execution_results.clear()
        state.oracle_results.clear()

        # Reset counters (but preserve iteration_count as it tracks progress)
        state.total_tokens_used = 0
        state.consecutive_failures = 0

        # Clear history vectors (will be restored with sample if configured)
        state.history_vectors.clear()

        # Clear verbose feedback
        state.fuzzing_feedback = ""

    def _restore_preserved_state(self, state: WorkflowState, preserved: Dict[str, Any]):
        """Restore preserved state after reset."""
        if "defect_reports" in preserved:
            state.defect_reports = preserved["defect_reports"]

        if "contracts" in preserved:
            state.contracts = preserved["contracts"]

        if "db_config" in preserved:
            state.db_config = preserved["db_config"]

        if "history_sample" in preserved:
            state.history_vectors = preserved["history_sample"]

        # Always preserve critical metadata
        state.run_id = preserved["run_id"]
        state.iteration_count = preserved["iteration_count"]
        state.max_iterations = preserved["max_iterations"]
        state.target_db_input = preserved["target_db_input"]

    async def _log_reset_event(self, state: WorkflowState, metrics: ResetMetrics):
        """Log reset event to telemetry."""
        event = TelemetryEvent(
            trace_id=state.run_id,
            node_name="reset_manager",
            event_type="context_reset",
            state_delta={
                "trigger": metrics.trigger.value,
                "iteration": metrics.iteration_count,
                "tokens_before": metrics.tokens_before_reset,
                "tokens_saved": metrics.tokens_saved,
                "duration_seconds": metrics.reset_duration_seconds,
                "reset_count": self.reset_count,
                "success": metrics.success,
            }
        )
        self.telemetry.log_event(event)

    def _notify_callbacks(self, state: WorkflowState, metrics: ResetMetrics):
        """Notify registered callbacks of reset completion."""
        for callback in self._reset_callbacks:
            try:
                callback(state, metrics)
            except Exception:
                pass  # Don't let callback failures break reset

    def register_callback(self, callback: Callable[[WorkflowState, ResetMetrics], None]):
        """Register a callback to be called after each reset."""
        self._reset_callbacks.append(callback)

    def get_reset_summary(self) -> Dict[str, Any]:
        """Get summary of all reset operations."""
        if not self.reset_history:
            return {
                "total_resets": 0,
                "total_tokens_saved": 0,
                "average_duration": 0.0,
                "success_rate": 1.0
            }

        successful = [m for m in self.reset_history if m.success]
        return {
            "total_resets": len(self.reset_history),
            "successful_resets": len(successful),
            "total_tokens_saved": sum(m.tokens_saved for m in successful),
            "average_duration": sum(m.reset_duration_seconds for m in self.reset_history) / len(self.reset_history),
            "success_rate": len(successful) / len(self.reset_history),
            "trigger_counts": {
                trigger.value: sum(1 for m in self.reset_history if m.trigger == trigger)
                for trigger in ResetTrigger
            }
        }


# Exception for reset failures
class ResetFailedError(Exception):
    """Raised when context reset fails."""

    def __init__(self, iteration: int, reason: str, evidence=None):
        self.iteration = iteration
        self.reason = reason
        self.evidence = evidence
        super().__init__(f"Reset failed at iteration {iteration}: {reason}")
