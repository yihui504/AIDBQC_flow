import time
import pytest

from src.events.bus import EventBus
from src.events.types import TestEvent, TestEventType


@pytest.fixture
def bus():
    return EventBus()


def _make_event(event_type=TestEventType.ROUND_STARTED, session_id="s1", round_id="r1", data=None):
    return TestEvent(
        event_type=event_type,
        session_id=session_id,
        round_id=round_id,
        data=data or {},
    )


class TestEventBusEmit:
    def test_emit_triggers_subscribed_handler(self, bus):
        received = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received.append(e))

        event = _make_event()
        bus.emit(event)

        assert len(received) == 1
        assert received[0] is event

    def test_emit_does_not_trigger_unrelated_handler(self, bus):
        received = []
        bus.subscribe(TestEventType.TOOL_INVOKED, lambda e: received.append(e))

        bus.emit(_make_event(TestEventType.ROUND_STARTED))

        assert len(received) == 0

    def test_emit_triggers_multiple_handlers(self, bus):
        received_a = []
        received_b = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received_a.append(e))
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received_b.append(e))

        event = _make_event()
        bus.emit(event)

        assert len(received_a) == 1
        assert len(received_b) == 1


class TestEventBusGlobalHandler:
    def test_subscribe_global_receives_all_events(self, bus):
        received = []
        bus.subscribe_global(lambda e: received.append(e))

        bus.emit(_make_event(TestEventType.ROUND_STARTED))
        bus.emit(_make_event(TestEventType.TOOL_INVOKED))

        assert len(received) == 2

    def test_global_and_specific_both_fire(self, bus):
        specific = []
        global_ = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: specific.append(e))
        bus.subscribe_global(lambda e: global_.append(e))

        bus.emit(_make_event(TestEventType.ROUND_STARTED))

        assert len(specific) == 1
        assert len(global_) == 1


class TestEventBusDedup:
    def test_dedup_suppresses_duplicate_within_window(self, bus):
        received = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received.append(e))

        event = _make_event(data={"key": "val"})
        bus.emit(event)
        bus.emit(event)

        assert len(received) == 1

    def test_dedup_allows_after_window(self, bus):
        bus._dedup_window = 0.0
        received = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received.append(e))

        event = _make_event(data={"key": "val"})
        bus.emit(event)

        bus._dedup_window = 1.0
        time.sleep(0.01)
        bus._dedup_window = 0.0
        bus.emit(event)

        assert len(received) == 2

    def test_dedup_allows_different_data(self, bus):
        received = []
        bus.subscribe(TestEventType.ROUND_STARTED, lambda e: received.append(e))

        bus.emit(_make_event(data={"a": 1}))
        bus.emit(_make_event(data={"b": 2}))

        assert len(received) == 2


class TestEventBusBuffer:
    def test_emit_adds_to_buffer(self, bus):
        event = _make_event()
        bus.emit(event)

        assert len(bus._buffer) == 1
        assert bus._buffer[0] is event

    def test_buffer_truncates_at_500(self, bus):
        bus._dedup_window = 0.0

        for i in range(510):
            bus.emit(_make_event(data={"i": i}))

        assert len(bus._buffer) == 500
