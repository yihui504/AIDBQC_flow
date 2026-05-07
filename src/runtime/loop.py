from __future__ import annotations

import asyncio
import logging

from pydantic_ai import Agent, ModelSettings

from src.models.state import UnifiedState, FocusMode
from src.session import SessionStore
from src.events import EventBus, TestEventType, TestEvent
from src.policy import PolicyEngine
from src.tools import create_registry
from src.tools.db.adapter_holder import set_adapter, get_adapter
from src.tools.event_bus_holder import set_event_bus
from src.tools.doc import set_config as doc_set_config
from src.tools.source import set_config as source_set_config
from src.adapters.factory import AdapterFactory
from src.config import AppConfig, DBInstanceConfig
from src.runtime.recovery import RecoveryStrategy
from src.runtime.agent import ModelFallback
from src.models.deepseek_provider import build_model_settings

logger = logging.getLogger(__name__)

_VALID_DB_TYPES = ["milvus", "qdrant", "weaviate", "pgvector"]


class TestRuntime:
    __test__ = False
    def __init__(self, config: AppConfig):
        self._config = config
        self._state = UnifiedState(
            target_db=config.database.default,
            target_version=config.database.target_version,
            max_rounds=config.harness.max_rounds,
            max_token_budget=config.harness.max_token_budget,
            max_consecutive_failures=config.harness.max_consecutive_failures,
        )
        self._session = SessionStore(session_dir=config.output.state_dir)
        self._event_bus = EventBus()
        self._policy = PolicyEngine(safety_level=config.harness.safety_level)
        self._registry = create_registry()
        self._registry.bind_focus_advisor(self._policy.focus_advisor)
        self._agent: Agent | None = None
        self._recovery = RecoveryStrategy(
            adapter_reset_fn=self._reset_adapter,
            compact_fn=self._session.compact_state,
        )
        self._fallback = ModelFallback(config)
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._skip_current = False
        self._message_history: list = []
        self._model_settings: ModelSettings = ModelSettings()

    def initialize(self) -> None:
        from src.runtime.agent import create_agent
        self._agent = create_agent(self._config, self._policy, self._event_bus, self._state.run_id)
        self._registry.register_to_agent(self._agent)

        db_config = self._config.database
        default_instance = None
        for inst in db_config.instances:
            if inst.alias == db_config.default or inst.type == db_config.default:
                default_instance = inst
                break
        if default_instance is None and db_config.instances:
            default_instance = db_config.instances[0]
        if default_instance is None:
            fallback_type = db_config.default if db_config.default in _VALID_DB_TYPES else "milvus"
            default_instance = DBInstanceConfig(type=fallback_type)
        try:
            adapter = AdapterFactory.create(default_instance)
            set_adapter(adapter)
        except Exception as e:
            logger.warning(f"Failed to create DB adapter: {e}. DB tools will be unavailable.")

        doc_set_config(self._config)
        source_set_config(self._config)
        set_event_bus(self._event_bus)

        self._model_settings = build_model_settings(self._config)
        self._session.create(self._state)
        self._emit(TestEventType.ROUND_STARTED, {"round": self._state.round_number, "focus": self._state.current_focus.value})

    async def _execute_agent(self, prompt: str, label: str = "", **run_kwargs) -> None:
        result = await self._agent.run(
            prompt, deps=self._state, model_settings=self._model_settings,
            message_history=self._message_history, **run_kwargs,
        )
        self._message_history = result.new_messages()
        try:
            usage = result.usage()
            self._state.token_usage += usage.input_tokens + usage.output_tokens
        except Exception:
            pass
        self._state.consecutive_failures = 0
        output_text = result.output if hasattr(result, 'output') else str(result)
        if output_text:
            suffix = f"({label})" if label else ""
            self._state.execution_log.append(f"R{self._state.round_number}{suffix}: {output_text[:500]}")

    async def run_round(self) -> bool:
        if self._state.should_stop():
            return False

        await self._pause_event.wait()
        if self._skip_current:
            self._skip_current = False
            self._state.advance_round()
            return True

        self._recovery.on_round_start()
        prompt = self._build_round_prompt()
        try:
            await self._execute_agent(prompt)
            self._fallback.record_pro_success()
        except Exception as e:
            self._state.consecutive_failures += 1
            fail_count = self._state.consecutive_failures
            logger.warning(f"Round {self._state.round_number} failed: {e}")

            if self._fallback.should_fallback(e):
                try:
                    flash_model = self._fallback.get_flash_model()
                    flash_settings: ModelSettings = {"timeout": self._config.llm.timeout}
                    await self._execute_agent(prompt, label="flash", model=flash_model, model_settings=flash_settings)
                    self._fallback.record_fallback()
                    self._emit(TestEventType.RECOVERY_ATTEMPTED, {
                        "error": str(e)[:200],
                        "consecutive": fail_count,
                        "recovery_action": "flash_fallback",
                        "will_retry": False,
                    })
                    return self._finish_round()
                except Exception as flash_err:
                    logger.warning(f"Flash fallback also failed: {flash_err}")

            recovery_result = await self._recovery.recover(e)
            self._emit(TestEventType.RECOVERY_ATTEMPTED, {
                "error": str(e)[:200],
                "consecutive": fail_count,
                "recovery_action": recovery_result.action_taken,
                "will_retry": recovery_result.should_retry,
            })
            if recovery_result.should_retry:
                try:
                    await self._execute_agent(prompt, label="retry")
                except Exception as retry_err:
                    logger.warning(f"Round {self._state.round_number} retry also failed: {retry_err}")
            if self._state.consecutive_failures >= self._state.max_consecutive_failures:
                return False

        return self._finish_round()

    def _finish_round(self) -> bool:
        self._session.save_round()
        self._emit(TestEventType.ROUND_COMPLETED, {
            "round": self._state.round_number,
            "defects": len(self._state.defects),
            "focus": self._state.current_focus.value,
            "flash_fallback": self._fallback.is_on_flash,
        })
        self._state.advance_round()
        if not self._state.should_stop():
            self._emit(TestEventType.ROUND_STARTED, {"round": self._state.round_number, "focus": self._state.current_focus.value})
        return True

    async def run(self) -> UnifiedState:
        self.initialize()
        try:
            while not self._state.should_stop():
                success = await self.run_round()
                if not success:
                    break
        finally:
            self._session.save_snapshot()
        return self._state

    async def _reset_adapter(self) -> None:
        fallback_type = self._config.database.default if self._config.database.default in _VALID_DB_TYPES else "milvus"
        default_instance = DBInstanceConfig(type=fallback_type)
        try:
            new_adapter = AdapterFactory.create(default_instance)
        except Exception as e:
            logger.error(f"Failed to create new adapter: {e}")
            return
        old_adapter = get_adapter()
        set_adapter(new_adapter)
        try:
            if hasattr(old_adapter, 'close'):
                await old_adapter.close() if asyncio.iscoroutinefunction(old_adapter.close) else old_adapter.close()
        except Exception as e:
            logger.warning(f"Failed to close old adapter: {e}")

    def _build_round_prompt(self) -> str:
        parts = [
            f"Round {self._state.round_number}/{self._state.max_rounds}",
            f"Focus: {self._state.current_focus.value}",
            f"Target: {self._state.target_db} v{self._state.target_version}",
        ]
        if self._state.defects:
            parts.append(f"Defects found so far: {len(self._state.defects)}")
            recent = self._state.defects[-3:]
            parts.append("Recent defects: " + "; ".join(f"{d.defect_id}: {d.title[:60]}" for d in recent))
        if self._state.issues:
            verified = sum(1 for i in self._state.issues if i.verification_status.value == "final")
            parts.append(f"Issues: {len(self._state.issues)} total, {verified} verified")
        if self._state.feedback.weak_points:
            parts.append(f"Weak points: {', '.join(self._state.feedback.weak_points[:3])}")
        if self._state.feedback.mutation_strategies:
            parts.append(f"Suggested strategies: {', '.join(self._state.feedback.mutation_strategies[:2])}")
        if self._state.contracts.all_rules():
            validated = len(self._state.contracts.validated_rules())
            parts.append(f"Contracts: {validated}/{len(self._state.contracts.all_rules())} validated")
        if self._state.execution_log:
            last_log = self._state.execution_log[-1]
            if last_log:
                parts.append(f"Last action: {last_log[:100]}")
        return ". ".join(parts)

    def _emit(self, event_type: TestEventType, data: dict) -> None:
        self._event_bus.emit(TestEvent(
            event_type=event_type,
            session_id=self._state.run_id,
            round_id=f"R{self._state.round_number:03d}",
            data=data,
        ))

    @property
    def state(self) -> UnifiedState:
        return self._state

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def pause(self) -> None:
        self._paused = True
        self._pause_event.clear()
        logger.info("Runtime paused")

    def resume(self) -> None:
        self._paused = False
        self._pause_event.set()
        logger.info("Runtime resumed")

    def skip(self) -> None:
        self._skip_current = True
        if self._paused:
            self._paused = False
            self._pause_event.set()
        logger.info("Skipping current round")

    def stop(self) -> None:
        self._state.should_terminate = True
        if self._paused:
            self._pause_event.set()
        logger.info("Runtime stop requested")

    def set_focus(self, focus: str) -> bool:
        try:
            mode = FocusMode(focus)
            self._state.switch_focus(mode)
            logger.info(f"Focus set to: {focus}")
            return True
        except ValueError:
            logger.warning(f"Invalid focus mode: {focus}")
            return False

    def get_status(self) -> dict:
        state = self._state
        return {
            "run_id": state.run_id,
            "round": f"{state.round_number}/{state.max_rounds}",
            "focus": state.current_focus.value,
            "target": f"{state.target_db} v{state.target_version}",
            "defects": len(state.defects),
            "issues": len(state.issues),
            "verified": sum(1 for i in state.issues if i.verification_status.value == "final"),
            "tokens": state.token_usage,
            "budget_pct": round(state.token_usage / state.max_token_budget * 100, 1) if state.max_token_budget > 0 else 0,
            "consecutive_failures": state.consecutive_failures,
            "paused": self._paused,
            "flash_fallback": self._fallback.is_on_flash,
        }
