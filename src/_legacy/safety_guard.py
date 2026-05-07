from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    SAFE = "safe"
    CAUTIOUS = "cautious"
    AGGRESSIVE = "aggressive"


_DANGEROUS_TOOLS = {
    "db_drop_collection",
    "db_delete_data",
}

_CAUTIOUS_TOOLS = {
    "db_create_collection",
    "db_insert_data",
    "db_upsert_data",
    "db_flush",
    "db_load_collection",
    "db_release_collection",
    "db_create_partition",
    "code_run_mre",
}

_SAFE_TOOLS = {
    "db_search",
    "db_query",
    "db_get_collection_info",
    "db_list_collections",
    "db_health_check",
    "doc_search",
    "doc_validate_reference",
    "web_search",
    "web_crawl",
    "update_stage",
    "record_defect",
    "generate_feedback",
}

_DANGEROUS_ARGS_PATTERNS = {
    "db_insert_data": [{"key": "count", "threshold": 5000}],
    "db_delete_data": [],
}


class TestSafetyGuard:
    def __init__(self, active_level: SafetyLevel = SafetyLevel.CAUTIOUS):
        self.active_level = active_level
        self._tool_classifications = {
            **{t: SafetyLevel.SAFE for t in _SAFE_TOOLS},
            **{t: SafetyLevel.CAUTIOUS for t in _CAUTIOUS_TOOLS},
            **{t: SafetyLevel.AGGRESSIVE for t in _DANGEROUS_TOOLS},
        }

    def classify_tool(self, tool_name: str, args: dict | None = None) -> SafetyLevel:
        base_level = self._tool_classifications.get(tool_name, SafetyLevel.CAUTIOUS)
        if args and tool_name in _DANGEROUS_ARGS_PATTERNS:
            for pattern in _DANGEROUS_ARGS_PATTERNS[tool_name]:
                key = pattern["key"]
                threshold = pattern["threshold"]
                val = args.get(key)
                if val is not None and isinstance(val, (int, float)) and val > threshold:
                    return SafetyLevel.AGGRESSIVE
        return base_level

    def check_execution(
        self,
        tool_name: str,
        args: dict | None = None,
        required_level: Optional[SafetyLevel] = None,
    ) -> bool:
        tool_level = self.classify_tool(tool_name, args)
        effective_level = required_level or self.active_level

        level_order = {
            SafetyLevel.SAFE: 0,
            SafetyLevel.CAUTIOUS: 1,
            SafetyLevel.AGGRESSIVE: 2,
        }

        if level_order[tool_level] > level_order[effective_level]:
            logger.warning(
                f"Tool '{tool_name}' requires {tool_level.value} but active level is {effective_level.value}. Blocked."
            )
            return False

        return True

    def get_tool_safety_level(self, tool_name: str) -> str:
        return self.classify_tool(tool_name).value
