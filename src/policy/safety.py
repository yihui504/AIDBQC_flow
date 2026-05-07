from __future__ import annotations

from enum import Enum


class SafetyLevel(str, Enum):
    CAUTIOUS = "cautious"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


_DANGEROUS_PATTERNS = [
    "DELETE ALL",
    "TRUNCATE",
    "DROP TABLE",
    "DROP DATABASE",
    "DROP SCHEMA",
    "ALTER TABLE",
    "ALTER DATABASE",
    "GRANT",
    "REVOKE",
    "EXECUTE AS",
    "XP_CMDSHELL",
    "UNION SELECT",
    "INTO OUTFILE",
    "INTO DUMPFILE",
    "LOAD_FILE",
    "INFORMATION_SCHEMA",
]


def _check_value_recursive(value) -> str | None:
    if isinstance(value, str):
        upper = value.upper()
        for pattern in _DANGEROUS_PATTERNS:
            if pattern in upper:
                return pattern
    elif isinstance(value, dict):
        for v in value.values():
            hit = _check_value_recursive(v)
            if hit:
                return hit
    elif isinstance(value, (list, tuple)):
        for v in value:
            hit = _check_value_recursive(v)
            if hit:
                return hit
    return None


class SafetyGuard:
    def __init__(self, safety_level: str = "cautious"):
        try:
            self._safety_level = SafetyLevel(safety_level)
        except ValueError:
            self._safety_level = SafetyLevel.CAUTIOUS

    def check_execution(self, tool_name: str, args: dict) -> dict:
        if self._safety_level == SafetyLevel.AGGRESSIVE:
            return {"allowed": True, "reason": "aggressive mode bypasses safety check"}
        for v in args.values():
            hit = _check_value_recursive(v)
            if hit:
                return {"allowed": False, "reason": f"Potentially dangerous operation: {hit}"}
        return {"allowed": True, "reason": ""}
