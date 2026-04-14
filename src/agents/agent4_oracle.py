import json
import os
from typing import Dict, Any, List

from src.agents.agent_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

from src.state import WorkflowState, TestCase, ExecutionResult, OracleValidation
from src.rate_limiter import global_llm_rate_limiter

class OracleLLMOutput(BaseModel):
    passed: bool = Field(description="Whether the results match the semantic intent")
    confidence_score: float = Field(description="Confidence score from 0.0 to 1.0 of this evaluation", ge=0.0, le=1.0)
    chain_of_thought: str = Field(description="Detailed step-by-step reasoning explaining how the conclusion was reached")
    anomalies: List[Dict[str, str]] = Field(description="List of anomalies found, if any. Keys: 'type', 'description'")
    explanation: str = Field(description="Final brief explanation of the evaluation")

class OracleCoordinatorAgent:
    """
    Agent 4: Oracle Coordinator
    Responsibilities:
    1. Traditional Oracle: Check basic result properties (e.g., monotonicity of distances).
    2. Semantic Oracle: Use LLM to verify if the retrieved results align with the user's query intent.
    """
    
    def __init__(self):
        # We use centralized factory for rigorous evaluation
        self.llm = get_llm(model_name="glm-4.7", temperature=0.1)
        self.parser = JsonOutputParser(pydantic_object=OracleLLMOutput)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI Database Quality Assurance Oracle acting as a rigorous Evaluation Scorer.
Your job is to verify if the database execution results meet the semantic expectations.
You must provide a step-by-step chain of thought (chain_of_thought) before reaching your conclusion, and assign a confidence_score (0.0 - 1.0).

### Format Instructions
{format_instructions}"""),
            ("user", """
Please evaluate the following test case execution.

Test Case ID: {case_id}
Query Text: {query_text}
Semantic Intent: {semantic_intent}

Execution Success: {success}
Error Message (if any): {error_message}

Raw Results (Top K):
{raw_results}

Analyze the results and determine if they match the semantic intent. 
If the test case was expected to fail (e.g., it's adversarial or testing a boundary) and it failed gracefully, that might be a PASS for the oracle.
If it was expected to succeed but failed, or if the retrieved items are irrelevant to the query text, it's a FAIL.

Respond with structured JSON.
""")
        ])

    def _traditional_oracle_check(self, raw_response: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Check for traditional consistency like distance monotonicity.
        Assuming distances are provided. Note: For L2, smaller is better. For IP/Cosine, larger is better.
        Since we don't know the metric here easily, we just check if it's sorted at all.
        """
        anomalies = []
        if not raw_response or len(raw_response) <= 1:
            return anomalies
            
        distances = [hit.get("distance", 0) for hit in raw_response]
        # Check if strictly ascending or descending
        is_ascending = all(distances[i] <= distances[i+1] for i in range(len(distances)-1))
        is_descending = all(distances[i] >= distances[i+1] for i in range(len(distances)-1))
        
        if not (is_ascending or is_descending):
            anomalies.append({
                "type": "sorting_anomaly",
                "description": f"Distances are neither ascending nor descending: {distances}"
            })
            
        return anomalies

    def _traditional_oracle_check_enhanced(self, test_case, raw_response: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Enhanced traditional oracle with multi-property validation.

        Checks:
        1. Distance monotonicity (existing)
        2. Result count consistency with top_k
        3. Vector dimension consistency
        4. Metric type vs distance range correspondence
        5. Distance value validity (no NaN/Inf)
        """
        import math

        anomalies = []

        # Start with existing monotonicity check
        anomalies.extend(self._traditional_oracle_check(raw_response))

        if not raw_response or len(raw_response) <= 1:
            return anomalies

        # --- NEW CHECK 2: Result count consistency ---
        is_tc_dict = isinstance(test_case, dict)
        top_k = test_case.get('top_k') if is_tc_dict else getattr(test_case, 'top_k', None)
        if top_k is not None:
            expected_count = int(top_k)
            actual_count = len(raw_response)
            if actual_count != expected_count and actual_count > 0:
                anomalies.append({
                    "type": "count_mismatch",
                    "description": f"Expected {expected_count} results (top_k={top_k}), got {actual_count}"
                })

        # --- NEW CHECK 3: Vector dimension consistency ---
        dimension = test_case.get('dimension') if is_tc_dict else getattr(test_case, 'dimension', None)
        if dimension and raw_response:
            first_hit = raw_response[0]
            vector = first_hit.get("vector") if isinstance(first_hit, dict) else None
            if vector and len(vector) > 0 and len(vector) != int(dimension):
                anomalies.append({
                    "type": "dimension_mismatch",
                    "description": f"Vector dimension mismatch: expected {dimension}, got {len(vector)}"
                })

        # --- NEW CHECK 4: Metric type vs distance range ---
        metric_type = test_case.get('metric_type') if is_tc_dict else getattr(test_case, 'metric_type', None)
        distances = [hit.get("distance", 0) for hit in raw_response if isinstance(hit, dict)]

        if metric_type and distances:
            metric_lower = str(metric_type).upper()
            if metric_lower in ("L2", "L2_SQUARED", "EUCLIDEAN"):
                neg_distances = [d for d in distances if isinstance(d, (int, float)) and d < 0]
                if neg_distances:
                    anomalies.append({
                        "type": "metric_range_violation",
                        "description": f"L2 distance should be non-negative, found negative values: {neg_distances[:3]}"
                    })
            elif metric_lower in ("COSINE", "IP", "INNER_PRODUCT", "DOT"):
                out_of_range = [d for d in distances if isinstance(d, (int, float)) and (d > 1.0 or d < -1.0)]
                if out_of_range:
                    anomalies.append({
                        "type": "metric_range_violation",
                        "description": f"Cosine/IP distance should be in [-1, 1], found out-of-range values: {out_of_range[:3]}"
                    })

        # --- NEW CHECK 5: Distance value validity ---
        invalid_distances = []
        for i, hit in enumerate(raw_response):
            if not isinstance(hit, dict):
                continue
            d = hit.get("distance")
            if d is not None:
                try:
                    f = float(d)
                    if math.isnan(f) or math.isinf(f):
                        invalid_distances.append((i, d))
                except (ValueError, TypeError):
                    invalid_distances.append((i, d))

        if invalid_distances:
            anomalies.append({
                "type": "distance_invalid",
                "description": f"Invalid distance values (NaN/Inf/non-numeric) at indices: {[x[0] for x in invalid_distances[:5]]}"
            })

        return anomalies

    def _evaluate_single_case(self, exec_res, tc_map, state):
        is_dict_res = isinstance(exec_res, dict)
        case_id = exec_res.get("case_id") if is_dict_res else exec_res.case_id
        success = exec_res.get("success") if is_dict_res else exec_res.success
        error_msg = exec_res.get("error_message") if is_dict_res else exec_res.error_message
        raw_response = exec_res.get("raw_response") if is_dict_res else exec_res.raw_response
        
        tc = tc_map.get(case_id)
        if not tc:
            return None, 0
            
        is_tc_dict = isinstance(tc, dict)
        query_text = tc.get('query_text', 'N/A') if is_tc_dict else getattr(tc, 'query_text', 'N/A')
        semantic_intent = tc.get('semantic_intent', '') if is_tc_dict else getattr(tc, 'semantic_intent', '')
        is_adversarial = tc.get('is_adversarial', False) if is_tc_dict else getattr(tc, 'is_adversarial', False)
        expected_l1 = tc.get('expected_l1_legal', True) if is_tc_dict else getattr(tc, 'expected_l1_legal', True)

        # 1. Traditional Check
        traditional_anomalies = []
        if success and raw_response:
            traditional_anomalies = self._traditional_oracle_check_enhanced(tc, raw_response)
            
        # Simple heuristic before LLM:
        if not expected_l1 and success:
            traditional_anomalies.append({
                "type": "l1_bypass_anomaly",
                "description": "Test case was L1 illegal but execution succeeded."
            })
        
        if expected_l1 and not success:
            traditional_anomalies.append({
                "type": "unexpected_failure",
                "description": f"Test case was expected to succeed but failed with: {error_msg}"
            })

        import tenacity
        
        # LLM Verification with retries
        chain = self.prompt.partial(format_instructions=self.parser.get_format_instructions()) | self.llm | self.parser
        tokens_used = 0
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            global_llm_rate_limiter.acquire(wait=True)
            res = chain.invoke({
                "case_id": case_id,
                "query_text": query_text,
                "semantic_intent": semantic_intent,
                "success": success,
                "error_message": error_msg or "None",
                "raw_results": json.dumps(raw_response, ensure_ascii=False)[:1000] if raw_response else "No results"
            })
            
            # Ensure result is an OracleLLMOutput object or dict converted to it
            if isinstance(res, dict):
                res = OracleLLMOutput(**res)
                
            # Estimate tokens (rough approximation: ~4 chars per token)
            input_text = f"{query_text} {semantic_intent} {json.dumps(raw_response, ensure_ascii=False)[:1000] if raw_response else 'No results'}"
            estimated_tokens = len(input_text) // 4
            return res, estimated_tokens

        try:
            llm_eval, tokens_used = _invoke_with_retry()
            
            passed = llm_eval.passed
            anomalies = traditional_anomalies + [{"type": a.get("type", "llm_anomaly"), "description": a.get("description", str(a))} for a in llm_eval.anomalies]
            
            # WBS 3.1: Combine CoT and Explanation
            explanation = f"[Confidence: {llm_eval.confidence_score:.2f}] [CoT: {llm_eval.chain_of_thought}] {llm_eval.explanation}"
            
            # If traditional anomalies exist, force passed = False
            if traditional_anomalies:
                passed = False
                
        except Exception as e:
            print(f"[Agent 4] LLM Oracle failed for case {case_id}: {e}")
            passed = len(traditional_anomalies) == 0
            anomalies = traditional_anomalies
            explanation = f"LLM evaluation failed. Fallback to traditional oracle. Error: {e}"

        validation = OracleValidation(
            case_id=case_id,
            passed=passed,
            anomalies=anomalies,
            explanation=explanation
        )
        print(f"[Agent 4] Oracle Case {case_id} | Passed: {passed} | Anomalies: {len(anomalies)}")
        return validation, tokens_used

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Agent 4] Running Oracle validations for {len(state.execution_results)} results...")
        
        oracle_results = []
        
        # Create a lookup for test cases
        tc_map = {}
        for tc in state.current_test_cases:
            is_dict = isinstance(tc, dict)
            case_id = tc.get('case_id') if is_dict else tc.case_id
            tc_map[case_id] = tc

        for exec_res in state.execution_results:
            validation, tokens_used = self._evaluate_single_case(exec_res, tc_map, state)
            if validation is not None:
                oracle_results.append(validation)
            state.total_tokens_used += tokens_used

        state.oracle_results = oracle_results
        return state

def agent4_oracle(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = OracleCoordinatorAgent()
    return agent.execute(state)
