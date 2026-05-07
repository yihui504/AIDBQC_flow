from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from src.models.contract import ContractSet
from src.models.defect import DefectReport
from src.models.issue import BugIssue


class FocusMode(str, Enum):
    UNDERSTANDING = "understanding"
    GENERATION = "generation"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    REPORTING = "reporting"


class FuzzingFeedback(BaseModel):
    weak_points: list[str] = Field(default_factory=list)
    mutation_strategies: list[str] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)
    round_number: int = 0

    def to_prompt_text(self) -> str:
        parts = []
        if self.weak_points:
            parts.append(f"Weak points: {', '.join(self.weak_points)}")
        if self.mutation_strategies:
            parts.append(f"Suggested strategies: {', '.join(self.mutation_strategies)}")
        if self.coverage_gaps:
            parts.append(f"Coverage gaps: {', '.join(self.coverage_gaps)}")
        return " | ".join(parts) if parts else "No specific feedback"


class FocusTransition(BaseModel):
    from_focus: FocusMode
    to_focus: FocusMode
    reason: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ToolMeta(BaseModel):
    focus_modes: list[FocusMode] = Field(default_factory=list)
    permission: str = "read"
    compress: str = "summary"
    db_target: bool = False
    description: str = ""


def tool_meta(**kwargs) -> Callable:
    def decorator(func: Callable) -> Callable:
        func._tool_meta = ToolMeta(**kwargs)
        return func
    return decorator


class UnifiedState(BaseModel):
    run_id: str = ""
    target_db: str = "milvus"
    target_version: str = "2.6.12"
    scenario: str = ""
    current_focus: FocusMode = FocusMode.UNDERSTANDING
    round_number: int = 1
    max_rounds: int = 4
    contracts: ContractSet = Field(default_factory=ContractSet)
    defects: list[DefectReport] = Field(default_factory=list)
    issues: list[BugIssue] = Field(default_factory=list)
    coverage_score: float = 0.0
    token_usage: int = 0
    max_token_budget: int = 800000
    consecutive_failures: int = 0
    max_consecutive_failures: int = 5
    should_terminate: bool = False
    feedback: FuzzingFeedback = Field(default_factory=FuzzingFeedback)
    execution_log: list[str] = Field(default_factory=list)
    tool_call_history: list[dict] = Field(default_factory=list)
    feedback_history: list[FuzzingFeedback] = Field(default_factory=list)
    user_instructions: list[str] = Field(default_factory=list)
    focus_history: list[FocusTransition] = Field(default_factory=list)
    source_analysis: str | None = None
    stage_artifacts: dict[str, Any] = Field(default_factory=dict)
    defect_counter: int = 0

    def add_execution_log(self, entry: str) -> None:
        self.execution_log.append(f"[{datetime.now().isoformat()}] {entry}")
        if len(self.execution_log) > 500:
            self.execution_log = self.execution_log[-500:]

    def add_tool_call(self, tool_name: str, args: dict, result_summary: str) -> None:
        self.tool_call_history.append({
            "tool": tool_name,
            "args_summary": str(args)[:200],
            "result_summary": result_summary[:200],
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.tool_call_history) > 200:
            self.tool_call_history = self.tool_call_history[-200:]

    def switch_focus(self, new_focus: FocusMode, reason: str = "") -> None:
        if new_focus != self.current_focus:
            transition = FocusTransition(
                from_focus=self.current_focus,
                to_focus=new_focus,
                reason=reason,
            )
            self.focus_history.append(transition)
            self.current_focus = new_focus

    def advance_round(self) -> None:
        self.round_number += 1

    def is_budget_exhausted(self) -> bool:
        return self.token_usage >= self.max_token_budget

    def is_max_rounds_reached(self) -> bool:
        return self.round_number >= self.max_rounds

    def should_stop(self) -> bool:
        return (
            self.should_terminate
            or self.is_budget_exhausted()
            or self.is_max_rounds_reached()
            or self.consecutive_failures >= self.max_consecutive_failures
        )

    @classmethod
    def from_legacy(cls, core_dict: dict, context_dict: dict | None = None) -> UnifiedState:
        kwargs = {}
        direct_fields = [
            "run_id", "target_db", "scenario", "coverage_score", "token_usage",
            "max_token_budget", "consecutive_failures", "max_consecutive_failures",
            "should_terminate", "contracts", "defects", "issues", "feedback",
        ]
        for key in direct_fields:
            if key in core_dict:
                kwargs[key] = core_dict[key]

        if "current_stage" in core_dict:
            try:
                kwargs["current_focus"] = FocusMode(core_dict["current_stage"])
            except ValueError:
                kwargs["current_focus"] = FocusMode.UNDERSTANDING
        if "current_round" in core_dict:
            kwargs["round_number"] = core_dict["current_round"]

        if context_dict:
            for key in ["execution_log", "tool_call_history", "feedback_history",
                        "user_instructions", "source_analysis", "stage_artifacts"]:
                if key in context_dict:
                    kwargs[key] = context_dict[key]

        return cls(**kwargs)
