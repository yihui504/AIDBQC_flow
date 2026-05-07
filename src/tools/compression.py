from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from src.models.state import ToolMeta


@dataclass
class CompressionConfig:
    max_chars_per_output: int = 2000
    max_lines_per_output: int = 50
    max_line_chars: int = 200


_TOOL_STRATEGIES = {
    "db_search": {
        "preserve_patterns": ["success", "error", "results_count", "top_k", "ids"],
        "truncate_fields": ["vectors", "scores", "distances", "data"],
        "max_data_items": 5,
    },
    "db_query": {
        "preserve_patterns": ["success", "error", "count"],
        "truncate_fields": ["data", "results"],
        "max_data_items": 5,
    },
    "db_insert_data": {
        "preserve_patterns": ["success", "error", "insert_count"],
        "truncate_fields": ["ids"],
        "max_data_items": 10,
    },
    "db_create_collection": {
        "preserve_patterns": ["success", "error", "collection_name"],
        "truncate_fields": [],
        "max_data_items": 0,
    },
    "db_get_collection_info": {
        "preserve_patterns": ["success", "error", "name", "schema", "index"],
        "truncate_fields": ["vectors"],
        "max_data_items": 0,
    },
    "code_run_mre": {
        "preserve_patterns": ["success", "error", "exit_code", "stdout"],
        "truncate_fields": ["stderr"],
        "max_data_items": 0,
    },
    "doc_search": {
        "preserve_patterns": ["success", "error", "title", "url"],
        "truncate_fields": ["content", "text", "body"],
        "max_data_items": 3,
    },
    "doc_validate_reference": {
        "preserve_patterns": ["valid", "relevance_score", "url", "title"],
        "truncate_fields": ["content", "text", "body"],
        "max_data_items": 0,
    },
}

_PRIORITY_ORDER = [
    "error", "success", "exit_code", "results_count", "count",
    "title", "url", "stdout", "stderr", "data", "content",
]

_COMPRESS_LEVELS = {
    "minimal": 0.2,
    "summary": 0.5,
    "results_only": 0.7,
    "full": 1.0,
}


class ToolOutputCompressor:
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()

    def compress(self, tool_name: str, output: str, meta: Optional[ToolMeta] = None) -> str:
        if not output or len(output) <= self.config.max_chars_per_output:
            return output

        level = _COMPRESS_LEVELS.get(meta.compress, 0.5) if meta else 0.5

        strategy = _TOOL_STRATEGIES.get(tool_name)
        if strategy:
            compressed = self._apply_strategy(output, strategy, level)
        else:
            compressed = self._generic_compress(output)

        budget = int(self.config.max_chars_per_output * level)
        if len(compressed) > budget:
            compressed = self._enforce_budget(compressed, budget)

        return compressed

    def _apply_strategy(self, output: str, strategy: dict, level: float) -> str:
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return self._generic_compress(output)

        if not isinstance(data, dict):
            return self._generic_compress(output)

        preserve = strategy.get("preserve_patterns", [])
        truncate = strategy.get("truncate_fields", [])
        max_items = max(1, int(strategy.get("max_data_items", 5) * level))

        result = {}
        for key, value in data.items():
            if any(p in key for p in preserve):
                if isinstance(value, list) and max_items > 0 and len(value) > max_items:
                    result[key] = value[:max_items]
                    result[f"{key}_truncated"] = f"... ({len(value) - max_items} more items)"
                elif isinstance(value, str) and len(value) > 500:
                    result[key] = value[:500] + "..."
                else:
                    result[key] = value
            elif any(t in key for t in truncate):
                if isinstance(value, list):
                    result[key] = f"[{len(value)} items truncated]"
                elif isinstance(value, str):
                    result[key] = f"[{len(value)} chars truncated]"
                else:
                    result[key] = "[truncated]"
            else:
                if isinstance(value, str) and len(value) > 200:
                    result[key] = value[:200] + "..."
                else:
                    result[key] = value

        return json.dumps(result, ensure_ascii=False)

    def _generic_compress(self, output: str) -> str:
        lines = output.split("\n")
        if len(lines) <= self.config.max_lines_per_output:
            return output

        selected = self._select_lines(lines, self.config.max_lines_per_output)
        header = f"[Output compressed: {len(lines)} lines -> {len(selected)} lines]"
        return header + "\n" + "\n".join(selected)

    def _select_lines(self, lines: list[str], budget: int) -> list[str]:
        if len(lines) <= budget:
            return lines

        scored = []
        for i, line in enumerate(lines):
            score = 0
            line_lower = line.lower()
            for priority_idx, keyword in enumerate(_PRIORITY_ORDER):
                if keyword in line_lower:
                    score += (len(_PRIORITY_ORDER) - priority_idx) * 10
            if "error" in line_lower or "fail" in line_lower:
                score += 100
            if "success" in line_lower:
                score += 50
            if i < 3 or i >= len(lines) - 3:
                score += 20
            scored.append((score, i, line))

        scored.sort(key=lambda x: (-x[0], x[1]))
        selected_indices = sorted([s[1] for s in scored[:budget]])
        return [lines[i] for i in selected_indices]

    def _enforce_budget(self, text: str, budget: int) -> str:
        if len(text) <= budget:
            return text
        truncated = text[:budget - 50]
        return truncated + f"\n... [truncated, {len(text)} total chars]"
