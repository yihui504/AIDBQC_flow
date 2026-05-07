from enum import Enum
from pydantic import BaseModel, Field

class TestEventType(str, Enum):
    __test__ = False
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    FOCUS_CHANGED = "focus_changed"
    TOOL_INVOKED = "tool_invoked"
    TOOL_COMPLETED = "tool_completed"
    DEFECT_DISCOVERED = "defect_discovered"
    DEFECT_VERIFIED = "defect_verified"
    ADAPTER_SELECTED = "adapter_selected"
    COMPACTION_APPLIED = "compaction_applied"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    SESSION_SAVED = "session_saved"
    SANDBOX_EXECUTED = "sandbox_executed"

class TestEvent(BaseModel):
    __test__ = False
    event_type: TestEventType
    session_id: str = ""
    round_id: str = ""
    data: dict[str, object] = Field(default_factory=dict)
