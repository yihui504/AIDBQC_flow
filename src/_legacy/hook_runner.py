from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    proceed: bool = True
    modified_args: dict | None = None
    message: str = ""


HookFn = Callable[[str, dict], HookResult]


@dataclass
class HookEntry:
    name: str
    fn: HookFn
    priority: int = 0


class TestHookRunner:
    def __init__(self):
        self._pre_hooks: list[HookEntry] = []
        self._post_hooks: list[HookEntry] = []
        self._post_failure_hooks: list[HookEntry] = []
        self._post_defect_hooks: list[HookEntry] = []

    def register_pre_hook(self, name: str, fn: HookFn, priority: int = 0) -> None:
        self._pre_hooks.append(HookEntry(name=name, fn=fn, priority=priority))
        self._pre_hooks.sort(key=lambda h: h.priority, reverse=True)

    def register_post_hook(self, name: str, fn: HookFn, priority: int = 0) -> None:
        self._post_hooks.append(HookEntry(name=name, fn=fn, priority=priority))
        self._post_hooks.sort(key=lambda h: h.priority, reverse=True)

    def register_post_failure_hook(self, name: str, fn: HookFn, priority: int = 0) -> None:
        self._post_failure_hooks.append(HookEntry(name=name, fn=fn, priority=priority))
        self._post_failure_hooks.sort(key=lambda h: h.priority, reverse=True)

    def register_post_defect_hook(self, name: str, fn: HookFn, priority: int = 0) -> None:
        self._post_defect_hooks.append(HookEntry(name=name, fn=fn, priority=priority))
        self._post_defect_hooks.sort(key=lambda h: h.priority, reverse=True)

    def run_pre_hooks(self, tool_name: str, args: dict) -> HookResult:
        current_args = args
        for entry in self._pre_hooks:
            try:
                result = entry.fn(tool_name, current_args)
                if not result.proceed:
                    logger.info(f"Pre-hook '{entry.name}' blocked execution of '{tool_name}': {result.message}")
                    return result
                if result.modified_args is not None:
                    current_args = result.modified_args
            except Exception as e:
                logger.error(f"Pre-hook '{entry.name}' error for '{tool_name}': {e}")
        return HookResult(proceed=True, modified_args=current_args if current_args is not args else None)

    def run_post_hooks(self, tool_name: str, args: dict) -> HookResult:
        for entry in self._post_hooks:
            try:
                result = entry.fn(tool_name, args)
                if result.message:
                    logger.info(f"Post-hook '{entry.name}' for '{tool_name}': {result.message}")
            except Exception as e:
                logger.error(f"Post-hook '{entry.name}' error for '{tool_name}': {e}")
        return HookResult(proceed=True)

    def run_post_failure_hooks(self, tool_name: str, args: dict) -> HookResult:
        for entry in self._post_failure_hooks:
            try:
                result = entry.fn(tool_name, args)
                if result.message:
                    logger.info(f"Post-failure hook '{entry.name}' for '{tool_name}': {result.message}")
            except Exception as e:
                logger.error(f"Post-failure hook '{entry.name}' error for '{tool_name}': {e}")
        return HookResult(proceed=True)

    def run_post_defect_hooks(self, tool_name: str, args: dict) -> HookResult:
        for entry in self._post_defect_hooks:
            try:
                result = entry.fn(tool_name, args)
                if result.message:
                    logger.info(f"Post-defect hook '{entry.name}' for '{tool_name}': {result.message}")
            except Exception as e:
                logger.error(f"Post-defect hook '{entry.name}' error for '{tool_name}': {e}")
        return HookResult(proceed=True)


def create_default_hooks() -> TestHookRunner:
    runner = TestHookRunner()

    def pre_validate_mre(tool_name: str, args: dict) -> HookResult:
        if tool_name == "code_run_mre":
            mre_code = args.get("mre_code", "")
            if not mre_code.strip():
                return HookResult(proceed=False, message="MRE code is empty")
            if "import os" in mre_code and "rm -rf" in mre_code:
                return HookResult(proceed=False, message="MRE code contains dangerous command")
        return HookResult(proceed=True)

    def pre_check_timeout(tool_name: str, args: dict) -> HookResult:
        if tool_name == "code_run_mre":
            timeout = args.get("timeout", 60)
            if isinstance(timeout, (int, float)) and timeout > 300:
                return HookResult(
                    proceed=True,
                    modified_args={**args, "timeout": 300},
                    message="Timeout capped at 300s",
                )
        return HookResult(proceed=True)

    def post_collect_evidence(tool_name: str, args: dict) -> HookResult:
        if tool_name.startswith("db_"):
            logger.debug(f"Evidence collected for {tool_name}")
        return HookResult(proceed=True)

    def post_defect_trigger_verify(tool_name: str, args: dict) -> HookResult:
        if tool_name == "record_defect":
            logger.info(f"Defect recorded, verification should be triggered: {args.get('title', 'unknown')}")
        return HookResult(proceed=True)

    runner.register_pre_hook("validate_mre", pre_validate_mre, priority=10)
    runner.register_pre_hook("check_timeout", pre_check_timeout, priority=5)
    runner.register_post_hook("collect_evidence", post_collect_evidence, priority=5)
    runner.register_post_defect_hook("trigger_verify", post_defect_trigger_verify, priority=10)

    return runner
