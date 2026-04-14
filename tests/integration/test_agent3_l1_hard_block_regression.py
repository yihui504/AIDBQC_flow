import pytest

from src.agents.agent3_executor import ExecutionGatingAgent
from src.state import Contract, WorkflowState


def _state_with_contract(max_dim: int = 1024, max_top_k: int = 10) -> WorkflowState:
    state = WorkflowState(run_id="it-agent3-l1", target_db_input="Milvus")
    state.contracts = Contract(
        l1_api={
            "dimension_constraint": {"mode": "range", "min": 1, "max": max_dim},
            "max_top_k": max_top_k,
        }
    )
    state.current_collection = "col_it"
    state.data_inserted = True
    return state


def _agent_hard_block_enabled() -> ExecutionGatingAgent:
    # Integration regression focuses on L1/L2/execution flow integration, not model loading.
    agent = ExecutionGatingAgent.__new__(ExecutionGatingAgent)
    agent.l1_hard_block_illegal_params = True
    return agent


class _ProbeAdapter:
    def __init__(self):
        self.current_collection_dim = 128
        self.search_call_count = 0

    async def search_async(self, *args, **kwargs):
        self.search_call_count += 1
        return {"success": True, "hits": []}


@pytest.mark.asyncio
async def test_dim_overflow_rejected_e2e():
    agent = _agent_hard_block_enabled()
    state = _state_with_contract(max_dim=512, max_top_k=10)
    adapter = _ProbeAdapter()
    tc = {"case_id": "L1_NEG_DIM_001", "dimension": 4096, "query_text": "dim overflow"}

    result = await agent._execute_single_case(tc, adapter, "col_it", True, state)

    assert result.l1_passed is False
    assert result.success is False
    assert "L1 Hard Blocked" in (result.error_message or "")
    assert adapter.search_call_count == 0


@pytest.mark.asyncio
async def test_topk_overflow_rejected_e2e():
    agent = _agent_hard_block_enabled()
    state = _state_with_contract(max_dim=512, max_top_k=10)
    adapter = _ProbeAdapter()
    tc = {"case_id": "L1_NEG_TOPK_002", "dimension": 128, "top_k": 9999, "query_text": "topk overflow"}

    result = await agent._execute_single_case(tc, adapter, "col_it", True, state)

    assert result.l1_passed is False
    assert result.success is False
    assert "L1 Hard Blocked" in (result.error_message or "")
    assert adapter.search_call_count == 0
