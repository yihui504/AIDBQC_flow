import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from src.state import WorkflowState
from src.knowledge_base import DefectKnowledgeBase, BugRecord
from src.rate_limiter import global_llm_rate_limiter
from src.agents.agent_factory import get_llm
from langchain_community.callbacks.manager import get_openai_callback

class ReflectionOutput(BaseModel):
    summary: str = Field(description="Summary of the testing session")
    new_strategies: str = Field(description="New fuzzing strategies learned from this session")
    save_to_kb: bool = Field(description="Whether we should save these strategies to the KB as a meta-record")

class ReflectionAgent:
    """
    Agent: Strategy Reflection Node
    Responsibilities:
    1. Runs at the end of the pipeline (after verification).
    2. Summarizes what worked and what didn't.
    3. Extracts new mutation operators or strategies.
    4. Saves meta-learnings to the Knowledge Base.
    """
    
    def __init__(self):
        self.llm = get_llm(model_name="glm-4.7", temperature=0.3)
        self.parser = JsonOutputParser(pydantic_object=ReflectionOutput)
        self.kb = DefectKnowledgeBase()

    def execute(self, state: WorkflowState) -> WorkflowState:
        print("\n[Reflection Agent] Starting post-run reflection...")
        
        verified_defects = state.verified_defects
        if not verified_defects:
            verified_defects = [d for d in state.defect_reports if getattr(d, "reproduced_bug", False)]

        if not verified_defects:
            print("[Reflection Agent] No reproducible defects found in this run. Skipping deep reflection.")
            return state
            
        defect_summaries = "\n".join([
            f"- [{d.bug_type}] ({getattr(d, 'verifier_verdict', 'pending')}) {d.root_cause_analysis}"
            for d in verified_defects
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Lead AI QA Architect. The testing session just finished.
Analyze the defects found and extract high-level "Testing Strategies" or "Mutation Operators" that successfully triggered these bugs.
These strategies will be saved and used to train future Fuzzing Agents.

Output a JSON object with keys: summary (string), new_strategies (string), and save_to_kb (boolean)."""),
            ("human", "Defects Found:\n{defects}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        import tenacity
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            with get_openai_callback() as cb:
                global_llm_rate_limiter.acquire(wait=True)
                res = chain.invoke({"defects": defect_summaries})
                return res, cb.total_tokens

        try:
            reflection, tokens_used = _invoke_with_retry()
            state.total_tokens_used += tokens_used
            
            def _get_attr(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)
            
            if reflection is None:
                print("[Reflection Agent] Reflection returned None. Skipping summary output.")
                print("[Reflection Agent] No strategies learned from this run.")
            else:
                print(f"[Reflection Agent] Summary: {_get_attr(reflection, 'summary')}")
                print(f"[Reflection Agent] Learned Strategies: {_get_attr(reflection, 'new_strategies')}")
                
                if _get_attr(reflection, 'save_to_kb', False):
                    # Save meta-strategy to KB as a special bug record
                    meta_record = BugRecord(
                        case_id=f"META_STRATEGY_{state.run_id[:8]}",
                        bug_type="Meta-Strategy",
                        root_cause_analysis=_get_attr(reflection, 'new_strategies', ''),
                        evidence_level="L3"
                    )
                    self.kb.add_defect(meta_record)
                    print("[Reflection Agent] Saved learned strategies to Knowledge Base.")
                
        except Exception as e:
            print(f"[Reflection Agent] Reflection failed: {e}")
            
        return state

def agent_reflection(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = ReflectionAgent()
    return agent.execute(state)
