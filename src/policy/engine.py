from src.models.state import FocusMode
from src.policy.focus import FocusAdvisor
from src.policy.permission import PermissionEvaluator
from src.policy.safety import SafetyGuard


_META_TOOLS = {"update_focus", "generate_feedback"}


class PolicyEngine:
    def __init__(self, safety_level: str = "cautious"):
        self.focus_advisor = FocusAdvisor()
        self.permission_evaluator = PermissionEvaluator(safety_level)
        self.safety_guard = SafetyGuard(safety_level)

    def check_tool_execution(self, tool_name: str, current_focus: FocusMode, args: dict) -> dict:
        out_of_focus = self.focus_advisor.is_out_of_focus(tool_name, current_focus) if tool_name not in _META_TOOLS else False
        perm = self.permission_evaluator.evaluate(tool_name)
        safety = self.safety_guard.check_execution(tool_name, args)

        allowed = perm["allowed"] and safety["allowed"] and not out_of_focus
        reasons = []
        if out_of_focus:
            reasons.append(f"Tool '{tool_name}' is outside current focus '{current_focus.value}'")
        if not perm["allowed"]:
            reasons.append(perm["reason"])
        if not safety["allowed"]:
            reasons.append(safety["reason"])

        return {
            "allowed": allowed,
            "out_of_focus": out_of_focus,
            "reasons": reasons,
            "focus_warning": f"Tool '{tool_name}' is outside current focus '{current_focus.value}'" if out_of_focus else "",
        }
