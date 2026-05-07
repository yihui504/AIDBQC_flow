from __future__ import annotations

import logging
import time
from collections import deque
from typing import Callable

from .types import TestEvent, TestEventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[TestEvent], None]

_DEDUP_EVENTS = {TestEventType.ROUND_STARTED, TestEventType.ROUND_COMPLETED}


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[TestEventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._buffer: deque[TestEvent] = deque(maxlen=500)
        self._dedup_window: float = 1.0
        self._recent_hashes: dict[str, float] = {}

    def on(self, event_type: TestEventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    subscribe = on

    def subscribe_global(self, handler: EventHandler) -> None:
        self._global_handlers.append(handler)

    def emit(self, event: TestEvent) -> None:
        if event.event_type in _DEDUP_EVENTS:
            dedup_key = self._compute_dedup_key(event)
            now = time.time()
            if dedup_key in self._recent_hashes:
                if now - self._recent_hashes[dedup_key] < self._dedup_window:
                    return
            self._recent_hashes[dedup_key] = now
            if len(self._recent_hashes) > 1000:
                cutoff = now - self._dedup_window * 2
                self._recent_hashes = {
                    k: v for k, v in self._recent_hashes.items() if v > cutoff
                }

        self._buffer.append(event)

        handlers = list(self._handlers.get(event.event_type, []))
        globals_ = list(self._global_handlers)

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")

        for handler in globals_:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global event handler error: {event.event_type}: {e}")

    def _compute_dedup_key(self, event: TestEvent) -> str:
        import hashlib
        data_str = str(sorted(event.data.items()))
        raw = f"{event.event_type.value}:{event.session_id}:{event.round_id}:{data_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


def create_logging_emitter() -> EventBus:
    bus = EventBus()
    bus.subscribe_global(lambda e: logger.info(f"[{e.event_type.value}] {e.data}"))
    return bus
