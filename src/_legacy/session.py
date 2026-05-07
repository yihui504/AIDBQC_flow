from __future__ import annotations

import json
import os
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.models.contract import ContractSet
from src.models.defect import DefectReport
from src.models.issue import BugIssue
from src.state import Stage, FuzzingFeedback

logger = logging.getLogger(__name__)


class CompactionRecord(BaseModel):
    round_id: str = ""
    removed_message_count: int = 0
    summary: str = ""
    timestamp: str = ""


class TestState(BaseModel):
    run_id: str = ""
    current_stage: Stage = Stage.UNDERSTANDING
    current_round: int = 1
    max_rounds: int = 4
    target_db: str = "milvus"
    target_version: str = "2.6.12"
    scenario: str = ""
    contracts: ContractSet = Field(default_factory=ContractSet)
    defects: list[DefectReport] = Field(default_factory=list)
    issues: list[BugIssue] = Field(default_factory=list)
    coverage_score: float = 0.0
    token_usage: int = 0
    max_token_budget: int = 2000000
    consecutive_failures: int = 0
    max_consecutive_failures: int = 5
    should_terminate: bool = False
    feedback: FuzzingFeedback = Field(default_factory=FuzzingFeedback)
    execution_log: list[str] = Field(default_factory=list)
    tool_call_history: list[dict] = Field(default_factory=list)

    def is_budget_exhausted(self) -> bool:
        return self.token_usage >= self.max_token_budget

    def is_max_rounds_reached(self) -> bool:
        return self.current_round >= self.max_rounds

    def should_stop(self) -> bool:
        return (
            self.should_terminate
            or self.is_budget_exhausted()
            or self.is_max_rounds_reached()
            or self.consecutive_failures >= self.max_consecutive_failures
        )

    def advance_stage(self) -> None:
        stage_order = list(Stage)
        current_idx = stage_order.index(self.current_stage)
        if current_idx < len(stage_order) - 1:
            self.current_stage = stage_order[current_idx + 1]
        else:
            self.current_round += 1
            self.current_stage = Stage.UNDERSTANDING

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


class TestSession(BaseModel):
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    messages: list[dict] = Field(default_factory=list)
    test_state: TestState = Field(default_factory=TestState)
    compaction_log: list[CompactionRecord] = Field(default_factory=list)

    def record_test_round(self, round_summary: dict) -> None:
        self.updated_at = time.time()
        self.messages = round_summary.get("messages", self.messages)
        self.test_state = TestState(**round_summary.get("test_state", self.test_state.model_dump()))

    def save_round(self, path: Path, round_summary: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            "round_id": f"R{self.test_state.current_round:03d}",
            "session_id": self.session_id,
            "messages_snapshot": round_summary.get("messages", []),
            "test_state_snapshot": self.test_state.model_dump(mode="json"),
            "token_usage": self.test_state.token_usage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "defects": [d.model_dump(mode="json") for d in self.test_state.defects],
            "contracts": self.test_state.contracts.model_dump(mode="json"),
        }, ensure_ascii=False, default=str)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        logger.info(f"Session round saved: {path} (round {self.test_state.current_round})")

    @classmethod
    def load_latest(cls, path: Path) -> Optional[TestSession]:
        if not path.exists():
            return None
        lines: list[str] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        if not lines:
            return None
        for line in reversed(lines):
            try:
                data = json.loads(line)
                test_state = TestState(**data.get("test_state_snapshot", {}))
                session = cls(
                    session_id=data.get("session_id", uuid.uuid4().hex[:16]),
                    messages=data.get("messages_snapshot", []),
                    test_state=test_state,
                )
                logger.info(f"Session restored from {path} (round {test_state.current_round})")
                return session
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Skipping corrupted line in {path}: {e}")
                continue
        logger.error(f"All lines corrupted in {path}, cannot restore session")
        return None

    def fork(self, new_session_id: Optional[str] = None) -> TestSession:
        forked = self.model_copy(deep=True)
        forked.session_id = new_session_id or str(uuid.uuid4())[:8]
        forked.created_at = time.time()
        forked.updated_at = time.time()
        return forked
