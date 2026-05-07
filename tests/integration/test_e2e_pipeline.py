import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.runtime import TestRuntime
from src.config import AppConfig
from src.events import EventBus, TestEventType, TestEvent
from src.policy import PolicyEngine
from src.runtime.recovery import RecoveryStrategy, ErrorCategory
from src.runtime.agent import ModelFallback, is_fallback_eligible
from src.models.state import UnifiedState, FocusMode, tool_meta
from src.models.defect import DefectReport, DefectType, Severity, EvidenceChain
from src.models.issue import BugIssue, VerificationStatus
from src.session import SessionStore
from src.tools.registry import ToolRegistry
from src.tools.compression import ToolOutputCompressor
from src.ui.display import AgentDisplay
from src.tools.verify.filter import FalsePositiveFilter, FilterResult
from src.ann_whitelist import ANNWhitelistChecker


class TestE2EPipeline:

    @pytest.mark.asyncio
    async def test_full_pipeline_initialization(self, tmp_path):
        config = AppConfig(
            output={"state_dir": str(tmp_path / "runs")},
            llm={"api_key": "test-key"},
        )
        mock_agent = MagicMock()
        with patch("src.runtime.agent.create_agent", return_value=mock_agent), \
             patch("src.adapters.factory.AdapterFactory.create") as mock_adapter, \
             patch("src.tools.db.adapter_holder.set_adapter"), \
             patch("src.tools.doc.set_config"), \
             patch("src.tools.source.set_config"):
            mock_adapter.return_value = MagicMock()
            runtime = TestRuntime(config)
            runtime.initialize()

        assert runtime._agent is mock_agent
        assert runtime._registry.tool_count > 0
        assert runtime._session.session_id != ""
        assert runtime.state.run_id != ""

    @pytest.mark.asyncio
    async def test_event_bus_propagation(self):
        bus = EventBus()
        display = AgentDisplay(bus)

        event = TestEvent(
            event_type=TestEventType.ROUND_STARTED,
            session_id="test-session",
            round_id="R001",
            data={"round": 1, "focus": "execution"},
        )
        bus.emit(event)

        assert display._current_round == 1
        assert display._current_focus == "execution"

    @pytest.mark.asyncio
    async def test_policy_blocks_dangerous_tool(self):
        policy = PolicyEngine(safety_level="cautious")
        result = policy.check_tool_execution(
            tool_name="db_execute",
            current_focus=FocusMode.EXECUTION,
            args={"query": "DELETE ALL FROM collection"},
        )
        assert result["allowed"] is False
        assert any("DELETE ALL" in r or "dangerous" in r.lower() for r in result["reasons"])

    @pytest.mark.asyncio
    async def test_recovery_on_connection_error(self):
        reset_fn = AsyncMock()
        strategy = RecoveryStrategy(adapter_reset_fn=reset_fn)

        error = ConnectionError("connection refused to database")
        result = await strategy.recover(error)

        assert result.should_retry is True
        assert "db_connection_lost" in result.action_taken
        reset_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flash_fallback_on_rate_limit(self):
        config = AppConfig(llm={"api_key": "test-key"})
        fallback = ModelFallback(config)

        error = Exception("429 rate limit exceeded")
        assert is_fallback_eligible(error) is True
        assert fallback.should_fallback(error) is True

        with patch("src.runtime.agent.create_flash_model") as mock_flash:
            mock_flash.return_value = MagicMock()
            flash = fallback.get_flash_model()
            assert flash is not None

        fallback.record_fallback()
        assert fallback.is_on_flash is True

    @pytest.mark.asyncio
    async def test_defect_lifecycle(self, tmp_path):
        state = UnifiedState(
            run_id="test-lifecycle",
            target_db="milvus",
            target_version="2.6.12",
        )

        defect = DefectReport(
            defect_id="D-001",
            defect_type=DefectType.ILLEGAL_SUCCESS.value,
            severity=Severity.HIGH.value,
            title="Insert accepts invalid dimension vectors",
            description="The database accepts vectors with wrong dimensions without error",
            evidence_chain=EvidenceChain(
                mre_code="from pymilvus import Collection\nc = Collection('test')\nc.insert([[1,2]])",
            ),
        )
        state.defects.append(defect)
        assert len(state.defects) == 1
        assert state.defects[0].defect_id == "D-001"

        issue = BugIssue(
            issue_id="I-001",
            title=defect.title,
            defect_type=DefectType.ILLEGAL_SUCCESS,
            severity=Severity.HIGH,
            mre_code=defect.evidence_chain.mre_code,
            expected_behavior="Should reject vectors with mismatched dimensions",
            actual_behavior="Accepts vectors silently",
            evidence_chain=defect.evidence_chain,
            verification_status=VerificationStatus.PENDING,
        )
        state.issues.append(issue)
        assert len(state.issues) == 1
        assert state.issues[0].issue_id == "I-001"

        fp_filter = FalsePositiveFilter()
        filter_result = await fp_filter.filter(issue)
        assert isinstance(filter_result, FilterResult)
        assert filter_result.mre_reproducible is False
        assert filter_result.mre_verified is False

    @pytest.mark.asyncio
    async def test_session_persistence(self, tmp_path):
        session_dir = str(tmp_path / "sessions")
        store = SessionStore(session_dir=session_dir)

        state = UnifiedState(
            run_id="persist-test",
            target_db="qdrant",
            target_version="1.8.0",
            round_number=1,
        )
        session_id = store.create(state)
        assert session_id == "persist-test"

        state.round_number = 2
        state.switch_focus(FocusMode.EXECUTION, "moving to execution")
        store.save_round()

        loaded = store.load_latest("persist-test")
        assert loaded is not None
        assert loaded.run_id == "persist-test"
        assert loaded.round_number == 2
        assert loaded.current_focus == FocusMode.EXECUTION

    @pytest.mark.asyncio
    async def test_compressor_integration(self):
        compressor = ToolOutputCompressor()
        registry = ToolRegistry(compressor=compressor)

        @tool_meta(focus_modes=[FocusMode.EXECUTION], compress="summary")
        def db_search(query: str) -> str:
            return ""

        registry.register(db_search)

        large_output = '{"success": true, "results_count": 500, "data": [' + \
            ", ".join([f'{{"id": {i}, "score": 0.{i:03d}}}' for i in range(500)]) + \
            '], "vectors": [' + \
            ", ".join([f'[{",".join(["0.1"]*128)}]' for i in range(50)]) + \
            ']}'

        compressed = registry.compress_output("db_search", large_output)
        assert len(compressed) < len(large_output)
