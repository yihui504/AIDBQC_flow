import os
import sys
import uuid
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from src.config import ConfigLoader
from src.critical_error_handler import (
    CriticalErrorHandler,
    get_global_critical_error_handler,
    initialize_global_critical_error_handler,
    CriticalErrorType
)
from src.docker_port_manager import (
    DockerPortManager,
    get_global_port_manager,
    initialize_global_port_manager
)
from src.mre_generator import (
    MREGenerator,
    generate_mre_from_exception
)
from src.root_cause_analyzer import (
    RootCauseAnalyzer,
    RootCauseCategory,
    SeverityLevel
)
from src.standardized_error_report import (
    ErrorReportGenerator,
    ReportFormat
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _ensure_utf8_console() -> None:
    """Force UTF-8 encoding for Windows console output."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def _normalize_text(value) -> str:
    """Normalize arbitrary values to a lowercase string for guard checks."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_weaviate_1369_target(target_db_input: str) -> bool:
    """Return True when the target explicitly points to Weaviate 1.36.9 or Qdrant v1.17.1."""
    text = _normalize_text(target_db_input)
    return (("weaviate" in text) and ("1.36.9" in text)) or (("qdrant" in text) and ("1.17.1" in text))


def _contains_forbidden_terms(text: str, forbidden_terms) -> bool:
    """Check whether text contains any forbidden degraded/simulated execution markers."""
    normalized = _normalize_text(text)
    return any(term in normalized for term in forbidden_terms)


def _extract_field(item, field_name: str):
    """Read field from either dicts or model-like objects."""
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


def _enforce_real_run_configuration(config_loader) -> None:
    """
    Enforce Task4 hard constraints:
    - target_db_input must be Weaviate 1.36.9
    - max_iterations must be exactly 4
    - target input must not include simulated/degraded markers
    """
    enabled = config_loader.get_bool("run_guard.enabled", default=True)
    if not enabled:
        logger.warning("[RunGuard] run_guard.enabled=false, runtime guard disabled")
        return

    target_db_input = config_loader.get("harness.target_db_input", "weaviate")
    max_iterations = config_loader.get_int("harness.max_iterations", 8)
    forbidden_terms = config_loader.get(
        "run_guard.forbidden_terms",
        ["degraded", "fallback", "simulate", "simulation", "mock", "fake", "降级", "替代", "模拟"],
    )

    if _contains_forbidden_terms(target_db_input, forbidden_terms):
        raise RuntimeError(
            "[RunGuard] target_db_input contains degraded/simulated marker. "
            "Real-run mode forbids fallback/mock/simulation paths."
        )

    enforce_weaviate = config_loader.get_bool("run_guard.enforce_weaviate_1369", default=True)
    if enforce_weaviate and not _is_weaviate_1369_target(str(target_db_input)):
        raise RuntimeError(
            f"[RunGuard] Invalid target_db_input={target_db_input!r}; "
            "expected Weaviate 1.36.9 or Qdrant v1.17.1 for this live run."
        )

    enforce_iterations = config_loader.get_bool("run_guard.enforce_max_iterations_4", default=True)
    if enforce_iterations and max_iterations != 4:
        raise RuntimeError(
            f"[RunGuard] Invalid harness.max_iterations={max_iterations}; expected exactly 4."
        )

    logger.info(
        "[RunGuard] Real-run configuration validated: target_db_input=%s, max_iterations=%s",
        target_db_input,
        max_iterations,
    )


def _enforce_no_degraded_runtime_paths(node_name: str, state_update: dict, config_loader) -> None:
    """Fail-closed if degraded/simulated runtime paths are detected."""
    enabled = config_loader.get_bool("run_guard.enabled", default=True)
    if not enabled:
        return

    forbidden_terms = config_loader.get(
        "run_guard.forbidden_terms",
        ["degraded", "fallback", "simulate", "simulation", "mock", "fake", "降级", "替代", "模拟"],
    )

    # Guard 1: explicit verifier degraded verdict/status
    if node_name == "agent6_verifier":
        for defect in state_update.get("defect_reports", []) or []:
            verification_status = _normalize_text(_extract_field(defect, "verification_status"))
            verifier_verdict = _normalize_text(_extract_field(defect, "verifier_verdict"))
            if verification_status == "degraded" or verifier_verdict == "degraded":
                case_id = _extract_field(defect, "case_id")
                raise RuntimeError(
                    f"[RunGuard] Detected degraded verifier output for case {case_id}; aborting fail-closed."
                )

    # Guard 2: scan common mode/status keys for forbidden simulation markers
    guarded_keys = ["execution_mode", "run_mode", "path_type", "mode", "strategy"]
    for key in guarded_keys:
        value = state_update.get(key)
        if value is not None and _contains_forbidden_terms(value, forbidden_terms):
            raise RuntimeError(
                f"[RunGuard] Detected forbidden runtime path marker in state_update[{key!r}]={value!r}"
            )

# Load environment variables
load_dotenv()

def main():
    _ensure_utf8_console()
    from src.state import WorkflowState, StateManager
    from src.graph import build_workflow
    from src.telemetry import telemetry_sink, TelemetryEvent, log_node_execution
    from src.performance import performance_monitor

    print("=== AI-DB-QC Multi-Agent Pipeline Runner ===")

    # Load configuration
    config_loader = ConfigLoader(config_path=".trae/config.yaml")
    try:
        config_loader.load()
        config_loader.override_from_env()
        
        # Validate configuration
        validation_errors = config_loader.validate()
        if validation_errors:
            logger.warning("Configuration validation warnings:")
            for error in validation_errors:
                logger.warning(f"  - {error}")
        
        logger.info("Configuration loaded successfully")
        _enforce_real_run_configuration(config_loader)
        
        # Initialize critical error handler after configuration is loaded
        critical_error_enabled = config_loader.get_bool("critical_error_handler.enabled", default=True)
        if critical_error_enabled:
            critical_error_handler = initialize_global_critical_error_handler(
                log_dir=config_loader.get("critical_error_handler.log_dir", ".trae/logs"),
                state_dir=config_loader.get("critical_error_handler.state_dir", ".trae/runs"),
                enable_auto_cleanup=config_loader.get_bool("critical_error_handler.enable_auto_cleanup", default=True),
                max_shutdown_time_seconds=config_loader.get_int("critical_error_handler.max_shutdown_time_seconds", 30)
            )
        else:
            critical_error_handler = get_global_critical_error_handler()
            logger.info("Critical error handler disabled in configuration")
        
        # Initialize Docker port manager after configuration is loaded
        port_manager_enabled = config_loader.get_bool("docker_port_manager.enabled", default=True)
        if port_manager_enabled:
            port_manager = initialize_global_port_manager(
                state_dir=config_loader.get("docker_port_manager.state_dir", ".trae/port_manager"),
                enable_auto_cleanup=config_loader.get_bool("docker_port_manager.enable_auto_cleanup", default=True),
                cleanup_interval_seconds=config_loader.get_int("docker_port_manager.cleanup_interval_seconds", 300),
                orphan_timeout_minutes=config_loader.get_int("docker_port_manager.orphan_timeout_minutes", 60)
            )
        else:
            port_manager = get_global_port_manager()
            logger.info("Docker port manager disabled in configuration")
        
        # Register cleanup handlers for critical errors
        critical_error_handler.register_cleanup_handler(port_manager.cleanup_orphaned_ports)
        
        logger.info("Critical error handler and Docker port manager initialized")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Check for required API keys
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        print("ERROR: No API key found. Please set DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, or ZHIPUAI_API_KEY in the .env file.")
        print("Please copy .env.example to .env and add your API key.")
        return

    # 1. Initialize the State
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    print(f"Initializing Run ID: {run_id}")

    # Initialize StateManager
    state_manager = StateManager(base_dir=".trae/runs")
    
    # Get configuration values
    max_token_budget = config_loader.get_int("harness.max_token_budget", 1000000)
    max_iterations = config_loader.get_int("harness.max_iterations", 8)
    target_db_input = config_loader.get("harness.target_db_input", "weaviate")
    from_scratch = config_loader.get_bool("harness.from_scratch", default=False)
    
    initial_state = WorkflowState(
        run_id=run_id,
        target_db_input=str(target_db_input),
        business_scenario="We are building an e-commerce semantic search engine that needs to handle both dense and sparse vector retrievals with high concurrency.",
        max_token_budget=max_token_budget,
        max_iterations=max_iterations,
        from_scratch=from_scratch
    )
    
    # 2. Build the LangGraph Workflow
    app = build_workflow()
    
    # 3. Execute the Graph
    print("\n>>> Starting Pipeline Execution...\n")
    
    # In LangGraph, we need to pass a config for the Checkpointer
    config = {"configurable": {"thread_id": run_id}}
    
    # Track tokens for telemetry and state persistence
    current_total_tokens = initial_state.total_tokens_used
    current_state = initial_state  # Track complete state for saving

    # Log Pipeline START
    telemetry_sink.log_event(TelemetryEvent(
        trace_id=run_id,
        node_name="pipeline",
        event_type="START",
        token_usage=0,
        state_delta={"target_db": initial_state.target_db_input}
    ))

    performance_monitor.start()
    performance_monitor.snapshot("pipeline_start")

    # Save initial state
    state_manager.save_state(run_id, current_state)
    print(f">>> State initialized and saved to .trae/runs/{run_id}/state.json")

    try:
        # stream() lets us see the output of each node as it finishes.
        for output in app.stream(initial_state.model_dump(), config=config):
            for node_name, state_update in output.items():
                print(f"\n--- Finished Node: {node_name} ---")

                # Merge state_update into current_state
                for key, value in state_update.items():
                    if hasattr(current_state, key):
                        setattr(current_state, key, value)

                # Telemetry Logging
                log_node_execution(
                    trace_id=run_id,
                    node_name=node_name,
                    state_update=state_update,
                    previous_tokens=current_total_tokens
                )

                _enforce_no_degraded_runtime_paths(node_name=node_name, state_update=state_update, config_loader=config_loader)

                performance_monitor.snapshot(node_name)

                # Update current total tokens
                if "total_tokens_used" in state_update:
                    current_total_tokens = state_update["total_tokens_used"]

                # Save state after key nodes for monitoring
                if node_name in ["agent3_executor", "agent4_oracle", "agent5_reflection"]:
                    try:
                        state_manager.save_state(run_id, current_state)
                        print(f">>> State saved after {node_name}")
                    except Exception as save_err:
                        print(f"Warning: Failed to save state: {save_err}")

                # If Agent 3 just finished, print execution results
                if node_name == "agent3_executor" and "execution_results" in state_update:
                    print(f"Execution completed for {len(state_update['execution_results'])} cases.")
                    for res in state_update['execution_results'][:3]: # Print first 3 to avoid spam
                        # Handle dict vs Pydantic model
                        if isinstance(res, dict):
                            print(f"  ID: {res.get('case_id')} | Success: {res.get('success')} | Time: {res.get('execution_time_ms', 0):.2f}ms")
                        else:
                            print(f"  ID: {res.case_id} | Success: {res.success} | Time: {res.execution_time_ms:.2f}ms")
                    if len(state_update['execution_results']) > 3:
                        print("  ... (more results omitted)")
                    
    except Exception as e:
        import traceback
        print(f"\nPipeline execution failed: {e}")
        traceback.print_exc()
        
        # Initialize report generator for MRE and root cause analysis
        report_generator = ErrorReportGenerator(
            reports_dir=".trae/error_reports"
        )
        
        # Generate MRE first
        mre = None
        try:
            mre = generate_mre_from_exception(
                exception=e,
                state=current_state,
                run_id=run_id,
                node_name="pipeline",
                additional_context={
                    "total_tokens_used": current_total_tokens,
                    "current_iteration": getattr(current_state, 'iteration_count', 0),
                    "target_db": getattr(current_state, 'target_db_input', 'unknown')
                }
            )
            print(f">>> MRE generated: {mre.mre_id}")
        except Exception as mre_err:
            print(f"Warning: Failed to generate MRE: {mre_err}")
        
        # Perform root cause analysis
        root_cause_result = None
        try:
            analyzer = RootCauseAnalyzer()
            root_cause_result = analyzer.analyze(
                exception=e,
                context={
                    "run_id": run_id,
                    "node": "pipeline",
                    "state": current_state.model_dump() if current_state else {}
                }
            )
            print(f">>> Root cause analyzed: {root_cause_result.category.value} (Severity: {root_cause_result.severity.value})")
            print(f">>> Root cause summary: {root_cause_result.summary}")
        except Exception as analysis_err:
            print(f"Warning: Failed to analyze root cause: {analysis_err}")
        
        # Generate and save standardized error report
        try:
            error_report = report_generator.generate_report(
                exception=e,
                root_cause_result=root_cause_result,
                mre=mre,
                additional_context={"run_id": run_id}
            )
            report_path_json = report_generator.save_report(error_report, format=ReportFormat.JSON)
            report_path_md = report_generator.save_report(error_report, format=ReportFormat.MARKDOWN)
            print(f">>> Error report saved: {report_path_json}")
            print(f">>> Markdown report: {report_path_md}")
            
            # Add to knowledge base
            if root_cause_result:
                report_generator.add_to_knowledge_base(error_report, root_cause_result)
        except Exception as report_err:
            print(f"Warning: Failed to generate error report: {report_err}")
        
        # Check if this is a critical error that requires immediate interruption
        critical_info = critical_error_handler.classify_critical_error(
            exception=e,
            context={"run_id": run_id, "node": "pipeline"}
        )
        
        if critical_info and critical_info.requires_immediate_shutdown:
            # Handle critical error with immediate shutdown
            print(f"\n!!! CRITICAL ERROR DETECTED: {critical_info.error_type.value} !!!")
            print(f"!!! Initiating immediate shutdown !!!")
            
            critical_error_handler.handle_critical_error(
                exception=e,
                run_id=run_id,
                additional_context={
                    "run_id": run_id,
                    "total_tokens_used": current_total_tokens,
                    "current_iteration": getattr(current_state, 'current_iteration', 0),
                    "mre_id": mre.mre_id if mre else None,
                    "root_cause": root_cause_result.category.value if root_cause_result else None,
                    "severity": root_cause_result.severity.value if root_cause_result else None
                }
            )
            # The handler will trigger system exit, so code below won't execute
        else:
            # Log ERROR event for non-critical errors
            telemetry_sink.log_event(TelemetryEvent(
                trace_id=run_id,
                node_name="pipeline",
                event_type="ERROR",
                token_usage=0,
                state_delta={"error_message": str(e)}
            ))
            
            # WBS 3.2: Emergency State Dump
            print(f">>> CRITICAL: Performing emergency state dump to .trae/runs/{run_id}/emergency_dump.json")
            try:
                dump_dir = os.path.join(".trae", "runs", run_id)
                os.makedirs(dump_dir, exist_ok=True)
                perf_summary = performance_monitor.to_dict()
                with open(os.path.join(dump_dir, "emergency_dump.json"), "w", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "run_id": run_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "is_critical": critical_info is not None if critical_info else False,
                        "timestamp": datetime.utcnow().isoformat(),
                        "performance": perf_summary
                    }, indent=2))
            except Exception as dump_err:
                print(f"Failed to perform emergency dump: {dump_err}")

            # Try to save current state even on error
            try:
                state_manager.save_state(run_id, current_state)
                print(f">>> State saved during error handling")
            except Exception as save_err:
                print(f"Warning: Failed to save state during error: {save_err}")

    finally:
        # Save final state
        try:
            state_manager.save_state(run_id, current_state)
            print(f">>> Final state saved to .trae/runs/{run_id}/state.json")
        except Exception as save_err:
            print(f"Warning: Failed to save final state: {save_err}")

        # Cleanup Docker port manager
        try:
            port_stats = port_manager.get_port_usage_stats()
            print(f">>> Port manager stats: {port_stats}")
            
            # Release ports for this run
            if run_id:
                active_allocations = port_manager.get_active_allocations()
                for allocation in active_allocations:
                    if allocation.run_id == run_id:
                        port_manager.release_port(allocation.port, force=True)
                        print(f">>> Released port {allocation.port} for run {run_id}")
        except Exception as port_err:
            print(f"Warning: Failed to cleanup port manager: {port_err}")

        # In v2.0 with hot sandboxes, we might not want to tear down immediately.
        # But for this script, we'll ask if we should keep it.
        # To make it fully automated but reusable, we can keep it alive
        # and only let a dedicated cleanup script kill it.
        # For now, we leave the cleanup code but comment it out to allow hot sandboxing.
        print("\n>>> Skipping Docker cleanup to maintain hot sandbox pool.")
        # run_dir = os.path.join(os.getcwd(), ".trae", "runs", run_id)
        # if os.path.exists(os.path.join(run_dir, "docker-compose.yml")):
        #     import subprocess
        #     try:
        #         subprocess.run(
        #             ["docker-compose", "down", "-v"],
        #             cwd=run_dir,
        #             check=True,
        #             capture_output=True
        #         )
        #         print("Successfully removed containers and volumes.")
        #     except Exception as e:
        #         print(f"Failed to clean up docker containers: {e}")
        
        # Shutdown critical error handler
        try:
            critical_error_handler._is_shutting_down = True
            print(">>> Critical error handler shutdown complete")
        except Exception as handler_err:
            print(f"Warning: Failed to shutdown critical error handler: {handler_err}")
                
    print("\n>>> Pipeline Execution Completed.")
    
    performance_monitor.snapshot("pipeline_end")
    perf_summary = performance_monitor.get_summary()
    if perf_summary.get("enabled"):
        print(f"\n=== Performance Summary ===")
        print(f"  Memory: {perf_summary['memory']['min_mb']:.1f}MB - {perf_summary['memory']['max_mb']:.1f}MB (avg: {perf_summary['memory']['avg_mb']:.1f}MB)")
        print(f"  CPU: {perf_summary['cpu']['min_percent']:.1f}% - {perf_summary['cpu']['max_percent']:.1f}% (avg: {perf_summary['cpu']['avg_percent']:.1f}%)")
        print(f"  Elapsed: {perf_summary['elapsed_seconds']:.1f}s")
    
    # Log Pipeline END
    telemetry_sink.log_event(TelemetryEvent(
        trace_id=run_id,
        node_name="pipeline",
        event_type="END",
        token_usage=current_total_tokens,
        state_delta={"status": "completed"}
    ))
    
    # Gracefully shutdown telemetry manager
    telemetry_sink.shutdown()

if __name__ == "__main__":
    main()
