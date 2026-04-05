import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.tools import DuckDuckGoSearchResults
from pydantic import BaseModel, Field

from src.state import WorkflowState
from src.rate_limiter import global_llm_rate_limiter
from src.agents.agent_factory import get_llm
from langchain_community.callbacks.manager import get_openai_callback

class SearchDecision(BaseModel):
    needs_search: bool = Field(description="Whether we need to search the web for new strategies")
    search_query: str = Field(description="The query to search if needs_search is True")
    reasoning: str = Field(description="Why we need or don't need to search")

class WebSearchAgent:
    """
    Agent: Web Search & Learning
    Responsibilities:
    1. Determine if the fuzzing loop is stuck (e.g., no new bugs found).
    2. Use DuckDuckGo Search for free, unlimited searches.
    3. Inject this new knowledge into the state to guide the next test generation.
    """
    
    def __init__(self):
        self.llm = get_llm(model_name="glm-4.7", temperature=0.2)
        self.parser = JsonOutputParser(pydantic_object=SearchDecision)
        
        # We use DuckDuckGo Search instead of Tavily for free, unlimited searches
        self.search_tool = DuckDuckGoSearchResults(max_results=3)

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Web Search Agent] Analyzing if external knowledge is needed (Iteration: {state.iteration_count})...")
        
        # Only consider searching if we've done at least one iteration
        # and maybe we didn't find any bugs in the last run (simple heuristic)
        # For demonstration, we'll let the LLM decide based on the feedback.
        
        # 智谱 (Zhipu) GLM models require messages to alternate strictly between human and assistant, 
        # or have a very specific system prompt format. We'll simplify the prompt to avoid 400 errors.
        safe_feedback = str(state.fuzzing_feedback) if state.fuzzing_feedback else "No feedback yet."
        if len(safe_feedback) > 2000:
            safe_feedback = safe_feedback[-2000:]
            
        sys_prompt = """You are a Web Search Decision Agent for a database testing pipeline.
Analyze the current fuzzing state and decide if external search is needed.
Respond ONLY with YES or NO."""
        
        user_prompt = f"""Current Fuzzing Feedback: {safe_feedback}
Iteration: {state.iteration_count}
Do we need to search the web for more bug reports? (YES/NO)"""
        
        import tenacity
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            from langchain_core.messages import SystemMessage, HumanMessage
            with get_openai_callback() as cb:
                global_llm_rate_limiter.acquire(wait=True)
                response = self.llm.invoke([
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=user_prompt)
                ])
                
                content = response.content.strip().upper()
                if "YES" in content:
                    query_prompt = f"Based on this feedback: '{safe_feedback}', what should we search for? Return ONLY the search query."
                    
                    global_llm_rate_limiter.acquire(wait=True)
                    query_response = self.llm.invoke([
                        SystemMessage(content="You generate search queries."),
                        HumanMessage(content=query_prompt)
                    ])
                    decision = SearchDecision(needs_search=True, search_query=query_response.content.strip(), reasoning="Feedback suggests search")
                else:
                    decision = SearchDecision(needs_search=False, search_query="", reasoning="Not needed")
                
                return decision, cb.total_tokens

        try:
            decision, tokens_used = _invoke_with_retry()
            state.total_tokens_used += tokens_used
            
            if decision.needs_search:
                print(f"[Web Search Agent] Decision: NEED SEARCH. Query: '{decision.search_query}'")
                
                # Execute Search using DuckDuckGo
                search_results = self.search_tool.invoke({"query": decision.search_query})
                
                # Format results
                knowledge = f"Web Search Results for '{decision.search_query}':\n{search_results}\n"
                
                print(f"[Web Search Agent] Found new external knowledge.")
                state.external_knowledge = knowledge
            else:
                print(f"[Web Search Agent] Decision: NO SEARCH NEEDED. Reasoning: {decision.reasoning}")
                
        except Exception as e:
            print(f"[Web Search Agent] Search decision failed: {e}")
            
        return state

def agent_web_search(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = WebSearchAgent()
    return agent.execute(state)
