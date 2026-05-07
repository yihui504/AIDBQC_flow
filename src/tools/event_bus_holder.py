from __future__ import annotations

from src.events import EventBus

_current_bus: EventBus | None = None


def set_event_bus(bus: EventBus) -> None:
    global _current_bus
    _current_bus = bus


def get_event_bus() -> EventBus | None:
    return _current_bus
