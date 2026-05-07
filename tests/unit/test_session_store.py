import json
import pytest

from src.session.store import SessionStore
from src.models.state import UnifiedState


@pytest.fixture
def store(tmp_path):
    return SessionStore(session_dir=str(tmp_path / "sessions"))


@pytest.fixture
def state():
    return UnifiedState(run_id="test-run-001", target_db="milvus", round_number=1)


class TestSessionStoreCreate:
    def test_create_saves_snapshot(self, store, state, tmp_path):
        session_id = store.create(state)
        assert session_id == "test-run-001"
        assert store.session_id == "test-run-001"
        assert store.state is not None

        snapshot_path = tmp_path / "sessions" / f"state_{session_id}.json"
        assert snapshot_path.exists()
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert data["run_id"] == "test-run-001"

    def test_create_generates_id_when_missing(self, tmp_path):
        store = SessionStore(session_dir=str(tmp_path / "sessions"))
        state = UnifiedState(run_id="", round_number=1)
        session_id = store.create(state)
        assert session_id.startswith("run-")
        assert state.run_id == session_id


class TestSessionStoreSaveRound:
    def test_save_round_appends_jsonl(self, store, state, tmp_path):
        store.create(state)
        store.save_round()

        jsonl_path = tmp_path / "sessions" / f"{store.session_id}.jsonl"
        assert jsonl_path.exists()

        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["round"] == 1

    def test_save_round_multiple(self, store, state, tmp_path):
        store.create(state)
        store.save_round()
        state.round_number = 2
        store.save_round()

        jsonl_path = tmp_path / "sessions" / f"{store.session_id}.jsonl"
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["round"] == 1
        assert json.loads(lines[1])["round"] == 2

    def test_save_round_no_state_does_nothing(self, store, tmp_path):
        store.save_round()
        jsonl_path = tmp_path / "sessions" / "None.jsonl"
        assert not jsonl_path.exists()


class TestSessionStoreLoadLatest:
    def test_load_latest_restores_state(self, store, state, tmp_path):
        store.create(state)
        store.save_round()

        store2 = SessionStore(session_dir=str(tmp_path / "sessions"))
        loaded = store2.load_latest("test-run-001")
        assert loaded is not None
        assert loaded.run_id == "test-run-001"
        assert loaded.round_number == 1

    def test_load_latest_nonexistent_returns_none(self, store):
        result = store.load_latest("nonexistent-session")
        assert result is None

    def test_load_latest_picks_last_entry(self, store, state, tmp_path):
        store.create(state)
        store.save_round()

        state.round_number = 5
        store.save_round()

        store2 = SessionStore(session_dir=str(tmp_path / "sessions"))
        loaded = store2.load_latest("test-run-001")
        assert loaded is not None
        assert loaded.round_number == 5


class TestSessionStoreFork:
    def test_fork_deep_copies_state(self, store, state):
        store.create(state)
        forked = store.fork()
        assert forked is not None
        assert forked.run_id == state.run_id
        assert forked is not state

        forked.round_number = 99
        assert store.state.round_number == 1

    def test_fork_no_state_returns_none(self, store):
        result = store.fork()
        assert result is None


class TestSessionStoreCompactState:
    def test_compact_state_truncates_lists(self, store, state):
        state.execution_log = [f"log-{i}" for i in range(100)]
        state.tool_call_history = [{"tool": f"t-{i}"} for i in range(50)]
        state.feedback_history = []
        state.focus_history = []
        store.create(state)
        store.compact_state()

        assert len(store.state.execution_log) == 50
        assert store.state.execution_log[0] == "log-50"
        assert len(store.state.tool_call_history) == 30

    def test_compact_state_no_state_does_nothing(self, store):
        store.compact_state()
