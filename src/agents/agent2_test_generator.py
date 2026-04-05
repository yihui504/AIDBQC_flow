import os
import uuid
import random
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.agents.agent_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate

from src.state import WorkflowState, Contract, TestCase
from src.knowledge_base import DefectKnowledgeBase
from src.rate_limiter import global_llm_rate_limiter
from langchain_community.callbacks.manager import get_openai_callback

class TestGenerationResponse(BaseModel):
    """Schema for LLM generated test cases."""
    reasoning: str = Field(description="Explanation of why these test cases were generated based on the contracts and feedback.")
    test_cases: List[TestCase] = Field(description="List of generated test cases. Provide at least 2 rule-based and 2 semantic/adversarial cases.")

class HybridTestGeneratorAgent:
    """
    Agent 2: Hybrid Test Generation Agent
    Responsibilities:
    1. Receive L1-L3 contracts and fuzzing feedback from previous iterations.
    2. Use Rule-based + LLM-based strategies to generate multi-dimensional test cases.
    3. Generate both normal boundaries and adversarial semantic queries.
    """
    
    def __init__(self):
        # Using centralized factory for creative test generation
        self.llm = get_llm(model_name="glm-4.7", temperature=0.7)
        self.parser = JsonOutputParser(pydantic_object=TestGenerationResponse)
        self.kb = DefectKnowledgeBase()

    def _generate_test_cases(self, contracts: Contract, iteration: int, feedback: str, scenario: str, external_knowledge: str) -> TestGenerationResponse:
        """Use LLM to generate test cases based on contracts, feedback, and RAG knowledge."""
        
        # WBS 2.2: RAG-based Fuzzing
        # Retrieve similar historical defects based on current scenario or feedback
        search_query = feedback if feedback else scenario
        historical_bugs = self.kb.search_similar_defects(search_query, top_k=2)
        
        historical_context = "No historical bugs found."
        if historical_bugs:
            historical_context = "Historical Similar Bugs:\n"
            for bug in historical_bugs:
                historical_context += f"- [{bug['metadata'].get('bug_type', 'Unknown')}] {bug['document']}\n"
                
        # Append external knowledge from Web Search Agent
        if external_knowledge:
            historical_context += f"\nExternal Knowledge / New Strategies:\n{external_knowledge}\n"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Fuzzing Engineer for Vector Databases.
Your task is to generate high-quality test cases based on the provided contracts (L1 API, L2 Semantic, L3 Application).

### Format Instructions
{format_instructions}

### Input Analysis
1. **Contracts**: Parse the provided L1, L2, and L3 contracts carefully. 
2. **Operational Sequences & State Transitions**: Pay special attention to `operational_sequences` and `state_transitions` in the L2 contract. These define the valid lifecycle and order of operations for the database.

### Strategies to use:
1. **Rule-based Boundary**: Test max dimensions, max top_k, edge metrics, and other L1 constraints.
2. **Semantic Adversarial**: Test semantic boundaries (e.g., synonyms, typos, out-of-domain concepts) based on L2 and L3.
3. **Adversarial Attack**: Systematically target system weaknesses, e.g., out-of-range parameters or data format injection.
4. **Chaotic Sequence Injection**: Generate test cases that intentionally violate the specified order in `operational_sequences` or `state_transitions` (e.g., calling a search operation before the collection is loaded or even created).
5. **RAG-guided Mutation**: Use the provided "Historical Similar Bugs" to mutate new vectors or queries that might trigger similar vulnerabilities.
6. **Coverage Diversity**: Aim for high coverage across different bug types, dimensions, and scenarios. Avoid repeating similar patterns.
7. **Dimension Exploration**: Test dimensions beyond the allowed list (including dimensions that have never been tested before) as negative tests.
8. **Hybrid Strategy**: Combine multiple strategies for comprehensive coverage. Each strategy should cover at least 2 test cases.

### Distribution Requirement:
At least 20% of the generated test cases MUST be negative tests (`is_negative_test: true`).
Negative tests should include:
- Invalid dimensions (e.g., dimension not in allowed list).
- Out-of-range parameters.
- **Chaotic sequences** (e.g., performing a search operation before the collection is created or data is inserted, violating the `operational_sequences`).
- For negative tests, `expected_l1_legal` should likely be `false`.

### Bug Type Coverage:
Distribute tests across different bug types:
- Type-1: L1 Crash/Error
- Type-2: Poor diagnostics
- Type-3: Application error
- Type-4: Semantic violation/Contract violation
- Type-5: Data corruption
- Type-6: Performance degradation
- Type-7: Security vulnerability
- Type-8: Resource exhaustion

Current Fuzzing Iteration: {iteration}
Feedback from previous loop (if any): {feedback}

{historical_context}

### Source URL Mapping
For each test case generated, you MUST identify which specific contract rule or parameter it is testing. 
Look up the corresponding rule name in:
- `contracts.l1_api.source_urls`
- `contracts.l2_semantic.source_urls`
- `contracts.l3_application.source_urls`
Populate the `assigned_source_url` field in the `TestCase` object with the matching URL. If no exact match is found, use the most relevant URL from the same contract level.

### Test Case Requirements
For each test case, you MUST generate:
- `case_id` (unique string)
- `dimension` (must match one of L1 allowed dimensions, unless creating a negative test)
- `query_text` (the semantic intent string)
- `is_adversarial` (boolean)
- `is_negative_test` (boolean)
- `expected_l1_legal` (boolean)
- `expected_l2_ready` (boolean)
- `expected_ground_truth`: A list of 2-3 dictionaries representing "perfect match" data items for this query. 
- `assigned_source_url`: The URL of the documentation rule being tested.

Note: For `query_vector`, you can leave it empty or provide a dummy list of floats. The Execution Agent will handle vector embedding if missing.
"""),
            ("human", "Contracts:\n{contracts}")
        ])
        
        chain = prompt.partial(format_instructions=self.parser.get_format_instructions()) | self.llm | self.parser
        
        if not global_llm_rate_limiter.acquire(wait=True):
            print("[Agent 2] Rate limit exceeded. Skipping test generation.")
            return None
        
        res = chain.invoke({
            "contracts": str(contracts),
            "iteration": iteration,
            "feedback": feedback if feedback else "Initial run. Cover basic and advanced boundaries.",
            "historical_context": historical_context
        })
        
        # Ensure result is a TestGenerationResponse object or dict converted to it
        if isinstance(res, dict):
            return TestGenerationResponse(**res)
        return res

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Main execution flow for Agent 2."""
        print(f"[Agent 2] Starting Hybrid Test Generation (Iteration: {state.iteration_count})...")
        
        if not state.contracts:
            raise ValueError("[Agent 2] No contracts found in state. Agent 1 must run first.")
            
        import tenacity
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            with get_openai_callback() as cb:
                response = self._generate_test_cases(
                    contracts=state.contracts,
                    iteration=state.iteration_count,
                    feedback=state.fuzzing_feedback,
                    scenario=state.business_scenario,
                    external_knowledge=state.external_knowledge
                )
                return response, cb.total_tokens

        try:
            response, tokens_used = _invoke_with_retry()
            
            print(f"[Agent 2] LLM Reasoning: {response.reasoning}")
            print(f"[Agent 2] Generated {len(response.test_cases)} test cases.")
            
            # Append new test cases to the state
            # In a real fuzzer, you might replace them or keep a rolling buffer
            state.current_test_cases = response.test_cases
            state.total_tokens_used += tokens_used
            print(f"[Agent 2] Tokens used: {tokens_used}")
            
        except Exception as e:
            print(f"[Agent 2] Test generation failed after retries: {e}")
            raise e
            
        return state

def agent2_test_generator(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = HybridTestGeneratorAgent()
    return agent.execute(state)
