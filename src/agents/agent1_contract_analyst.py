import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.agents.agent_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate

from src.state import WorkflowState, Contract
from src.parsers.doc_parser import StructuredDocParser
from src.rate_limiter import global_llm_rate_limiter
from langchain_community.callbacks.manager import get_openai_callback

class L1Contract(BaseModel):
    """L1 API Contracts (Strong constraints from docs)"""
    allowed_dimensions: List[int] = Field(description="List of allowed vector dimensions")
    supported_metrics: List[str] = Field(description="Supported distance metrics (e.g., L2, IP, COSINE)")
    max_top_k: int = Field(description="Maximum allowed value for top_k parameter")
    max_collection_name_length: int = Field(default=255, description="Maximum allowed length for collection names")
    max_payload_size_bytes: int = Field(default=65535, description="Maximum payload size in bytes")
    supported_index_types: List[str] = Field(default=["HNSW", "IVF_FLAT", "FLAT"], description="Supported indexing algorithms")
    state_constraints: List[str] = Field(default=["collection_exists", "index_loaded"], description="Pre-conditions for execution (e.g., collection must exist, index must be loaded)")
    source_urls: Dict[str, str] = Field(default_factory=dict)
    exhaustive_constraints: Dict[str, Any] = Field(default_factory=dict)

class L2Contract(BaseModel):
    """L2 Semantic Contracts (Weak constraints/logic)"""
    expected_monotonicity: bool = Field(default=True, description="Whether top_k results should be monotonic")
    expected_consistency: bool = Field(default=True, description="Whether write-then-read should be consistent")
    expected_strictness: bool = Field(default=True, description="Whether filters should strictly reduce the result set")
    semantic_threshold_hint: float = Field(default=0.5, description="Suggested threshold for semantic relevance")
    query_intent_types: List[str] = Field(default=["similarity", "exact_match", "hybrid"], description="Types of query intents to test")
    source_urls: Dict[str, str] = Field(default_factory=dict)
    operational_sequences: List[Dict[str, Any]] = Field(default_factory=list)
    state_transitions: List[Dict[str, Any]] = Field(default_factory=list)

class ScoringRubric(BaseModel):
    rule: str = Field(description="A specific semantic expectation rule")
    weight: float = Field(description="Weight of this rule (0.0 to 1.0)")

class ContextConstraints(BaseModel):
    domain: str = Field(default="generic", description="The business domain (e.g., e-commerce, finance)")
    user_intent: str = Field(default="find similar items", description="The overarching user intent for the scenario")
    vector_types: List[str] = Field(description="Expected vector types (e.g., dense, sparse, binary)")
    metadata_fields: List[str] = Field(description="Expected metadata fields for filtering")

class L3Contract(BaseModel):
    """L3 Application Contracts (Scenario based)"""
    scenario_name: str = Field(description="Name of the business scenario")
    scoring_rubrics: List[ScoringRubric] = Field(description="Specific, weighted rules for the Scorer to evaluate")
    context_constraints: ContextConstraints = Field(description="Key-value pairs of context constraints")
    source_urls: Dict[str, str] = Field(default_factory=dict)

class ParsedContracts(BaseModel):
    """Wrapper for all three contract levels."""
    l1: L1Contract
    l2: L2Contract
    l3: L3Contract

class ContractAnalystAgent:
    """
    Agent 1: Scenario & Contract Analyst Agent
    Responsibilities:
    1. Parse the target DB documentation (from Agent 0).
    2. Parse the business scenario (from user input).
    3. Extract and formalize L1 (API), L2 (Semantic), and L3 (Application) contracts.
    """
    
    def __init__(self):
        # Initialize LLM for contract extraction using centralized factory
        self.llm = get_llm(model_name="glm-4.7", temperature=0.1)
        self.parser = JsonOutputParser(pydantic_object=ParsedContracts)

    def _prune_docs(self, docs: str, max_chars: int = 30000) -> str:
        """Prune documentation to stay within token limits while preserving relevant info."""
        if len(docs) <= max_chars:
            return docs
            
        print(f"[Agent 1] Pruning docs from {len(docs)} to ~{max_chars} chars...")
        
        # Split into sections by Source
        sections = docs.split("Source: ")
        pruned_sections = []
        
        # Keywords that indicate relevant API info
        keywords = ["limit", "dimension", "metric", "parameter", "config", "capacity", "constraint", "top_k", "collection", "index"]
        
        for section in sections:
            if not section.strip():
                continue
                
            # Extremely large sections (like raw HTML/PDF dumps) should be skipped or heavily truncated
            if len(section) > 50000:
                print(f"[Agent 1] Warning: Skipping extremely large section ({len(section)} chars)")
                continue
            
            # If the section contains keywords, keep more of it
            section_lower = section.lower()
            if any(kw in section_lower for kw in keywords):
                # Keep up to 10k per high-value section
                pruned_sections.append(section[:10000])
            else:
                # Keep only 2k for lower-value sections
                pruned_sections.append(section[:2000])
        
        result = "Source: ".join(pruned_sections)
        
        # Final safety check
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...[TRUNCATED TO PREVENT LLM CONTEXT OVERFLOW]..."
            
        return result

    def _extract_contracts(self, docs_context: str, scenario: str) -> ParsedContracts:
        """Use LLM to extract formal contracts from text context with pre-extracted constraints."""
        import json

        # WBS 3.4: Content Pruning to prevent LLM overload
        pruned_docs = self._prune_docs(docs_context)

        # Step 1: Run StructuredDocParser to extract constraints before LLM
        structured_context = ""
        try:
            parser = StructuredDocParser()

            # Parse each document source (split by "Source: " delimiter)
            doc_sources = pruned_docs.split("Source: ")
            all_constraints = []

            for source_content in doc_sources:
                if not source_content.strip():
                    continue

                # Extract URL if present (first line usually contains the URL)
                lines = source_content.strip().split('\n')
                source_url = lines[0].strip() if lines and (lines[0].startswith('http') or '/' in lines[0]) else None

                # Parse content (handles both HTML and Text)
                constraints = parser.parse(source_content, source_url)
                all_constraints.extend(constraints)

            # Convert constraints to JSON format for LLM context
            if all_constraints:
                structured_constraints = {
                    'total_constraints': len(all_constraints),
                    'constraints_by_parameter': {}
                }

                for constraint in all_constraints:
                    param = constraint.parameter
                    if param not in structured_constraints['constraints_by_parameter']:
                        structured_constraints['constraints_by_parameter'][param] = []

                    constraint_dict = constraint.to_dict()
                    structured_constraints['constraints_by_parameter'][param].append(constraint_dict)

                structured_context = json.dumps(structured_constraints, indent=2, ensure_ascii=False)
                print(f"[Agent 1] StructuredDocParser extracted {len(all_constraints)} constraints")
            else:
                print("[Agent 1] StructuredDocParser found no constraints, falling back to LLM-only extraction")

        except Exception as e:
            print(f"[Agent 1] StructuredDocParser failed: {e}. Continuing with LLM-only extraction.")
            structured_context = "{}"

        # Step 2: Enhanced LLM prompt with pre-extracted constraints
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Vector Database Quality Assurance Analyst.
Your task is to analyze the provided database documentation and the user's business scenario, then extract formal test contracts based on the AI-DB-QC framework.

IMPORTANT: The pre-extracted constraints below are your PRIMARY source of truth for L1 API contracts. Use them as the foundation and only supplement with information from the raw documentation context when necessary.

{structured_context}

### Deep Exhaustive Extraction
- **L1 API Contracts**: Perform "Deep Exhaustive Extraction" of all API parameters found in `structured_context`. Extract every single parameter, limit, and constraint listed. Populate `exhaustive_constraints` with any additional parameters not covered by the main L1 fields.
- **Operational Sequences & State Transitions (L2)**: Identify mandatory sequences of operations (e.g., "must call load() before search()") and state transitions (e.g., "index state moves from 'creating' to 'ready'"). Populate `operational_sequences` and `state_transitions` in the L2 contract.
- **Source Tracking**: For EVERY extracted rule or constraint, you MUST populate the `source_urls` dictionary (in L1, L2, and L3) mapping the rule name or parameter name to its corresponding `source_url` provided in the `APIConstraint` objects within `structured_context`. If a rule comes from the raw text, use the URL associated with that section of documentation.

### Contract Definitions
- **l1**: Hard API limits (dimensions, metrics, max_top_k, max_collection_name_length, max_payload_size_bytes, supported_index_types, state_constraints).
- **l2**: Expected algorithmic properties (monotonicity, consistency, filter strictness, semantic thresholds, query intent types, operational sequences, and state transitions).
- **l3**: Scenario-specific expectations represented as `scoring_rubrics` with weights, and context constraints.

### Output Requirement
Your output MUST be a valid JSON object with exactly the following keys at the top level: "l1", "l2", "l3".
- "l1" MUST have keys: "allowed_dimensions" (list), "supported_metrics" (list), "max_top_k" (int), "max_collection_name_length" (int), "max_payload_size_bytes" (int), "supported_index_types" (list), "state_constraints" (list), "source_urls" (dict), "exhaustive_constraints" (dict).
- "l2" MUST have keys: "expected_monotonicity" (bool), "expected_consistency" (bool), "expected_strictness" (bool), "semantic_threshold_hint" (float), "query_intent_types" (list), "source_urls" (dict), "operational_sequences" (list of dicts), "state_transitions" (list of dicts).
- "l3" MUST have keys: "scenario_name" (str), "scoring_rubrics" (list of {{"rule": str, "weight": float}}), "context_constraints" ({{"domain": str, "user_intent": str, "vector_types": list, "metadata_fields": list}}), "source_urls" (dict).

Format Instructions:
{format_instructions}"""),
            ("human", "Database Documentation Context:\n{docs}\n\nBusiness Scenario:\n{scenario}")
        ])

        chain = prompt.partial(format_instructions=self.parser.get_format_instructions()) | self.llm | self.parser

        # Debug: Print inputs
        print(f"[Agent 1] Invoking LLM with docs length: {len(pruned_docs)}, scenario: {scenario[:50] if scenario else 'None'}...")
        try:
            if global_llm_rate_limiter is not None:
                global_llm_rate_limiter.acquire(wait=True)
            res = chain.invoke({
                "structured_context": structured_context,
                "docs": pruned_docs,
                "scenario": scenario if scenario else "Generic Vector Similarity Search"
            })
            print(f"[Agent 1] LLM returned result type: {type(res)}")
            if res is None:
                print("[Agent 1] WARNING: LLM returned None!")
                raise ValueError("LLM returned None result during contract extraction")
            
            # Ensure result is a ParsedContracts object or dict converted to it
            if isinstance(res, dict):
                return ParsedContracts(**res)
            return res
        except Exception as e:
            print(f"[Agent 1] LLM invocation failed: {e}")
            raise

    def execute(self, state: WorkflowState) -> WorkflowState:
        """Main execution flow for Agent 1."""
        print("[Agent 1] Starting scenario analysis and contract extraction...")
        
        # Ensure we have docs context from Agent 0
        docs_context = ""
        if state.db_config and state.db_config.docs_context:
            docs_context = state.db_config.docs_context
        else:
            print("[Agent 1] Warning: No documentation context found in state. Using fallback.")
            docs_context = "Standard Vector Database (assumed Milvus/Qdrant behavior)"
            
        # Extract contracts with retries
        import tenacity
        
        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        def _invoke_with_retry():
            with get_openai_callback() as cb:
                parsed = self._extract_contracts(docs_context, state.business_scenario)
                return parsed, cb.total_tokens

        try:
            parsed, tokens_used = _invoke_with_retry()
            print(f"[Agent 1] Successfully extracted contracts for scenario: {parsed.l3.scenario_name}")
            
            # Print the full JSON structure of the extracted contracts
            import json
            print("\n=== Extracted Contracts (JSON) ===")
            print(json.dumps(parsed.model_dump(), indent=2, ensure_ascii=False))
            print("==================================\n")
            
            # Update State
            state.contracts = Contract(
                l1_api=parsed.l1.model_dump(),
                l2_semantic=parsed.l2.model_dump(),
                l3_application=parsed.l3.model_dump()
            )
            state.total_tokens_used += tokens_used
            print(f"[Agent 1] Tokens used: {tokens_used}")
            
        except Exception as e:
            print(f"[Agent 1] Failed to extract contracts after retries: {e}")
            raise e
            
        return state

def agent1_scenario_analyst(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = ContractAnalystAgent()
    return agent.execute(state)
