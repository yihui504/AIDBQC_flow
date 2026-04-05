from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Any, Dict

from .state import WorkflowState
from .agents.agent0_env_recon import agent0_environment_recon
from .agents.agent1_contract_analyst import agent1_scenario_analyst
from .agents.agent2_test_generator import agent2_test_generator
from .agents.agent3_executor import agent3_execution_gating
from .agents.agent4_oracle import agent4_oracle
from .agents.agent5_diagnoser import agent5_defect_diagnoser
from .agents.agent_web_search import agent_web_search
from .agents.agent_reranker import agent_reranker
from .agents.agent6_verifier import agent6_defect_verifier
from .agents.agent_reflection import agent_reflection
from .agents.agent_recovery import agent_recovery_node
from .coverage_monitor import run_coverage_monitor

# --- Conditional Routing Logic ---

def should_continue_fuzzing(state: WorkflowState) -> str:
    """Determine whether to continue the fuzzing loop or move to verification."""
    # Check Token Circuit Breaker
    if state.total_tokens_used >= state.max_token_budget:
        print(f"[Circuit Breaker] Token budget exceeded ({state.total_tokens_used}/{state.max_token_budget}). Terminating fuzzing.")
        state.should_terminate = True
        
    if state.should_terminate:
        return "verify"
    return "fuzz"

def check_circuit_breaker(state: WorkflowState) -> str:
    """Check if the system needs to enter recovery mode due to consecutive failures."""
    if state.consecutive_failures >= state.max_consecutive_failures:
        return "recover"
    return "continue"

# --- Graph Construction ---

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow for AI-DB-QC."""
    workflow = StateGraph(WorkflowState)

    # Add Nodes (Agents)
    workflow.add_node("agent0_env", agent0_environment_recon)
    workflow.add_node("agent1_contract", agent1_scenario_analyst)
    workflow.add_node("agent2_generator", agent2_test_generator)
    workflow.add_node("agent3_executor", agent3_execution_gating)
    workflow.add_node("agent_reranker", agent_reranker)
    workflow.add_node("agent4_oracle", agent4_oracle)
    workflow.add_node("agent5_diagnoser", agent5_defect_diagnoser)
    workflow.add_node("coverage_monitor", run_coverage_monitor)
    workflow.add_node("agent_web_search", agent_web_search)
    workflow.add_node("agent6_verifier", agent6_defect_verifier)
    workflow.add_node("agent_reflection", agent_reflection)
    workflow.add_node("agent_recovery", agent_recovery_node)

    # Define Linear Edges (Initialization Phase)
    workflow.set_entry_point("agent0_env")
    workflow.add_edge("agent0_env", "agent1_contract")
    workflow.add_edge("agent1_contract", "agent2_generator")

    # Define the Fuzzing Loop Edges
    workflow.add_edge("agent2_generator", "agent3_executor")
    
    # Circuit Breaker Conditional Edge
    workflow.add_conditional_edges(
        "agent3_executor",
        check_circuit_breaker,
        {
            "recover": "agent_recovery",
            "continue": "agent_reranker"
        }
    )
    
    workflow.add_edge("agent_reranker", "agent4_oracle")
    
    # Recovery node routes back to generator
    workflow.add_edge("agent_recovery", "agent2_generator")
    
    workflow.add_edge("agent4_oracle", "agent5_diagnoser")
    workflow.add_edge("agent5_diagnoser", "coverage_monitor")

    # Conditional Edge from Coverage Monitor
    workflow.add_conditional_edges(
        "coverage_monitor",
        should_continue_fuzzing,
        {
            "fuzz": "agent_web_search",  # Loop back to generate new tests via web search
            "verify": "agent6_verifier"  # Exit loop and verify bugs
        }
    )

    workflow.add_edge("agent_web_search", "agent2_generator")

 # Final Edge
    workflow.add_edge("agent6_verifier", "agent_reflection")
    workflow.add_edge("agent_reflection", END)

    # Initialize memory saver for checkpointing (WBS 1.3)
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)

# Example execution entrypoint
if __name__ == "__main__":
    app = build_workflow()
    print("AI-DB-QC LangGraph Workflow compiled successfully with Checkpointing.")
