from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.models.state import UnifiedState
from src.config import AppConfig
from src.policy.engine import PolicyEngine
from src.events import EventBus, TestEventType, TestEvent

logger = logging.getLogger(__name__)

try:
    from pydantic_ai.exceptions import SkipToolExecution
except ImportError:
    class SkipToolExecution(Exception):
        def __init__(self, result: str):
            self.result = result
            super().__init__(result)

_HOOKS_AVAILABLE = False
try:
    from pydantic_ai.capabilities import Hooks
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai import ToolDefinition
    _HOOKS_AVAILABLE = True
except ImportError:
    pass


def _build_policy_hooks(policy: PolicyEngine, event_bus: EventBus | None = None, session_id: str = "") -> Hooks:
    if not _HOOKS_AVAILABLE:
        raise RuntimeError(
            "PydanticAI Hooks not available. Policy enforcement cannot be disabled. "
            "Please install a compatible version of pydantic-ai (>=1.0)."
        )

    hooks = Hooks()

    @hooks.on.before_tool_execute
    async def enforce_policy(
        ctx: RunContext[UnifiedState],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        state = ctx.deps
        result = policy.check_tool_execution(call.tool_name, state.current_focus, args)
        if not result["allowed"]:
            reasons = "; ".join(result["reasons"])
            raise SkipToolExecution(
                f"Policy blocked '{call.tool_name}': {reasons}"
            )
        if event_bus is not None:
            def _truncate_repr(v: Any, max_len: int = 60) -> str:
                r = repr(v)
                return r[:max_len - 3] + "..." if len(r) > max_len else r
            args_summary = ", ".join(f"{k}={_truncate_repr(v)}" for k, v in list(args.items())[:4])
            event_bus.emit(TestEvent(
                event_type=TestEventType.TOOL_INVOKED,
                session_id=session_id,
                round_id=f"R{state.round_number:03d}",
                data={"tool": call.tool_name, "args": args_summary},
            ))
        return args

    @hooks.on.after_tool_execute
    async def on_tool_completed(
        ctx: RunContext[UnifiedState],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
        result: Any,
    ) -> Any:
        if event_bus is not None:
            state = ctx.deps
            event_bus.emit(TestEvent(
                event_type=TestEventType.TOOL_COMPLETED,
                session_id=session_id,
                round_id=f"R{state.round_number:03d}",
                data={"tool": call.tool_name, "success": True},
            ))
        return result

    @hooks.on.tool_execute_error
    async def on_tool_error(
        ctx: RunContext[UnifiedState],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
        error: Exception,
    ) -> Any:
        if event_bus is not None:
            state = ctx.deps
            event_bus.emit(TestEvent(
                event_type=TestEventType.RECOVERY_ATTEMPTED,
                session_id=session_id,
                round_id=f"R{state.round_number:03d}",
                data={"tool": call.tool_name, "error": str(error)[:200]},
            ))
        raise error

    return hooks


SYSTEM_PROMPT = """You are an AI-driven database quality testing agent (AIDBQC v6.0). Your mission is to discover real, reproducible bugs in vector databases.

## Focus Modes
You operate in focus modes that guide your testing strategy:
- **understanding**: Study documentation, source code, and contracts. Build your knowledge base.
- **generation**: Design test cases and strategies based on your understanding.
- **execution**: Run tests against the target database. Create collections, insert data, perform searches.
- **verification**: Verify defects, check evidence chains, filter false positives.
- **reporting**: Generate final bug issues with complete MRE code and evidence.

You can switch focus modes freely using the `update_focus` tool. The current focus is a guide, not a constraint.

## Testing Dimensions (R1-R7)
- R1: API contract compliance
- R2: Semantic correctness
- R3: Error handling robustness
- R4: Cross-database differential testing
- R5: Semantic boundary testing
- R6: Performance anomaly detection
- R7: Consistency verification

## Defect Classification
- Type-1: Illegal success (operation should fail but succeeds)
- Type-2: Insufficient diagnostics (error message lacks information)
- Type-2.PF: Precondition failure (wrong error for invalid input)
- Type-3: Traditional oracle (wrong result)
- Type-4: Semantic violation (violates documented contract)

## ANN Approximation Warning
Vector databases use approximate nearest neighbor (ANN) algorithms. Recall < 1.0 is EXPECTED behavior, not a bug. Only report ANN-related issues if the recall degradation exceeds documented thresholds or occurs under conditions where exact results are guaranteed.

## Key Rules
1. Always use `record_defect` to report findings with complete MRE code
2. Always verify defects with `verify_defect` before reporting
3. Provide evidence from documentation (`doc_reference_url`) when possible
4. MRE code must be self-contained and reproducible
5. Focus on finding REAL bugs, not expected behavior

## CRITICAL: When to Record Defects
You MUST call `record_defect` IMMEDIATELY whenever you observe ANY of these:
- An operation succeeds when it should fail (Type-1)
- An error message is misleading or unhelpful (Type-2)
- A search/query returns incorrect results (Type-3)
- An operation violates documented behavior (Type-4)
- Unexpected data loss or corruption
- Inconsistent behavior between similar operations

Do NOT wait until the "verification" or "reporting" phase to record defects. Record them AS SOON as you discover them during execution. You can always verify them later with `verify_defect`.

## Testing Strategy
1. Start by understanding the database (docs, source)
2. Quickly move to execution - create collections, insert data, search
3. Test edge cases: empty vectors, NaN, dimension mismatches, invalid metric types, boundary values
4. Test error handling: what happens with invalid inputs? Does it fail gracefully?
5. Test consistency: do insert+upsert+delete maintain data integrity?
6. Record EVERY anomaly you find immediately
"""


def _create_model(config: AppConfig, model_attr: str) -> OpenAIChatModel:
    provider = OpenAIProvider(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    model_name = getattr(config.llm, model_attr)
    model = OpenAIChatModel(
        model_name=model_name,
        provider=provider,
    )
    logger.info(f"Created model: {model_name}")
    return model


def create_pro_model(config: AppConfig) -> OpenAIChatModel:
    return _create_model(config, "pro_model")


def create_flash_model(config: AppConfig) -> OpenAIChatModel:
    return _create_model(config, "flash_model")


def create_agent(config: AppConfig, policy: PolicyEngine, event_bus: EventBus | None = None, session_id: str = "") -> Agent:
    model = create_pro_model(config)
    hooks = _build_policy_hooks(policy, event_bus, session_id)

    agent = Agent(
        model=model,
        deps_type=UnifiedState,
        system_prompt=SYSTEM_PROMPT,
        capabilities=[hooks],
    )

    logger.info("Policy hooks attached via capabilities")

    @agent.system_prompt
    def inject_focus_context(ctx: RunContext[UnifiedState]) -> str:
        state = ctx.deps
        focus = state.current_focus
        parts = [
            f"Current focus: {focus.value}",
            f"Round: {state.round_number}/{state.max_rounds}",
            f"Target: {state.target_db} v{state.target_version}",
            f"Defects found: {len(state.defects)}",
            f"Contracts: L1={len(state.contracts.l1_rules)}, L2={len(state.contracts.l2_rules)}, L3={len(state.contracts.l3_rules)}",
        ]
        if state.feedback.weak_points:
            parts.append(f"Weak points: {', '.join(state.feedback.weak_points[:5])}")
        return "\n".join(parts)

    return agent


def is_fallback_eligible(error: Exception) -> bool:
    msg = str(error).lower()
    return any(kw in msg for kw in ["429", "rate limit", "quota", "timeout", "timed out", "capacity"])


class ModelFallback:
    def __init__(self, config: AppConfig):
        self._config = config
        self._flash_model: OpenAIChatModel | None = None
        self._consecutive_fallbacks = 0
        self._max_consecutive = 3
        self._cooldown_rounds = 0
        self._cooldown_threshold = 2

    def get_flash_model(self) -> OpenAIChatModel:
        if self._flash_model is None:
            self._flash_model = create_flash_model(self._config)
        return self._flash_model

    def should_fallback(self, error: Exception) -> bool:
        if not is_fallback_eligible(error):
            return False
        if self._consecutive_fallbacks >= self._max_consecutive:
            return False
        return True

    def record_fallback(self) -> None:
        self._consecutive_fallbacks += 1
        self._cooldown_rounds = 0
        logger.info(f"Flash fallback triggered (consecutive: {self._consecutive_fallbacks})")

    def record_pro_success(self) -> None:
        if self._consecutive_fallbacks > 0:
            self._cooldown_rounds += 1
            if self._cooldown_rounds >= self._cooldown_threshold:
                self._consecutive_fallbacks = 0
                self._cooldown_rounds = 0
                logger.info("Pro model recovered, resetting fallback counter")

    @property
    def is_on_flash(self) -> bool:
        return self._consecutive_fallbacks > 0
