import pytest

from src.agents.agent3_executor import ExecutionGatingAgent
from src.state import Contract, WorkflowState


def _build_state(l1_api: dict) -> WorkflowState:
    state = WorkflowState(run_id="run-agent3-l1", target_db_input="Milvus")
    state.contracts = Contract(l1_api=l1_api)
    state.current_collection = "col_test"
    state.data_inserted = True
    return state


def _build_agent(hard_block: bool | None = None) -> ExecutionGatingAgent:
    # Avoid heavy __init__ (SentenceTransformer loading) in unit tests.
    agent = ExecutionGatingAgent.__new__(ExecutionGatingAgent)
    if hard_block is not None:
        agent.l1_hard_block_illegal_params = hard_block
    return agent


def test_l1_dimension_hard_block_default_enabled():
    agent = _build_agent()  # default fallback should be True
    state = _build_state(
        {
            "dimension_constraint": {"mode": "range", "min": 1, "max": 1024},
            "max_top_k": 100,
        }
    )
    tc = {"case_id": "L1_NEG_DIM_001", "dimension": 4096, "query_text": "q"}

    passed, warning, details = agent._l1_gating(tc, state)

    assert passed is False
    assert warning is not None and "Dimension 4096" in warning
    assert details is not None
    assert details["violation_type"] == "dimension_out_of_range"
    assert details["blocked"] is True


def test_l1_topk_hard_block_default_enabled():
    agent = _build_agent()  # default fallback should be True
    state = _build_state(
        {
            "dimension_constraint": {"mode": "range", "min": 1, "max": 1024},
            "max_top_k": 10,
        }
    )
    tc = {"case_id": "L1_NEG_TOPK_002", "dimension": 128, "top_k": 999, "query_text": "q"}

    passed, warning, details = agent._l1_gating(tc, state)

    assert passed is False
    assert warning is not None and "top_k 999 exceeds max_top_k 10" in warning
    assert details is not None
    assert details["violation_type"] == "top_k_exceeds_limit"
    assert details["blocked"] is True


def test_l1_hard_block_can_be_disabled_by_switch():
    agent = _build_agent(hard_block=False)
    state = _build_state(
        {
            "dimension_constraint": {"mode": "range", "min": 1, "max": 1024},
            "max_top_k": 10,
        }
    )
    tc = {"case_id": "DIM_SOFT_WARN", "dimension": 2048, "query_text": "q"}

    passed, warning, details = agent._l1_gating(tc, state)

    assert passed is True
    assert warning is not None
    assert details is not None
    assert details["blocked"] is False


@pytest.mark.asyncio
async def test_execute_single_case_l1_hard_block_skips_search():
    agent = _build_agent(hard_block=True)
    state = _build_state(
        {
            "dimension_constraint": {"mode": "range", "min": 1, "max": 512},
            "max_top_k": 10,
        }
    )

    class FakeAdapter:
        def __init__(self):
            self.search_called = False
            self.current_collection_dim = 128

        async def search_async(self, *args, **kwargs):
            self.search_called = True
            return {"success": True, "hits": []}

    adapter = FakeAdapter()
    tc = {"case_id": "L1_NEG_DIM_001", "dimension": 2048, "query_text": "query"}

    result = await agent._execute_single_case(
        tc=tc,
        adapter=adapter,
        collection_name="col_test",
        l2_ready=True,
        state=state,
    )

    assert result.l1_passed is False
    assert result.success is False
    assert result.error_message is not None and "L1 Hard Blocked" in result.error_message
    assert adapter.search_called is False
