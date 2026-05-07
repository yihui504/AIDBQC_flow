from __future__ import annotations

import hashlib
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TestEventType(str, Enum):
    ROUND_STARTED = "test.round_started"
    STAGE_TRANSITION = "test.stage_transition"
    TOOL_INVOKED = "test.tool_invoked"
    TOOL_COMPLETED = "test.tool_completed"
    DEFECT_DISCOVERED = "test.defect_discovered"
    DEFECT_VERIFIED = "test.defect_verified"
    ROUND_COMPLETED = "test.round_completed"
    COMPACTION_APPLIED = "test.compaction_applied"
    RECOVERY_ATTEMPTED = "test.recovery_attempted"
    SESSION_SAVED = "test.session_saved"


class Provenance(str, Enum):
    LIVE_TEST = "live_test"
    REPLAY = "replay"
    VERIFICATION = "verification"


class TestEvent(BaseModel):
    event_type: TestEventType
    timestamp: float = Field(default_factory=time.time)
    session_id: str = ""
    round_id: Optional[str] = None
    data: dict = Field(default_factory=dict)
    provenance: Provenance = Provenance.LIVE_TEST
    confidence: Optional[float] = None


EventHandler = Callable[[TestEvent], None]


class TestEventEmitter:
    def __init__(self):
        self._handlers: dict[TestEventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._event_buffer: list[TestEvent] = []
        self._dedup_window: float = 1.0
        self._recent_hashes: dict[str, float] = {}

    def on(self, event_type: TestEventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_any(self, handler: EventHandler) -> None:
        self._global_handlers.append(handler)

    def off(self, event_type: TestEventType, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def emit(self, event: TestEvent) -> None:
        dedup_key = self._compute_dedup_key(event)
        now = time.time()
        if dedup_key in self._recent_hashes:
            if now - self._recent_hashes[dedup_key] < self._dedup_window:
                return
        self._recent_hashes[dedup_key] = now

        if len(self._recent_hashes) > 1000:
            cutoff = now - self._dedup_window * 2
            self._recent_hashes = {k: v for k, v in self._recent_hashes.items() if v > cutoff}

        self._event_buffer.append(event)
        if len(self._event_buffer) > 500:
            self._event_buffer = self._event_buffer[-500:]

        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")

        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global event handler error: {e}")

    def get_events(
        self,
        event_type: Optional[TestEventType] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> list[TestEvent]:
        events = self._event_buffer
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

    def _compute_dedup_key(self, event: TestEvent) -> str:
        data_str = str(sorted(event.data.items()))
        raw = f"{event.event_type.value}:{event.session_id}:{event.round_id or ''}:{data_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


def create_logging_emitter() -> TestEventEmitter:
    emitter = TestEventEmitter()

    def log_event(event: TestEvent) -> None:
        round_info = f" R{event.round_id}" if event.round_id else ""
        logger.info(f"[Event] {event.event_type.value}{round_info}: {event.data}")

    emitter.on_any(log_event)
    return emitter
