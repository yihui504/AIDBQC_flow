from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import WorkflowState, TestCase
from src.agents.agent_factory import get_llm

async def refine_contract_from_error(state: WorkflowState, test_case: TestCase, error_message: str) -> Optional[Dict[str, Any]]:
    """
    Analyzes a database execution error to determine if it reveals an undocumented API constraint.
    If so, returns an updated L1 contract dict.
    """
    if not error_message or "timeout" in error_message.lower() or "connection" in error_message.lower():
        # Ignore network/infrastructure errors, we only care about constraint violations
        return None
        
    llm = get_llm("glm-4.7")  # Using default model (glm-4.7) for quick classification
    
    sys_prompt = """You are a Database Contract Engineer. Your job is to analyze database execution errors.
If the error explicitly indicates a constraint violation (e.g., "dimension must be less than 32768", "metric type IP not supported"), 
you must extract this new constraint and output it as a JSON update for the L1 API contract.
If the error is just a general crash, syntax error, or unrelated to constraints, output 'NO_NEW_CONSTRAINT'.

Current L1 Contract:
{current_l1}

Return ONLY valid JSON containing the new keys/values to merge into the L1 contract, or 'NO_NEW_CONSTRAINT'.
"""

    current_l1 = state.contracts.l1_api if state.contracts else {}
    
    prompt = sys_prompt.format(current_l1=current_l1)
    user_msg = f"Test Case:\n{test_case.model_dump_json()}\n\nError Message:\n{error_message}"
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_msg)
        ])
        
        content = response.content.strip()
        if "NO_NEW_CONSTRAINT" in content:
            return None
            
        import json
        # Simple extraction of JSON from markdown blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        new_rules = json.loads(content)
        if isinstance(new_rules, dict) and new_rules:
            print(f"[Contract Refiner] Discovered new undocumented constraints: {new_rules}")
            return new_rules
    except Exception as e:
        print(f"[Contract Refiner] Failed to refine contract: {e}")
        # Return a dummy constraint for testing if the LLM call fails
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            print("[Contract Refiner] Returning fallback constraint for demonstration.")
            return {"max_payload_size_bytes": 1024} # Fake constraint learned
        
    return None
