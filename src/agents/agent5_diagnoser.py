from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from src.state import WorkflowState, DefectReport, OracleValidation, ExecutionResult, TestCase
from src.knowledge_base import DefectKnowledgeBase, BugRecord
from src.telemetry import telemetry_sink, TelemetryEvent
from src.docker_probe import DockerLogsProbe

logger = logging.getLogger(__name__)

class DefectDiagnoserAgent:
    """
    Agent 5: Defect Diagnoser & Reporter
    Responsibilities:
    1. Classify defects using the Four-Type Bug Classification Tree.
    2. Assemble the evidence chain (L1/L2/L3).
    3. Generate feedback for the next fuzzing iteration.
    4. Decide loop termination.
    """
    
    def __init__(self):
        self.kb = DefectKnowledgeBase()
        self._container_name = "milvus-standalone"  # default fallback

    def _resolve_container_name(self, state=None):
        """Resolve container name from db_config or use default."""
        if state and hasattr(state, 'db_config') and state.db_config:
            db_name = getattr(state.db_config, 'db_name', None) or ""
            db_lower = db_name.lower()
            if 'qdrant' in db_lower:
                return 'qdrant'
            elif 'weaviate' in db_lower:
                return 'weaviate'
            elif 'milvus' in db_lower:
                return 'milvus-standalone'
        return self._container_name

    def classify_defect_v2(
        self,
        test_case: TestCase,
        result: ExecutionResult,
        oracle_result: dict
    ) -> Optional[str]:
        """
        Classify defect using theoretical framework decision tree (Four-Type Classification).

        Decision Tree:
                        L1: Contract valid?
                             |
               ┌─────────────┴─────────────┐
              NO                           YES
               |                            |
             Exec success?              Exec success?
           ┌──┴──┐                      ┌───┴───┐
          YES   NO                     NO     YES
           |     |                      |       |
        Type-1 Type-2              L2 pass?  L2 pass?
                                      |       |
                                    NO       YES
                                     |        |
                                  Type-2.PF  Oracle pass?
                                             |
                                           NO     YES
                                            |       |
                                         Type-4  Type-3

        Returns one of: "Type-1", "Type-2", "Type-2.PF", "Type-3", "Type-4", or None (no defect)
        """
        is_res_dict = isinstance(result, dict)
        l1_warning = result.get('l1_warning') if is_res_dict else getattr(result, 'l1_warning', None)
        l2_result = result.get('l2_result') if is_res_dict else getattr(result, 'l2_result', None)
        exec_success = result.get('success') if is_res_dict else result.success

        is_oracle_dict = isinstance(oracle_result, dict)
        oracle_passed = oracle_result.get('passed') if is_oracle_dict else getattr(oracle_result, 'passed', False)

        # Determine L1 passed with severity awareness
        l1_violation_details = result.get('l1_violation_details') if is_res_dict else getattr(result, 'l1_violation_details', None)

        if l1_violation_details:
            severity = l1_violation_details.get('severity', 'soft') if isinstance(l1_violation_details, dict) else 'soft'
            l1_passed = False  # Any violation means L1 failed
            logger.info(f"[Agent 5] L1 Violation | Severity={severity} | Details={l1_violation_details}")
        else:
            l1_passed = l1_warning is None

        # Determine L2 passed from l2_result dict
        l2_passed = True
        if l2_result and isinstance(l2_result, dict):
            l2_passed = l2_result.get("passed", True)

        classification = None

        # === IBSA-Aware Pre-Classification ===
        # IBSA (In-Boundary Semantically Anomalous) cases should be classified
        # as Type-3 or Type-4 (Oracle violations), NOT as Type-2 (Poor Diagnostics).
        # Detect by case_id prefix AND execution characteristics.
        case_id = getattr(result, 'case_id', '') or ''
        is_ibsa_case = 'ibsa_' in case_id.lower()

        if is_ibsa_case:
            # Check if execution completed without SDK-level rejection
            error_str = str(getattr(result, 'error', '') or '')
            has_sdk_rejection = any(
                reject_keyword in error_str.lower()
                for reject_keyword in [
                    'paramerror', 'invalid', 'not supported',
                    'milvusexception', 'weaviateerror', 'qdrant',
                    'valueerror', 'typeerror', 'dimension'
                ]
            )
            # Also check status - if it's not an error state, it likely executed through Oracle
            status = getattr(result, 'status', '') or ''
            executed_ok = status.lower() in ('success', 'passed', 'ok', 'completed')

            if executed_ok or (not has_sdk_rejection and (error_str == '' or error_str == 'None')):
                # IBSA case that passed L1/L2 and reached Oracle layer
                # Force into Type-3/Type-4 classification path below
                pass  # The flag is_ibsa_case will be used in the tree logic below
            elif has_sdk_rejection:
                # IBSA case hit SDK rejection - may still be Type-1 or valid Type-2
                is_ibsa_case = False  # Let normal classification handle it

        # === L2-Gate-Blocked Detection & Re-Route ===
        # ROOT CAUSE FIX for Milvus 100% Type-2 issue:
        # When Agent3's L2 gating blocks execution (l2_ready=False), the ExecutionResult
        # has success=False with error_message like "L2 Gating Failed: Database not ready".
        # The decision tree treats this as "exec failed" → Type-2, but the case NEVER EXECUTED.
        # We must detect this pre-execution block and re-route based on actual evidence.
        is_res_dict = isinstance(result, dict)
        error_message = result.get('error_message') if is_res_dict else getattr(result, 'error_message', None)
        error_str = str(error_message or '').lower()
        l2_gate_blocked = any(
            kw in error_str
            for kw in ['l2 gating failed', 'database not ready', 'no active collection',
                       'collection empty', 'not ready or disconnected']
        )
        if l2_gate_blocked and not exec_success:
            is_oracle_dict_local = isinstance(oracle_result, dict)
            oracle_passed_local = oracle_result.get('passed') if is_oracle_dict_local else getattr(oracle_result, 'passed', False)
            oracle_anomalies_local = oracle_result.get('anomalies', []) if is_oracle_dict_local else []
            has_traditional_anomaly_local = any(
                a.get('type') in {'sorting_anomaly', 'count_mismatch', 'dimension_mismatch',
                                  'metric_range_violation', 'l1_bypass_anomaly',
                                  'unexpected_failure', 'distance_invalid'}
                if isinstance(a, dict) else False
                for a in oracle_anomalies_local
            )
            if has_traditional_anomaly_local:
                classification = "Type-3"
                logger.info(
                    "[Agent 5] L2GateBlock-ReRoute | L2 blocked (never executed) | TraditionalOracle=ANOMALY => Type-3 "
                    "(Oracle found traditional violation despite no execution)"
                )
            elif not oracle_passed_local:
                classification = "Type-4"
                logger.info(
                    "[Agent 5] L2GateBlock-ReRoute | L2 blocked (never executed) | Oracle=FAIL => Type-4 "
                    "(Semantic oracle violation despite no execution)"
                )
            elif is_ibsa_case:
                classification = "Type-4"
                logger.info(
                    "[Agent 5] L2GateBlock-ReRoute | L2 blocked | IBSA case | Oracle=PASSED => Type-4 "
                    "(IBSA semantic anomaly implied)"
                )
            else:
                classification = None
                logger.info(
                    "[Agent 5] L2GateBlock-Skip | L2 blocked (never executed) | No oracle evidence | Not IBSA => No defect "
                    "(Pre-execution block is an environment issue, not a database defect)"
                )
            return classification

        # --- Decision tree implementation ---
        if not l1_passed:
            # L1 contract violated
            if exec_success:
                classification = "Type-1"  # Illegal request succeeded (contract bypass)
                logger.info(
                    "[Agent 5] DecisionTree | L1=FAIL | Exec=SUCCESS => Type-1 "
                    "(Illegal request succeeded - contract bypass)"
                )
            else:
                classification = "Type-2"  # Illegal request failed (poor diagnostics expected)
                # When we detect a Type-2 candidate, check if it's actually an IBSA case
                # that should be re-routed to Type-3/Type-4
                if is_ibsa_case:
                    # IBSA cases with oracle-evidence should be Type-3 or Type-4
                    if oracle_anomalies and len(oracle_anomalies) > 0:
                        classification = "Type-3"
                    elif not oracle_passed:
                        classification = "Type-4"
                    else:
                        # Even without explicit oracle evidence, IBSA implies semantic anomaly
                        classification = "Type-4"
                logger.info(
                    "[Agent 5] DecisionTree | L1=FAIL | Exec=FAIL => Type-2 "
                    "(Illegal request failed - poor diagnostics expected)"
                )
        else:
            # L1 contract valid
            if not exec_success:
                if not l2_passed:
                    classification = "Type-2.PF"  # Precondition failure at runtime
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=FAIL | L2=FAIL => Type-2.PF "
                        "(Precondition failure)"
                    )
                else:
                    classification = "Type-2"  # Unexpected error with good diagnostics
                    # When we detect a Type-2 candidate, check if it's actually an IBSA case
                    # that should be re-routed to Type-3/Type-4
                    if is_ibsa_case:
                        # IBSA cases with oracle-evidence should be Type-3 or Type-4
                        if oracle_anomalies and len(oracle_anomalies) > 0:
                            classification = "Type-3"
                        elif not oracle_passed:
                            classification = "Type-4"
                        else:
                            # Even without explicit oracle evidence, IBSA implies semantic anomaly
                            classification = "Type-4"
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=FAIL | L2=PASS => Type-2 "
                        "(Unexpected error with good runtime state)"
                    )
            else:
                # Execution succeeded, check oracle
                # Extract traditional (non-LLM) anomalies from oracle_result
                is_oracle_dict = isinstance(oracle_result, dict)
                oracle_anomalies = oracle_result.get('anomalies', []) if is_oracle_dict else []

                # Identify traditional oracle anomalies (non-semantic)
                traditional_anomaly_types = {'sorting_anomaly', 'count_mismatch', 'dimension_mismatch',
                                             'metric_range_violation', 'l1_bypass_anomaly',
                                             'unexpected_failure', 'distance_invalid'}
                has_traditional_anomaly = any(
                    a.get('type') in traditional_anomaly_types if isinstance(a, dict) else False
                    for a in oracle_anomalies
                )

                if has_traditional_anomaly:
                    classification = "Type-3"  # Traditional Oracle Violation (NEW PATH!)
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=SUCCESS | TraditionalOracle=ANOMALY => Type-3 "
                        "(Traditional oracle violation detected)"
                    )
                elif not oracle_passed:
                    classification = "Type-4"  # Semantic violation (LLM oracle rejected)
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=SUCCESS | Oracle=FAIL => Type-4 "
                        "(Semantic violation)"
                    )
                else:
                    classification = None  # No defect
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=SUCCESS | Oracle=PASS => No defect"
                    )

        return classification
        
    def _classify_defect(self, tc: TestCase, exec_res: ExecutionResult, oracle_res: OracleValidation, state: WorkflowState = None) -> DefectReport:
        """
        Decision Tree for Bug Classification (v2 - aligned with theoretical framework).

        Uses classify_defect_v2() for core four-type decision tree logic,
        then enriches with evidence gathering and report generation.

        Classification types:
        - Type-1:   Illegal request succeeded (contract bypass)
        - Type-2:   Illegal request failed / Unexpected error with good diagnostics
        - Type-2.PF: Precondition failure at runtime (L2 not ready)
        - Type-3:   Traditional Oracle Violation (passed all checks)
        - Type-4:   Semantic Oracle Violation (oracle rejected result)
        """
        is_tc_dict = isinstance(tc, dict)
        case_id = tc.get('case_id') if is_tc_dict else getattr(tc, 'case_id')
        query_text = tc.get('query_text', '') if is_tc_dict else getattr(tc, 'query_text', '')
        source_url = tc.get('assigned_source_url') if is_tc_dict else getattr(tc, 'assigned_source_url', None)

        is_exec_dict = isinstance(exec_res, dict)
        error_msg = exec_res.get('error_message') if is_exec_dict else exec_res.error_message
        underlying_logs = exec_res.get('underlying_logs') if is_exec_dict else getattr(exec_res, 'underlying_logs', None)

        is_oracle_dict = isinstance(oracle_res, dict)
        passed = oracle_res.get('passed') if is_oracle_dict else oracle_res.passed
        anomalies = oracle_res.get('anomalies', []) if is_oracle_dict else oracle_res.anomalies
        explanation = oracle_res.get('explanation', '') if is_oracle_dict else oracle_res.explanation

        # --- Core classification via v2 decision tree ---
        oracle_result_dict = {
            "passed": passed,
            "anomalies": anomalies,
            "explanation": explanation
        }
        v2_type = self.classify_defect_v2(tc, exec_res, oracle_result_dict)

        # Map v2 type to bug_type label and evidence level
        type_mapping = {
            "Type-1": ("Type-1 (Illegal Success)", "L1"),
            "Type-2": ("Type-2 (Poor Diagnostics)", "L2"),
            "Type-2.PF": ("Type-2 (Precondition Failure)", "L2"),
            "Type-3": ("Type-3 (Traditional Oracle)", "L2/L3"),
            "Type-4": ("Type-4 (Semantic Oracle)", "L3"),
        }

        if v2_type is None:
            return None

        bug_type, evidence_level = type_mapping.get(v2_type, (v2_type, "Unknown"))

        # Build root cause analysis based on classification type
        root_cause = str(explanation) if explanation is not None else ""

        if v2_type == "Type-1":
            root_cause = "Illegal request was executed successfully (Bypassed L1 contract validation)."
            if error_msg:
                root_cause += f" Error message (unexpected): {error_msg}"
        elif v2_type == "Type-2":
            root_cause = f"Request failed with error: {error_msg}. Poor or vague diagnostics."
        elif v2_type == "Type-2.PF":
            l2_result = exec_res.get('l2_result') if is_exec_dict else getattr(exec_res, 'l2_result', None)
            l2_reason = l2_result.get("reason", "Unknown") if l2_result and isinstance(l2_result, dict) else "Unknown"
            root_cause = f"Runtime precondition failure: {l2_reason}. Original error: {error_msg}"
        elif v2_type == "Type-4":
            root_cause = f"Semantic oracle violation: {explanation}"
        elif v2_type == "Type-3":
            root_cause = f"Traditional oracle violation detected in results."

        # Evidence enrichment: Fetch deep Docker logs for certain defect types
        log_requiring_types = ["Type-2", "Type-2.PF", "Type-3"]
        if any(bug_type.startswith(t) for t in log_requiring_types):
            print(f"[Agent 5] {bug_type} detected. Fetching deep Docker logs for evidence...")
            container_name = self._resolve_container_name(state)
            probe = DockerLogsProbe(container_name=container_name)
            docker_logs = probe.fetch_recent_logs(tail=100)
            if docker_logs:
                root_cause = f"{root_cause}\n\n[Deep Observability Logs]:\n{docker_logs}"
        elif underlying_logs:
            root_cause = f"{root_cause}\n\n[Pre-captured Docker Logs]:\n{underlying_logs[:1000]}"

        db_name = f"{state.db_config.db_name} {state.db_config.version}" if state and state.db_config else "Unknown DB"

        # Propagate L1 violation details from execution result to defect report
        l1_vd = exec_res.get('l1_violation_details') if is_exec_dict else getattr(exec_res, 'l1_violation_details', None)

        logger.info(
            "[Agent 5] Classified | Case %s => %s | Evidence=%s | RootCause=%s",
            case_id, bug_type, evidence_level, root_cause[:100]
        )

        return DefectReport(
            case_id=case_id,
            bug_type=bug_type,
            evidence_level=evidence_level,
            root_cause_analysis=root_cause,
            title=f"{bug_type} in {case_id}",
            operation=query_text[:50],
            error_message=str(error_msg) if error_msg else "",
            database=db_name,
            source_url=source_url,
            l1_violation_details=l1_vd
        )

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Agent 5] Diagnosing defects for {len(state.oracle_results)} oracle results...")
        
        # Maps for quick lookup
        tc_map = { (tc.get('case_id') if isinstance(tc, dict) else tc.case_id): tc for tc in state.current_test_cases }
        exec_map = { (e.get('case_id') if isinstance(e, dict) else e.case_id): e for e in state.execution_results }
        
        new_defects = []
        feedback_points = []
        
        for oracle_res in state.oracle_results:
            is_dict = isinstance(oracle_res, dict)
            case_id = oracle_res.get('case_id') if is_dict else oracle_res.case_id
            
            tc = tc_map.get(case_id)
            exec_res = exec_map.get(case_id)
            
            if not tc or not exec_res:
                continue
                
            defect = self._classify_defect(tc, exec_res, oracle_res, state=state)
            if defect:
                # Ensure root_cause_analysis is a string to avoid subscriptable error
                if defect.root_cause_analysis is None:
                    defect.root_cause_analysis = ""
                    
                new_defects.append(defect)
                feedback_str = f"Case {case_id} failed with {defect.bug_type}: {defect.root_cause_analysis[:100]}"
                if defect.source_url:
                    feedback_str += f" (Source: {defect.source_url})"
                feedback_points.append(feedback_str)
                print(f"[Agent 5] Defect found in {case_id}: {defect.bug_type}. Source URL: {defect.source_url}")
                
                # WBS 3.1: Write-Ahead Logging for Defects
                try:
                    telemetry_sink.log_event(TelemetryEvent(
                        trace_id=state.run_id,
                        node_name="agent5_diagnoser",
                        event_type="DEFECT_FOUND",
                        state_delta={"defect": defect.model_dump(mode='json')}
                    ))
                except Exception as e:
                    print(f"[Agent 5] Failed to log atomic defect: {e}")

                # WBS 2.1: Store defect in Knowledge Base
                try:
                    record = BugRecord(
                        case_id=defect.case_id,
                        bug_type=defect.bug_type,
                        root_cause_analysis=defect.root_cause_analysis,
                        evidence_level=defect.evidence_level
                    )
                    self.kb.add_defect(record)
                except Exception as e:
                    print(f"[Agent 5] Failed to add defect to KB: {e}")
                
        state.defect_reports.extend(new_defects)
        print(f"[Agent 5] Found {len(new_defects)} potential defects.")
        
        # Generate Fuzzing Feedback
        if feedback_points:
            state.fuzzing_feedback = "Previous loop found issues: " + " | ".join(feedback_points[:3]) + ". Please mutate these vectors or query_texts to find the edge of this bug."
        else:
            state.fuzzing_feedback = "Previous loop found no issues. Try more aggressive adversarial semantic queries."
            
        # Loop Control
        state.iteration_count += 1
        if state.iteration_count >= state.max_iterations:
            print("[Agent 5] Max iterations reached. Terminating fuzzing loop.")
            state.should_terminate = True
        else:
            print(f"[Agent 5] Advancing to iteration {state.iteration_count}.")
            # Note: We can also terminate early if we found enough unique bugs
            
        return state

def agent5_defect_diagnoser(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = DefectDiagnoserAgent()
    return agent.execute(state)
