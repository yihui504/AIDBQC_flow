import time
import random
import asyncio
import logging
from typing import Dict, Any, List, Optional

from src.state import WorkflowState, TestCase, ExecutionResult, DimensionConstraint
from src.adapters.db_adapter import MilvusAdapter, QdrantAdapter, WeaviateAdapter
from src.docker_probe import DockerLogsProbe
from src.agents.agent_contract_refiner import refine_contract_from_error
from src.config import ConfigLoader

logger = logging.getLogger(__name__)

class ExecutionGatingAgent:
    """
    Agent 3: Execution & Gating Agent
    Responsibilities:
    1. Perform L1 abstract gating (check dimensions, metrics against contract).
    2. Embed the query_text into a query_vector if missing using SentenceTransformers.
    3. Perform L2 runtime gating (check connection, db status).
    4. Execute the test case against the target database via Adapter.
    """
    
    def __init__(self):
        print("[Agent 3] Loading SentenceTransformer model for real embeddings...")
        try:
            from sentence_transformers import SentenceTransformer
            # Using a fast, small model that outputs 384 dimensions
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.base_dimension = 384
        except ImportError:
            print("[Agent 3] ERROR: sentence_transformers not installed. This is required for real embeddings.")
            raise RuntimeError("sentence_transformers is required but not installed.")
        self.l1_hard_block_illegal_params = self._load_l1_hard_block_config()
        print(f"[Agent 3] L1 hard block for illegal dimension/top_k: {self.l1_hard_block_illegal_params}")

    def _load_l1_hard_block_config(self) -> bool:
        """
        Load L1 hard-block switch for illegal parameters.
        Priority:
        1) YAML/env config: agent3.l1_hard_block_illegal_params
        2) Default: True (secure by default)
        """
        try:
            config = ConfigLoader()
            config.load()
            config.override_from_env()
            return config.get_bool("agent3.l1_hard_block_illegal_params", default=True)
        except Exception as e:
            logger.warning("[Agent 3] Failed to load L1 hard-block config, using default=True: %s", e)
            return True

    def _is_l1_hard_block_enabled(self) -> bool:
        """Safe accessor for tests that bypass __init__ via __new__."""
        return bool(getattr(self, "l1_hard_block_illegal_params", True))
            
    def _get_embedding(self, text: str, target_dimension: int) -> List[float]:
        """Generate real embedding and pad/truncate to target dimension."""
        # 2. Implement 'Pressure Injection': If dimension > 10000, generate an extreme Zero-padded vector.
        if target_dimension > 10000:
            print(f"[Agent 3] Pressure Injection: target_dimension={target_dimension} > 10000. Generating extreme zero-padded vector.")
            return [0.0] * target_dimension

        # Generate real 384-dimensional embedding
        import numpy as np
        vec = self.embedder.encode(text).tolist()

        # Debug: Print initial dimensions
        print(f"[Agent 3] Embedding: text='{text[:30]}...', base_dim={len(vec)}, target_dim={target_dimension}")

        # Adjust dimension to match the test case requirement
        if target_dimension == self.base_dimension:
            pass  # Already correct
        elif target_dimension < self.base_dimension:
            # Truncate
            vec = vec[:target_dimension]
        else:
            # Pad with zeros
            vec = list(vec) + [0.0] * (target_dimension - self.base_dimension)

        # Verify final dimension
        if len(vec) != target_dimension:
            print(f"[Agent 3] WARNING: Embedding dimension mismatch! Expected {target_dimension}, got {len(vec)}")

        return vec

    def _l1_gating(self, tc: TestCase, state: WorkflowState) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        L1 Contract Validation.
        Returns (passed, warning_message, violation_details).
        For illegal dimension/top_k:
        - default: hard block (passed=False)
        - configurable: warning pass-through (passed=True)
        Checks:
        - dimension: whether within allowed_dimensions range
        - metric_type: whether in supported_metrics list
        - top_k: whether exceeds max_top_k limit
        """
        import logging
        logger = logging.getLogger(__name__)

        if not state.contracts:
            print("[Agent 3] No contracts found in state. Failing L1.")
            return False, None, None

        is_dict = isinstance(tc, dict)
        dimension = tc.get('dimension') if is_dict else tc.dimension
        case_id = tc.get('case_id') if is_dict else tc.case_id

        warning = None

        # Access the L1 contract dictionary properly
        l1_contract = state.contracts.l1_api if hasattr(state.contracts, 'l1_api') else state.contracts.get('l1_api', {})

        # 1. Check Dimension - CHANGED: Return warning instead of blocking
        # Dual-mode: prefer dimension_constraint (DimensionConstraint), fallback to allowed_dimensions
        dc = l1_contract.get("dimension_constraint")
        allowed_dimensions = l1_contract.get("allowed_dimensions", [])

        if dc:
            dc_obj = DimensionConstraint(**dc) if isinstance(dc, dict) else dc
            if not dc_obj.contains(dimension):
                if dc_obj.mode == "list":
                    warning = f"Dimension {dimension} not in allowed list {dc_obj.values}"
                else:
                    lo_txt = str(dc_obj.min) if dc_obj.min is not None else "0"
                    hi_txt = str(dc_obj.max) if dc_obj.max is not None else "inf"
                    warning = f"Dimension {dimension} out of range [{lo_txt}, {hi_txt}]"
                print(f"[Agent 3] L1 Warning: {warning}")
                logger.info("[Agent 3] L1 Gating | Case %s | dimension=%s | result=WARNING: %s", case_id, dimension, warning)
                hard_block = self._is_l1_hard_block_enabled()
                severity = "hard" if hard_block else "soft"
                violation_details = {
                    "violation_type": "dimension_out_of_range",
                    "actual_value": dimension,
                    "expected_range": [dc_obj.min, dc_obj.max] if dc_obj.mode == "range" else dc_obj.values,
                    "severity": severity,
                    "mode": dc_obj.mode,
                    "blocked": hard_block,
                }
                return (not hard_block), warning, violation_details
        elif allowed_dimensions and dimension not in allowed_dimensions:
            warning = f"Dimension {dimension} not in allowed {allowed_dimensions} - potential Type-1 bug"
            print(f"[Agent 3] L1 Warning: {warning}")
            logger.info("[Agent 3] L1 Gating | Case %s | dimension=%s | result=WARNING: %s", case_id, dimension, warning)
            hard_block = self._is_l1_hard_block_enabled()
            violation_details = {
                "violation_type": "dimension_out_of_range",
                "actual_value": dimension,
                "expected_range": allowed_dimensions,
                "severity": "hard" if hard_block else "soft",
                "mode": "legacy_list",
                "blocked": hard_block,
            }
            return (not hard_block), warning, violation_details

        # 2. Check metric_type - must be in supported_metrics
        supported_metrics = l1_contract.get("supported_metrics", [])
        if supported_metrics:
            metric_type = tc.get('metric_type') if is_dict else getattr(tc, 'metric_type', None)
            if metric_type and metric_type not in supported_metrics:
                warning = f"metric_type '{metric_type}' not in supported {supported_metrics} - potential Type-1 bug"
                print(f"[Agent 3] L1 Warning: {warning}")
                logger.info("[Agent 3] L1 Gating | Case %s | metric_type=%s | result=WARNING: %s", case_id, metric_type, warning)
                violation_details = {
                    "violation_type": "invalid_metric_type",
                    "actual_value": metric_type,
                    "expected_range": supported_metrics,
                    "severity": "soft"
                }
                return True, warning, violation_details

        # 3. Check top_k - must not exceed max_top_k
        max_top_k = l1_contract.get("max_top_k", None)
        if max_top_k is not None:
            top_k = tc.get('top_k') if is_dict else getattr(tc, 'top_k', None)
            if top_k is not None and int(top_k) > int(max_top_k):
                warning = f"top_k {top_k} exceeds max_top_k {max_top_k} - potential Type-1 bug"
                print(f"[Agent 3] L1 Warning: {warning}")
                logger.info("[Agent 3] L1 Gating | Case %s | top_k=%s | result=WARNING: %s", case_id, top_k, warning)
                hard_block = self._is_l1_hard_block_enabled()
                violation_details = {
                    "violation_type": "top_k_exceeds_limit",
                    "actual_value": int(top_k),
                    "expected_range": f"<= {max_top_k}",
                    "severity": "hard" if hard_block else "soft",
                    "blocked": hard_block,
                }
                return (not hard_block), warning, violation_details

        logger.info("[Agent 3] L1 Gating | Case %s | PASSED all checks", case_id)
        return True, None, None

    def _l2_gating(self, tc: TestCase, state: WorkflowState) -> tuple[bool, Optional[str]]:
        """
        L2 Runtime Readiness Check.

        Checks if the runtime state satisfies preconditions for execution.

        Returns (passed, reason):
        - (True, None): Ready for execution
        - (False, "reason"): Not ready, will affect classification

        Checks:
        - Collection exists in pool
        - Collection has data inserted
        - Index is loaded (if required)
        """
        import logging
        logger = logging.getLogger(__name__)

        is_dict = isinstance(tc, dict)
        case_id = tc.get('case_id') if is_dict else tc.case_id

        # Check if collection exists in current context
        collection_name = getattr(state, 'current_collection', None)
        if not collection_name:
            logger.info("[Agent 3] L2 Gating | Case %s | result=FAILED: No active collection", case_id)
            return False, "No active collection"

        # Check if data was inserted
        has_data = getattr(state, 'data_inserted', False)
        if not has_data:
            logger.info("[Agent 3] L2 Gating | Case %s | result=FAILED: Collection empty - no data inserted", case_id)
            return False, "Collection empty - no data inserted"

        logger.info("[Agent 3] L2 Gating | Case %s | PASSED all readiness checks", case_id)
        return True, None

    async def _execute_single_case(self, tc: TestCase, adapter, collection_name: str, l2_ready: bool, state: WorkflowState) -> ExecutionResult:
        # Handle Pydantic model vs Dict
        is_dict = isinstance(tc, dict)
        case_id = tc.get('case_id') if is_dict else tc.case_id
        dimension = tc.get('dimension') if is_dict else tc.dimension
        query_text = tc.get('query_text') if is_dict else tc.query_text

        # 1. L1 Interception: Contract validation
        l1_passed, l1_warning, l1_violation_details = self._l1_gating(tc, state)

        # 2. L2 Gating: Runtime readiness check
        l2_passed_detail, l2_reason = self._l2_gating(tc, state)
        l2_result_dict = {
            "passed": l2_passed_detail,
            "reason": l2_reason
        }

        error_msg = None
        raw_resp = None
        success = False
        exec_time = 0.0
        underlying_logs = None
        l1_illegal_success = False

        if not l1_passed:
            error_msg = f"L1 Hard Blocked: {l1_warning or 'Illegal dimensions or parameters.'}"
        elif not l2_ready:
            error_msg = "L2 Gating Failed: Database not ready or disconnected."
        elif not l2_passed_detail:
            error_msg = f"L2 Runtime Readiness Failed: {l2_reason}"
        else:
            if l1_warning:
                print(f"[Agent 3] Executing potentially illegal request: {l1_warning}")
                l1_illegal_success = True
            try:
                # 2. Embedding - IMPORTANT: Use collection's dimension, not test case dimension
                # Get the actual collection dimension from the adapter
                collection_dim = getattr(adapter, 'current_collection_dim', dimension)
                if collection_dim != dimension:
                    print(f"[Agent 3] Case {case_id}: Test dim={dimension}, Collection dim={collection_dim}. Padding to collection dim.")

                query_vector = self._get_embedding(query_text or "test", collection_dim)

                # 3. Execution (Async)
                import time as time_module
                start_time = time_module.time()
                res = await adapter.search_async(collection_name, query_vector, top_k=5)
                exec_time = (time_module.time() - start_time) * 1000 # ms

                success = res["success"]
                raw_resp = res.get("hits", [])
                if not success:
                    error_msg = res.get("error")
                    # 3. Enhanced Logging: Record raw MilvusException details if available.
                    if "code" in res and "message" in res:
                        error_msg = f"Milvus Error [Code: {res['code']}]: {res['message']}"
                    elif "code" in res:
                        error_msg = f"Milvus Error [Code: {res['code']}]: {error_msg}"
                    
                    # WBS 2.1: Use Docker Probe on failure
                    print(f"[Agent 3] Case {case_id} failed. Fetching deep observability logs...")
                    db_type = state.db_config.db_name.lower() if state.db_config and state.db_config.db_name else "unknown"
                    db_lower = db_type.lower() if db_type else ""
                    if 'qdrant' in db_lower:
                        probe_container = 'qdrant'
                    elif 'weaviate' in db_lower:
                        probe_container = 'weaviate'
                    else:
                        probe_container = 'milvus-standalone'
                    probe = DockerLogsProbe(container_name=probe_container)
                    underlying_logs = probe.fetch_recent_logs(tail=50)

                    # WBS 3.0: Adaptive Contract Evolution
                new_constraints = await refine_contract_from_error(state, tc, error_msg)
                if new_constraints and state.contracts and hasattr(state.contracts, 'l1_api'):
                    print(f"[Agent 3] Hot-patching L1 contract with new rules.")
                    state.contracts.l1_api.update(new_constraints)
            except OSError as oe:
                # Catch specific OS-level errors including errno 22
                import traceback
                error_msg = f"OS Error [Errno {oe.errno}]: {str(oe)}"
                print(f"[Agent 3] OS ERROR in case {case_id}: {error_msg}")
                traceback.print_exc()
                underlying_logs = traceback.format_exc()
            except Exception as e:
                import traceback
                # 3. Enhanced Logging: Record raw MilvusException details if available.
                if hasattr(e, 'code') and hasattr(e, 'message'):
                    error_msg = f"Milvus Exception [Code: {getattr(e, 'code')}]: {getattr(e, 'message')}"
                else:
                    error_msg = f"Unexpected error: {str(e)}"
                
                print(f"[Agent 3] ERROR in case {case_id}: {error_msg}")
                traceback.print_exc()
                underlying_logs = traceback.format_exc()
                
                # Attempt to refine contract even on unexpected exceptions
                try:
                    new_constraints = await refine_contract_from_error(state, tc, error_msg)
                    if new_constraints and state.contracts and hasattr(state.contracts, 'l1_api'):
                        print(f"[Agent 3] Hot-patching L1 contract with new rules (from unexpected error).")
                        state.contracts.l1_api.update(new_constraints)
                except Exception as refine_exc:
                    logger.exception(
                        "[Agent 3] Failed to refine contract for case_id=%s after execution error: %s",
                        case_id,
                        refine_exc
                    )

        l1_status = "FAIL" if not l1_passed else ("WARN" if l1_warning else "OK")
        print(f"[Agent 3] Executed Case {case_id} | Success: {success} | Time: {exec_time:.2f}ms | L1={l1_status} | L2={'FAIL' if not l2_passed_detail else 'OK'}")

        return ExecutionResult(
            case_id=case_id,
            success=success,
            l1_passed=l1_passed,
            l2_passed=l2_ready and l2_passed_detail,
            error_message=error_msg,
            raw_response=raw_resp,
            execution_time_ms=exec_time,
            underlying_logs=underlying_logs,
            l1_warning=l1_warning,
            l2_result=l2_result_dict,
            l1_violation_details=l1_violation_details
        )

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Agent 3] Starting Execution & Gating for {len(state.current_test_cases)} cases...")
        
        db_config = state.db_config
        if not db_config or not db_config.endpoint:
            print("[Agent 3] No DB endpoint found in state! Failing all tests.")
            return state
            
        # Initialize Adapter
        adapter = None
        db_name_lower = db_config.db_name.lower() if db_config and db_config.db_name else ""
        if db_name_lower == "milvus":
            adapter = MilvusAdapter(endpoint=db_config.endpoint)
        elif db_name_lower == "qdrant":
            adapter = QdrantAdapter(endpoint=db_config.endpoint)
        elif db_name_lower == "weaviate":
            adapter = WeaviateAdapter(endpoint=db_config.endpoint)
        else:
            print(f"[Agent 3] Unsupported DB adapter: {db_config.db_name}")
            return state
            
        # L2 Runtime Gating: Connect to DB
        l2_ready = adapter.connect()
        if not l2_ready:
            print("[Agent 3] L2 Gating Failed: Cannot connect to database.")
            
        # Collection Initialization for testing
        import time
        # Use timestamp to guarantee unique collection name, avoiding Milvus drop-latency issues
        collection_name = f"run_{state.iteration_count}_{int(time.time())}"
        setup_success = False
        real_collection_name = collection_name
        
        if l2_ready:
            # We assume a fixed dimension for the collection based on the first test case
            # In a more complex fuzzer, we'd create collections per dimension tested
            test_dim = state.current_test_cases[0].dimension if state.current_test_cases else 128
            if isinstance(test_dim, dict):
                 test_dim = 128 # fallback if parsing got weird
                 
            # Fix: Ensure dimension is an integer and within reasonable bounds for initialization
            try:
                test_dim = int(test_dim)
                dim_limit = 32768  # default fallback
                l1_api = state.contracts.l1_api if hasattr(state.contracts, 'l1_api') else state.contracts.get('l1_api', {})
                dc_from_contract = l1_api.get("dimension_constraint")
                if dc_from_contract and isinstance(dc_from_contract, dict) and dc_from_contract.get("max"):
                    dim_limit = dc_from_contract["max"]
                if test_dim > dim_limit:
                    test_dim = int(dc_from_contract.get("min", 128)) if dc_from_contract and isinstance(dc_from_contract, dict) and dc_from_contract.get("min") else 128
            except Exception as e:
                logger.warning("[Agent 3] Invalid test_dim=%r, fallback to 128: %s", test_dim, e)
                test_dim = 128
                 
            # v2.1 Software Harness: Use setup_harness hook
            setup_success = adapter.setup_harness(collection_name, dimension=test_dim)
            
            # 这里的 collection_name 可能会被 adapter 修改（加前缀），我们需要同步
            real_collection_name = getattr(adapter, 'current_collection_name', collection_name)
            
            if setup_success:
                # WBS 1.3 & v3.3: Inject Controlled Data + Expected Ground Truth
                all_gt_data = []
                for tc in state.current_test_cases:
                    is_dict = isinstance(tc, dict)
                    gt = tc.get('expected_ground_truth', []) if is_dict else getattr(tc, 'expected_ground_truth', [])
                    all_gt_data.extend(gt)
                
                print(f"[Agent 3] Collected {len(all_gt_data)} ground truth items from test cases.")
                
                from src.data_generator import ControlledDataGenerator
                generator = ControlledDataGenerator(scenario=state.business_scenario)
                # Generate some noise to fill the space
                corpus = generator.generate_corpus(size=50, noise_ratio=0.5)
                
                # Combine GT data with noise
                final_texts = []
                final_payloads = []
                
                # Process Ground Truth items
                for item in all_gt_data:
                    if isinstance(item, dict) and "text" in item:
                        final_texts.append(item["text"])
                        p = item.get("metadata", {}).copy()
                        p["text"] = item["text"]
                        final_payloads.append(p)
                
                # Process Corpus items
                for item in corpus:
                    if isinstance(item, dict) and "text" in item:
                        final_texts.append(item["text"])
                        p = item.get("metadata", {}).copy()
                        p["text"] = item["text"]
                        final_payloads.append(p)
                
                # Embed all data
                if final_texts:
                    print(f"[Agent 3] Embedding {len(final_texts)} data items for injection...")
                    final_vecs = [self._get_embedding(text, test_dim) for text in final_texts]
                    adapter.insert_data(real_collection_name, final_vecs, final_payloads)
                    print(f"[Agent 3] Successfully injected {len(final_texts)} items (GT + Noise) into {real_collection_name}")
                    state.current_collection = real_collection_name
                    state.data_inserted = True
                else:
                    print("[Agent 3] Warning: No valid data items found for injection.")
            else:
                print(f"[Agent 3] CRITICAL: Failed to setup harness for collection {real_collection_name}. Failing all test cases.")
                l2_ready = False # Fail the gate if we can't even create the collection

        results = []

        # Run all test cases concurrently
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Execute each case using the real collection name
        tasks = [self._execute_single_case(tc, adapter, real_collection_name, l2_ready, state) for tc in state.current_test_cases]

        if tasks:
            try:
                results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                # Check if any results are exceptions
                for i, r in enumerate(results):
                    if isinstance(r, Exception):
                        print(f"[Agent 3] Task {i} raised exception: {r}")
                        # Create a failed execution result
                        results[i] = ExecutionResult(
                            case_id=state.current_test_cases[i].case_id if not isinstance(state.current_test_cases[i], dict) else state.current_test_cases[i].get('case_id'),
                            success=False,
                            l1_passed=True,
                            l2_passed=l2_ready,
                            error_message=f"Task exception: {str(r)}",
                            raw_response=None,
                            execution_time_ms=0.0,
                            underlying_logs=str(r),
                            l2_result={"passed": False, "reason": "Task exception during execution"}
                        )
            except OSError as oe:
                import traceback
                print(f"[Agent 3] CRITICAL OS ERROR during execution: [Errno {oe.errno}] {oe}")
                traceback.print_exc()
                # Create failed results for all test cases
                results = [
                    ExecutionResult(
                        case_id=tc.case_id if not isinstance(tc, dict) else tc.get('case_id'),
                        success=False,
                        l1_passed=True,
                        l2_passed=l2_ready,
                        error_message=f"OS Error [Errno {oe.errno}]: {str(oe)}",
                        raw_response=None,
                        execution_time_ms=0.0,
                        underlying_logs=traceback.format_exc(),
                        l2_result={"passed": False, "reason": f"OS Error [Errno {oe.errno}]"}
                    )
                    for tc in state.current_test_cases
                ]
            except Exception as e:
                import traceback
                print(f"[Agent 3] CRITICAL ERROR during execution: {e}")
                traceback.print_exc()
                results = [
                    ExecutionResult(
                        case_id=tc.case_id if not isinstance(tc, dict) else tc.get('case_id'),
                        success=False,
                        l1_passed=True,
                        l2_passed=l2_ready,
                        error_message=f"Execution error: {str(e)}",
                        raw_response=None,
                        execution_time_ms=0.0,
                        underlying_logs=traceback.format_exc(),
                        l2_result={"passed": False, "reason": f"Execution error: {str(e)}"}
                    )
                    for tc in state.current_test_cases
                ]

        if l2_ready:
            # v2.1 Software Harness: Use teardown_harness hook
            try:
                adapter.teardown_harness(real_collection_name)
                adapter.disconnect()
            except Exception as teardown_err:
                print(f"[Agent 3] Warning: Teardown error: {teardown_err}")

        state.execution_results = list(results)
        
        # WBS 2.0: Consecutive Failure Tracking
        # A failure here means ALL test cases in this batch were blocked by L1/L2 or crashed
        batch_failed = True
        if results:
            for res in results:
                # If at least one test case passed L1 and executed successfully, the batch is not a complete failure
                if res.l1_passed and res.success:
                    batch_failed = False
                    break
        
        if batch_failed:
            state.consecutive_failures += 1
            print(f"[Agent 3] Batch completely failed. Consecutive failures: {state.consecutive_failures}")
        else:
            state.consecutive_failures = 0
            
        return state

def agent3_execution_gating(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = ExecutionGatingAgent()
    return agent.execute(state)
