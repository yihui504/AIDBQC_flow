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
        self.probe = DockerLogsProbe(container_name="milvus-standalone")

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

        # Determine L1 passed: L1 passed means no warning (contract is valid)
        l1_passed = l1_warning is None

        # Determine L2 passed from l2_result dict
        l2_passed = True
        if l2_result and isinstance(l2_result, dict):
            l2_passed = l2_result.get("passed", True)

        classification = None

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
                    logger.info(
                        "[Agent 5] DecisionTree | L1=PASS | Exec=FAIL | L2=PASS => Type-2 "
                        "(Unexpected error with good runtime state)"
                    )
            else:
                # Execution succeeded, check oracle
                if not oracle_passed:
                    classification = "Type-4"  # Semantic violation (oracle rejected)
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
            docker_logs = self.probe.fetch_recent_logs(tail=100)
            if docker_logs:
                root_cause = f"{root_cause}\n\n[Deep Observability Logs]:\n{docker_logs}"
        elif underlying_logs:
            root_cause = f"{root_cause}\n\n[Pre-captured Docker Logs]:\n{underlying_logs[:1000]}"

        db_name = f"{state.db_config.db_name} {state.db_config.version}" if state and state.db_config else "Unknown DB"

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
            source_url=source_url
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
