from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FaultScenario(str, Enum):
    API_TIMEOUT = "api_timeout"
    TOOL_EXECUTION_FAILURE = "tool_execution_failure"
    MILVUS_CONNECTION_LOST = "milvus_connection_lost"
    CONTEXT_OVERFLOW = "context_overflow"
    MRE_VERIFICATION_FAILED = "mre_verification_failed"
    FALSE_POSITIVE_SUSPECTED = "false_positive_suspected"


class EscalationPolicy(str, Enum):
    LOG_AND_CONTINUE = "log_and_continue"
    ABORT = "abort"


class RecoveryResult(BaseModel):
    recovered: bool = False
    scenario: FaultScenario = FaultScenario.API_TIMEOUT
    action_taken: str = ""
    retry_count: int = 0
    escalated: bool = False
    escalation_reason: str = ""


class RecoveryRecipe(BaseModel):
    scenario: FaultScenario
    max_retries: int = 1
    retry_delay_base: float = 1.0
    escalation_policy: EscalationPolicy = EscalationPolicy.LOG_AND_CONTINUE
    recovery_fn_name: str = ""


_DEFAULT_RECIPES = {
    FaultScenario.API_TIMEOUT: RecoveryRecipe(
        scenario=FaultScenario.API_TIMEOUT,
        max_retries=3,
        retry_delay_base=2.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_api_timeout",
    ),
    FaultScenario.TOOL_EXECUTION_FAILURE: RecoveryRecipe(
        scenario=FaultScenario.TOOL_EXECUTION_FAILURE,
        max_retries=1,
        retry_delay_base=1.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_tool_failure",
    ),
    FaultScenario.MILVUS_CONNECTION_LOST: RecoveryRecipe(
        scenario=FaultScenario.MILVUS_CONNECTION_LOST,
        max_retries=2,
        retry_delay_base=5.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_milvus_connection",
    ),
    FaultScenario.CONTEXT_OVERFLOW: RecoveryRecipe(
        scenario=FaultScenario.CONTEXT_OVERFLOW,
        max_retries=1,
        retry_delay_base=0.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_context_overflow",
    ),
    FaultScenario.MRE_VERIFICATION_FAILED: RecoveryRecipe(
        scenario=FaultScenario.MRE_VERIFICATION_FAILED,
        max_retries=1,
        retry_delay_base=1.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_mre_verification",
    ),
    FaultScenario.FALSE_POSITIVE_SUSPECTED: RecoveryRecipe(
        scenario=FaultScenario.FALSE_POSITIVE_SUSPECTED,
        max_retries=0,
        retry_delay_base=0.0,
        escalation_policy=EscalationPolicy.LOG_AND_CONTINUE,
        recovery_fn_name="_recover_false_positive",
    ),
}


class TestRecoveryEngine:
    def __init__(
        self,
        recipes: Optional[dict[FaultScenario, RecoveryRecipe]] = None,
        event_emitter: Optional[Any] = None,
        db_operator: Optional[Any] = None,
        compactor: Optional[Any] = None,
    ):
        self.recipes = recipes or _DEFAULT_RECIPES
        self.event_emitter = event_emitter
        self.db_operator = db_operator
        self.compactor = compactor
        self._attempt_tracker: dict[str, int] = {}
        self._current_round: int = 0

    def set_round(self, round_num: int) -> None:
        if round_num != self._current_round:
            self._current_round = round_num
            self._attempt_tracker.clear()

    def classify_error(self, error: Exception) -> FaultScenario:
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        if "milvus" in error_str:
            return FaultScenario.MILVUS_CONNECTION_LOST
        if "connection" in error_str or "refused" in error_str:
            return FaultScenario.MILVUS_CONNECTION_LOST
        if "timeout" in error_str or "timed out" in error_str:
            return FaultScenario.API_TIMEOUT
        if "context" in error_str or "token" in error_str or "too long" in error_str or "overflow" in error_str:
            return FaultScenario.CONTEXT_OVERFLOW
        if "mre" in error_str or "mre_verify" in error_str:
            return FaultScenario.MRE_VERIFICATION_FAILED
        if "false positive" in error_str:
            return FaultScenario.FALSE_POSITIVE_SUSPECTED
        return FaultScenario.TOOL_EXECUTION_FAILURE

    def attempt_recovery(self, error: Exception, context: Optional[dict] = None) -> RecoveryResult:
        scenario = self.classify_error(error)
        recipe = self.recipes.get(scenario)
        if recipe is None:
            return RecoveryResult(
                recovered=False,
                scenario=scenario,
                action_taken="no_recipe",
                escalated=True,
                escalation_reason=f"No recovery recipe for {scenario.value}",
            )

        attempt_key = f"{scenario.value}"
        current_attempts = self._attempt_tracker.get(attempt_key, 0)

        if current_attempts >= recipe.max_retries:
            return self._escalate(scenario, recipe, "max_retries_exceeded")

        self._attempt_tracker[attempt_key] = current_attempts + 1

        delay = recipe.retry_delay_base * (2 ** current_attempts)

        recovery_fn = getattr(self, recipe.recovery_fn_name, None)
        if recovery_fn is None:
            return self._escalate(scenario, recipe, "no_recovery_function")

        try:
            action_taken = recovery_fn(error, context, delay)
            logger.info(f"Recovery attempted for {scenario.value}: {action_taken}")

            if self.event_emitter:
                from src.events import TestEvent, TestEventType, Provenance
                self.event_emitter.emit(TestEvent(
                    event_type=TestEventType.RECOVERY_ATTEMPTED,
                    data={"scenario": scenario.value, "action": action_taken, "attempt": current_attempts + 1},
                    provenance=Provenance.LIVE_TEST,
                ))

            return RecoveryResult(
                recovered=False,
                scenario=scenario,
                action_taken=action_taken,
                retry_count=current_attempts + 1,
            )
        except Exception as e:
            logger.error(f"Recovery function failed for {scenario.value}: {e}")
            return self._escalate(scenario, recipe, f"recovery_fn_error: {e}")

    def _escalate(self, scenario: FaultScenario, recipe: RecoveryRecipe, reason: str) -> RecoveryResult:
        logger.warning(f"Escalating {scenario.value}: {reason} (policy: {recipe.escalation_policy.value})")

        if recipe.escalation_policy == EscalationPolicy.ABORT:
            return RecoveryResult(
                recovered=False,
                scenario=scenario,
                action_taken="escalated_abort",
                escalated=True,
                escalation_reason=reason,
            )

        return RecoveryResult(
            recovered=False,
            scenario=scenario,
            action_taken="escalated_log_and_continue",
            escalated=True,
            escalation_reason=reason,
        )

    def reset_attempts(self, scenario: Optional[FaultScenario] = None) -> None:
        if scenario:
            self._attempt_tracker.pop(scenario.value, None)
        else:
            self._attempt_tracker.clear()

    def _recover_api_timeout(self, error: Exception, context: Optional[dict], delay: float) -> str:
        import asyncio as _asyncio
        try:
            loop = _asyncio.get_running_loop()
            loop.create_task(_asyncio.sleep(delay))
        except RuntimeError:
            pass
        return f"retry_with_backoff(delay={delay}s)"

    def _recover_tool_failure(self, error: Exception, context: Optional[dict], delay: float) -> str:
        error_str = str(error)
        if "collection" in error_str.lower() and "not found" in error_str.lower():
            return "collection_not_found_check_and_recreate"
        if "already exists" in error_str.lower():
            return "duplicate_detected_use_existing"
        return f"check_params_and_retry(delay={delay}s)"

    def _recover_milvus_connection(self, error: Exception, context: Optional[dict], delay: float) -> str:
        if self.db_operator is not None:
            try:
                self.db_operator._client = None
                logger.info("Milvus client reset, will reconnect on next operation")
            except Exception as e:
                logger.warning(f"Failed to reset Milvus client: {e}")
        return f"reconnect_and_restore(delay={delay}s)"

    def _recover_context_overflow(self, error: Exception, context: Optional[dict], delay: float) -> str:
        if self.compactor is not None:
            try:
                from src.session import TestSession
                logger.info("Context overflow detected, compactor available for forced compaction")
            except ImportError:
                pass
        return "force_compaction_and_continue"

    def _recover_mre_verification(self, error: Exception, context: Optional[dict], delay: float) -> str:
        return f"regenerate_mre_and_retry(delay={delay}s)"

    def _recover_false_positive(self, error: Exception, context: Optional[dict], delay: float) -> str:
        return "flag_for_developer_review"
