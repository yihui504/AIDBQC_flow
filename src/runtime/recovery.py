from __future__ import annotations

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    API_TIMEOUT = "api_timeout"
    TOOL_EXECUTION_FAILURE = "tool_execution_failure"
    DB_CONNECTION_LOST = "db_connection_lost"
    CONTEXT_OVERFLOW = "context_overflow"
    POLICY_BLOCKED = "policy_blocked"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    retry: bool = False
    max_retries: int = 0
    base_delay: float = 1.0
    reset_adapter: bool = False
    notify_agent: bool = False
    skip_round: bool = False


@dataclass
class RecoveryResult:
    action_taken: str
    should_retry: bool
    delay: float = 0.0
    message: str = ""


_RECOVERY_POLICIES: dict[ErrorCategory, RecoveryAction] = {
    ErrorCategory.API_TIMEOUT: RecoveryAction(retry=True, max_retries=3, base_delay=1.0, notify_agent=True),
    ErrorCategory.TOOL_EXECUTION_FAILURE: RecoveryAction(retry=True, max_retries=1, base_delay=0.5, notify_agent=True),
    ErrorCategory.DB_CONNECTION_LOST: RecoveryAction(retry=True, max_retries=2, base_delay=2.0, reset_adapter=True, notify_agent=True),
    ErrorCategory.CONTEXT_OVERFLOW: RecoveryAction(retry=True, max_retries=1, base_delay=0.0, notify_agent=True),
    ErrorCategory.POLICY_BLOCKED: RecoveryAction(retry=False, notify_agent=True),
    ErrorCategory.RATE_LIMITED: RecoveryAction(retry=True, max_retries=3, base_delay=5.0, notify_agent=True),
    ErrorCategory.UNKNOWN: RecoveryAction(retry=True, max_retries=1, base_delay=1.0, notify_agent=True),
}


def classify_error(error: Exception) -> ErrorCategory:
    error_msg = str(error).lower()
    if "timeout" in error_msg or "timed out" in error_msg:
        return ErrorCategory.API_TIMEOUT
    if "connection" in error_msg or "refused" in error_msg or "unreachable" in error_msg:
        return ErrorCategory.DB_CONNECTION_LOST
    if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
        return ErrorCategory.RATE_LIMITED
    if "context" in error_msg and ("overflow" in error_msg or "too long" in error_msg or "exceed" in error_msg):
        return ErrorCategory.CONTEXT_OVERFLOW
    if "policy" in error_msg or "blocked" in error_msg or "skip" in error_msg:
        return ErrorCategory.POLICY_BLOCKED
    if "tool" in error_msg and ("execution" in error_msg or "failed" in error_msg):
        return ErrorCategory.TOOL_EXECUTION_FAILURE
    return ErrorCategory.UNKNOWN


class RecoveryStrategy:
    def __init__(self, adapter_reset_fn: Optional[Callable] = None, compact_fn: Optional[Callable] = None):
        self._adapter_reset_fn = adapter_reset_fn
        self._compact_fn = compact_fn
        self._retry_counts: dict[ErrorCategory, int] = {}
        self._total_retries: dict[ErrorCategory, int] = {}

    async def recover(self, error: Exception) -> RecoveryResult:
        category = classify_error(error)
        policy = _RECOVERY_POLICIES.get(category, _RECOVERY_POLICIES[ErrorCategory.UNKNOWN])
        current_retries = self._retry_counts.get(category, 0)
        total = self._total_retries.get(category, 0)

        if policy.retry and current_retries < policy.max_retries and total < policy.max_retries * 3:
            self._retry_counts[category] = current_retries + 1
            self._total_retries[category] = total + 1
            delay = policy.base_delay * (2 ** current_retries)

            if policy.reset_adapter and self._adapter_reset_fn:
                try:
                    await self._adapter_reset_fn()
                except Exception as e:
                    logger.warning(f"Adapter reset failed during recovery: {e}")

            if category == ErrorCategory.CONTEXT_OVERFLOW and self._compact_fn:
                try:
                    await asyncio.to_thread(self._compact_fn)
                except Exception as e:
                    logger.warning(f"State compaction failed during recovery: {e}")

            message = f"Recovering from {category.value}: retry {current_retries + 1}/{policy.max_retries}"
            if delay > 0:
                await asyncio.sleep(delay)

            return RecoveryResult(
                action_taken=f"retry_{category.value}",
                should_retry=True,
                delay=delay,
                message=message,
            )

        self._retry_counts[category] = 0

        if policy.notify_agent:
            return RecoveryResult(
                action_taken=f"notify_{category.value}",
                should_retry=False,
                message=f"Recovery exhausted for {category.value}: {error}",
            )

        return RecoveryResult(
            action_taken="skip",
            should_retry=False,
            message=f"Unrecoverable error: {category.value}: {error}",
        )

    def on_round_start(self) -> None:
        self._retry_counts.clear()

    def reset_counts(self) -> None:
        self._retry_counts.clear()
        self._total_retries.clear()
