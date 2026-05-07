import json
import os
from datetime import datetime
from typing import Optional
from src.models.state import UnifiedState


class SessionStore:
    def __init__(self, session_dir: str = "sessions"):
        self._session_dir = session_dir
        self._session_id: str = ""
        self._state: Optional[UnifiedState] = None
        os.makedirs(session_dir, exist_ok=True)

    def create(self, state: UnifiedState) -> str:
        self._session_id = state.run_id or datetime.now().strftime("run-%Y%m%d-%H%M%S")
        state.run_id = self._session_id
        self._state = state
        self._save_snapshot()
        return self._session_id

    @property
    def state(self) -> Optional[UnifiedState]:
        return self._state

    @property
    def session_id(self) -> str:
        return self._session_id

    def save_round(self) -> None:
        if self._state is None:
            return
        path = os.path.join(self._session_dir, f"{self._session_id}.jsonl")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "round": self._state.round_number,
            "focus": self._state.current_focus.value,
            "state": self._state.model_dump(),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def save_snapshot(self) -> None:
        self._save_snapshot()

    def _save_snapshot(self) -> None:
        if self._state is None:
            return
        path = os.path.join(self._session_dir, f"state_{self._session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._state.model_dump_json(indent=2))

    def load_latest(self, session_id: str) -> Optional[UnifiedState]:
        path = os.path.join(self._session_dir, f"{session_id}.jsonl")
        if not os.path.exists(path):
            return None
        last_valid = None
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    state_data = entry.get("state")
                    if state_data:
                        last_valid = state_data
                except json.JSONDecodeError:
                    continue
        if last_valid is None:
            return None
        self._state = UnifiedState.model_validate(last_valid)
        self._session_id = session_id
        return self._state

    def fork(self) -> Optional[UnifiedState]:
        if self._state is None:
            return None
        return self._state.model_copy(deep=True)

    def compact_state(self) -> None:
        if self._state is None:
            return
        self._state.execution_log = self._state.execution_log[-50:]
        self._state.tool_call_history = self._state.tool_call_history[-30:]
        self._state.feedback_history = self._state.feedback_history[-10:]
        self._state.focus_history = self._state.focus_history[-20:]
        self._save_snapshot()
