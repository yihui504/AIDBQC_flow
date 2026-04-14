import json
import asyncio
from typing import Dict, Any, List

from src.state import WorkflowState, ExecutionResult, TestCase

class RerankerAgent:
    """
    Agent: Reranker Agent
    Responsibilities:
    1. Re-score Top-K results using a Cross-Encoder model.
    2. Provide more accurate semantic ranking for the Oracle to evaluate.
    """

    def __init__(self):
        print("[Reranker Agent] Loading Cross-Encoder model: cross-encoder/ms-marco-MiniLM-L-6-v2...")
        try:
            from sentence_transformers import CrossEncoder
            # Set local_files_only=False but with a timeout or handle failure
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("[Reranker Agent] Cross-Encoder model loaded successfully.")
        except Exception as e:
            print(f"[Reranker Agent] Warning: Could not load Cross-Encoder ({e}). Using fallback word-overlap scoring.")
            self.model = None

    async def _rerank_single_result(self, exec_res: ExecutionResult, tc: TestCase) -> ExecutionResult:
        if not exec_res.success or not exec_res.raw_response:
            return exec_res

        query_text = (tc.query_text or "test").lower()
        hits = exec_res.raw_response

        # Prepare pairs for cross-encoder or compute fallback scores
        pairs = []
        valid_hits_indices = []
        fallback_scores = []

        for i, hit in enumerate(hits):
            payload = hit.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    # Keep original string payload; reranker will skip non-dict payloads.
                    pass
            
            # Try to find text in payload
            text = None
            if isinstance(payload, dict):
                text = payload.get("text") or payload.get("content")
            
            if text:
                if self.model:
                    pairs.append([query_text, text])
                else:
                    # Fallback: Simple word overlap score
                    q_words = set(query_text.split())
                    t_words = set(text.lower().split())
                    overlap = len(q_words & t_words) / len(q_words) if q_words else 0
                    fallback_scores.append(overlap)
                valid_hits_indices.append(i)

        if not valid_hits_indices:
            return exec_res

        if self.model and pairs:
            try:
                scores = self.model.predict(pairs)
            except Exception as e:
                print(f"[Reranker Agent] Error during prediction: {e}. Skipping rerank for this result.")
                return exec_res
        else:
            scores = fallback_scores

        # Update hits with rerank scores
        for idx, score in zip(valid_hits_indices, scores):
            hits[idx]["rerank_score"] = float(score)

        # Sort hits by rerank score descending
        hits.sort(key=lambda x: x.get("rerank_score", -float('inf')), reverse=True)
        
        exec_res.raw_response = hits
        return exec_res

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Reranker Agent] Reranking {len(state.execution_results)} execution results...")
        
        # Create a lookup for test cases
        tc_map = {}
        for tc in state.current_test_cases:
            is_dict = isinstance(tc, dict)
            case_id = tc.get('case_id') if is_dict else tc.case_id
            tc_map[case_id] = tc

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        tasks = []
        for exec_res in state.execution_results:
            is_dict_res = isinstance(exec_res, dict)
            case_id = exec_res.get('case_id') if is_dict_res else exec_res.case_id
            
            tc = tc_map.get(case_id)
            if tc:
                # We need to handle both Pydantic models and dicts for robustness
                if is_dict_res:
                    # If it's a dict, we temporarily wrap it or handle it
                    # But WorkflowState usually has Pydantic objects for execution_results
                    pass
                
                tasks.append(self._rerank_single_result(exec_res, tc))

        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks))
            print(f"[Reranker Agent] Completed reranking {len(tasks)} tasks")

        print(f"[Reranker Agent] Returning state with {len(state.execution_results)} execution results")
        return state

def agent_reranker(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = RerankerAgent()
    return agent.execute(state)
