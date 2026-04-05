from src.state import WorkflowState
from src.telemetry import telemetry_sink, TelemetryEvent

def agent_recovery_node(state: WorkflowState) -> WorkflowState:
    """
    Recovery Node (Circuit Breaker Triggered).
    Clears out hallucinated state, resets counters, and adds a strong system prompt 
    to force Agent 2 back on track.
    """
    print(f"\n[Circuit Breaker] Triggered! {state.consecutive_failures} consecutive failures detected.")
    
    # Log Circuit Break Event
    telemetry_sink.log_event(TelemetryEvent(
        trace_id=state.run_id,
        node_name="agent_recovery",
        event_type="CIRCUIT_BREAK",
        token_usage=0,
        state_delta={"consecutive_failures": state.consecutive_failures}
    ))
    
    # 1. Reset counters
    state.consecutive_failures = 0
    
    # 2. Clear out failing test cases to avoid polluting history
    state.current_test_cases = []
    
    # 3. Inject a strict recovery prompt into fuzzing_feedback
    recovery_message = (
        "CRITICAL SYSTEM RECOVERY: Your previous generated test cases repeatedly failed "
        "L1/L2 contract validation or caused immediate DB crashes. "
        "You must STRICTLY adhere to the L1 API Contracts and stop generating illegal dimensions or metric types. "
        "Resetting context. Please generate a highly conservative, standard test case to verify system stability."
    )
    
    state.fuzzing_feedback = recovery_message
    
    print("[Agent Recovery] State cleaned. Injecting recovery prompt for next iteration.")
    return state
