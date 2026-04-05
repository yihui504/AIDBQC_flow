import os
import sys
import uuid
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from src.state import WorkflowState, StateManager
from src.graph import build_workflow
from src.telemetry import telemetry_sink, TelemetryEvent, log_node_execution
from src.config import ConfigLoader
from src.performance import performance_monitor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv()

def main():
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
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.info("Continuing with default configuration values...")

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
    
    initial_state = WorkflowState(
        run_id=run_id,
        target_db_input="请帮我深度测试一下 Milvus v2.6.12",
        business_scenario="We are building an e-commerce semantic search engine that needs to handle both dense and sparse vector retrievals with high concurrency.",
        max_token_budget=max_token_budget,
        max_iterations=max_iterations
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
        # Log ERROR event
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
