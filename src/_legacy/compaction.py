from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from src.session import TestSession, TestState, CompactionRecord
from src.state import Stage

logger = logging.getLogger(__name__)


@dataclass
class CompactionConfig:
    max_estimated_tokens: int = 80000
    compact_every_n_rounds: int = 10
    preserve_recent_rounds: int = 3


@dataclass
class CompactionResult:
    removed_message_count: int = 0
    summary: str = ""
    preserved_rounds: int = 0
    estimated_tokens_before: int = 0
    estimated_tokens_after: int = 0


class TestRoundCompaction:
    def __init__(self, config: Optional[CompactionConfig] = None):
        self.config = config or CompactionConfig()

    def should_compact(self, session: TestSession) -> bool:
        ts = session.test_state
        if ts.current_round > 0 and ts.current_round % self.config.compact_every_n_rounds == 0:
            return True
        estimated = self.estimate_tokens(session.messages)
        if estimated > self.config.max_estimated_tokens:
            return True
        return False

    def estimate_tokens(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        text = part.get("text", "")
                        total += len(text) // 4
        return total

    def compact(self, session: TestSession) -> CompactionResult:
        ts = session.test_state
        messages = session.messages
        if not messages:
            return CompactionResult()

        tokens_before = self.estimate_tokens(messages)

        system_messages = [m for m in messages if m.get("role") == "system"]

        non_system_messages = [m for m in messages if m.get("role") != "system"]

        recent_count = 0
        recent_messages = []
        for m in reversed(non_system_messages):
            recent_messages.insert(0, m)
            if m.get("role") == "user":
                recent_count += 1
            if recent_count >= self.config.preserve_recent_rounds:
                break

        older_messages = non_system_messages[:len(non_system_messages) - len(recent_messages)]

        summary = self._build_compaction_summary(older_messages, ts)

        protected_indices = set()
        for i, m in enumerate(older_messages):
            if self._contains_critical_data(m.get("content", ""), ts):
                protected_indices.add(i)
                if m.get("role") == "tool" and m.get("tool_call_id"):
                    for j in range(i - 1, max(i - 5, -1), -1):
                        if older_messages[j].get("role") == "assistant":
                            tool_calls = older_messages[j].get("tool_calls", [])
                            if any(tc.get("id") == m.get("tool_call_id") for tc in tool_calls):
                                protected_indices.add(j)
                                break
                elif m.get("role") == "assistant" and m.get("tool_calls"):
                    for tc in m.get("tool_calls", []):
                        tc_id = tc.get("id")
                        if tc_id:
                            for j in range(i + 1, min(i + 5, len(older_messages))):
                                if older_messages[j].get("role") == "tool" and older_messages[j].get("tool_call_id") == tc_id:
                                    protected_indices.add(j)

        protected_messages = [older_messages[i] for i in sorted(protected_indices)]

        summary_message = {
            "role": "user",
            "content": summary,
        }

        new_messages = system_messages + [summary_message] + protected_messages + recent_messages
        removed_count = len(messages) - len(new_messages)

        session.messages = new_messages
        tokens_after = self.estimate_tokens(new_messages)

        cr = CompactionRecord(
            round_id=f"R{ts.current_round:03d}",
            removed_message_count=removed_count,
            summary=summary[:500],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        session.compaction_log.append(cr)

        result = CompactionResult(
            removed_message_count=removed_count,
            summary=summary,
            preserved_rounds=self.config.preserve_recent_rounds,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
        )

        logger.info(
            f"Compaction applied: removed {removed_count} messages, "
            f"tokens {tokens_before} -> {tokens_after}"
        )
        return result

    def _contains_critical_data(self, content, ts: TestState) -> bool:
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                part.get("text", "") + " " + str(part.get("input", "")) + " " + str(part.get("content", ""))
                for part in content if isinstance(part, dict)
            )
        else:
            text = str(content) if content is not None else ""

        critical_markers = [
            "DEF-", "ISS-",
            "defect_id", "issue_id",
            "evidence_completeness",
            "ContractWithConfidence",
        ]
        for marker in critical_markers:
            if marker in text:
                return True
        return False

    def _build_compaction_summary(self, older_messages: list[dict], ts: TestState) -> str:
        parts = ["[COMPACTION SUMMARY - Previous rounds have been compressed into this summary]"]

        if ts.defects:
            parts.append(f"Defects found so far ({len(ts.defects)}):")
            for d in ts.defects[:10]:
                parts.append(f"  - [{d.severity.value}] {d.title} ({d.defect_id})")
            if len(ts.defects) > 10:
                parts.append(f"  ... and {len(ts.defects) - 10} more")

        if ts.contracts and ts.contracts.all_rules():
            rules = ts.contracts.all_rules()
            parts.append(f"Contracts extracted ({len(rules)}):")
            for r in rules[:5]:
                parts.append(f"  - {getattr(r, 'name', str(r))[:80]}")
            if len(rules) > 5:
                parts.append(f"  ... and {len(rules) - 5} more")

        if ts.feedback and ts.feedback.weak_points:
            parts.append(f"Weak points: {', '.join(ts.feedback.weak_points[:5])}")

        if ts.feedback and ts.feedback.coverage_gaps:
            parts.append(f"Coverage gaps: {', '.join(ts.feedback.coverage_gaps[:5])}")

        parts.append(f"Coverage score: {ts.coverage_score:.1%}")
        parts.append(f"Current stage: {ts.current_stage.value}")
        parts.append(f"Token usage: {ts.token_usage}")

        tool_calls = [m for m in older_messages if m.get("role") == "tool"]
        if tool_calls:
            tool_names = set()
            for m in tool_calls:
                name = m.get("name", "")
                if name:
                    tool_names.add(name)
            parts.append(f"Tools used in compacted range: {', '.join(sorted(tool_names))}")

        return "\n".join(parts)

    def merge_compact_summaries(self, old_summary: str, new_summary: str) -> str:
        return f"{old_summary}\n---\n{new_summary}"
