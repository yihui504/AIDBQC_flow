from __future__ import annotations

import inspect
from typing import Callable

from pydantic_ai import Agent, RunContext, Tool

from src.models.state import FocusMode, ToolMeta, UnifiedState
from src.policy.focus import FocusAdvisor
from src.tools.compression import ToolOutputCompressor


class ToolRegistry:
    def __init__(self, compressor: Optional[ToolOutputCompressor] = None):
        self._tools: dict[str, Callable] = {}
        self._metas: dict[str, ToolMeta] = {}
        self._focus_advisor: Optional[FocusAdvisor] = None
        self._compressor = compressor or ToolOutputCompressor()

    def register(self, func: Callable) -> None:
        name = func.__name__
        self._tools[name] = func
        meta = getattr(func, '_tool_meta', None)
        if meta:
            self._metas[name] = meta

    def get_all_tools(self) -> dict[str, Callable]:
        return dict(self._tools)

    def get_meta(self, name: str) -> Optional[ToolMeta]:
        return self._metas.get(name)

    def bind_focus_advisor(self, advisor: FocusAdvisor) -> None:
        self._focus_advisor = advisor
        for name, meta in self._metas.items():
            advisor.register(name, meta)

    def register_to_agent(self, agent: Agent) -> None:
        for name, func in self._tools.items():
            has_ctx = self._has_run_context(func)
            if has_ctx:
                agent.tool(func)
            else:
                agent.tool_plain(func)

    def compress_output(self, tool_name: str, output: str) -> str:
        meta = self._metas.get(tool_name)
        return self._compressor.compress(tool_name, output, meta)

    @staticmethod
    def _has_run_context(func: Callable) -> bool:
        try:
            sig = inspect.signature(func)
            for p in sig.parameters.values():
                ann = p.annotation
                if ann is inspect.Parameter.empty:
                    continue
                if isinstance(ann, str):
                    if "RunContext" in ann:
                        return True
                elif ann is RunContext:
                    return True
                else:
                    try:
                        if isinstance(ann, type) and issubclass(ann, RunContext):
                            return True
                    except TypeError:
                        pass
        except Exception:
            pass
        return False

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
