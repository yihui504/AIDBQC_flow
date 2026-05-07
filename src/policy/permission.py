from __future__ import annotations

from enum import Enum

from src.policy.safety import SafetyLevel


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"


DANGEROUS_OPERATIONS = {
    "db_drop_collection": PermissionLevel.ADMIN,
    "db_delete_data": PermissionLevel.WRITE,
    "db_insert_data": PermissionLevel.WRITE,
    "db_create_collection": PermissionLevel.WRITE,
    "code_run_mre": PermissionLevel.EXECUTE,
}


class PermissionEvaluator:
    def __init__(self, safety_level: str = "cautious"):
        try:
            self._safety_level = SafetyLevel(safety_level)
        except ValueError:
            self._safety_level = SafetyLevel.CAUTIOUS

    def evaluate(self, tool_name: str) -> dict:
        required = DANGEROUS_OPERATIONS.get(tool_name)
        if required is None:
            return {"allowed": True, "reason": ""}

        if self._safety_level == SafetyLevel.AGGRESSIVE:
            return {"allowed": True, "reason": "aggressive mode bypasses permission check"}

        if required == PermissionLevel.ADMIN:
            return {"allowed": False, "reason": f"{tool_name} requires admin permission in {self._safety_level.value} mode"}
        if required == PermissionLevel.WRITE:
            if self._safety_level == SafetyLevel.CAUTIOUS:
                return {"allowed": False, "reason": f"{tool_name} requires write permission, blocked in cautious mode"}
            return {"allowed": True, "reason": ""}
        if required == PermissionLevel.EXECUTE:
            if self._safety_level == SafetyLevel.CAUTIOUS:
                return {"allowed": False, "reason": f"{tool_name} requires execute permission, blocked in cautious mode"}
            return {"allowed": True, "reason": ""}
        return {"allowed": True, "reason": ""}
