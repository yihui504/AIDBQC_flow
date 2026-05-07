import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

from src.config import AppConfig, DBInstanceConfig
from src.runtime.loop import TestRuntime


async def run_system_e2e():
    config = AppConfig.from_yaml("config.yaml")
    config._resolve_env()

    config.harness.max_rounds = 5
    config.harness.max_token_budget = 1000000

    if not config.database.instances:
        config.database.instances = [DBInstanceConfig(type="milvus", host="localhost", port=19530)]

    default_inst = config.database.instances[0]
    print(f"Target: {default_inst.type} @ {default_inst.host}:{default_inst.port}")
    print(f"Model: {config.llm.pro_model}")
    print(f"Max rounds: {config.harness.max_rounds}")
    print(f"API Key: {'***' + config.llm.api_key[-4:] if config.llm.api_key else 'NOT SET'}")
    print()

    runtime = TestRuntime(config)

    print("Initializing TestRuntime...")
    t0 = time.time()
    runtime.initialize()
    print(f"Initialized in {time.time()-t0:.1f}s")
    print(f"Agent tools: {len(runtime._registry.tool_names)}")
    print()

    event_bus = runtime.event_bus
    event_log = []

    def on_event(event):
        event_log.append(event)
        etype = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        data = event.data
        if etype in ("tool_invoked", "tool_completed", "error_occurred", "recovery_attempted"):
            print(f"  [EVENT] {etype}: {data}")

    event_bus.subscribe_global(on_event)

    print("Running TestRuntime (timeout: 15 min)...")
    t0 = time.time()
    try:
        state = await asyncio.wait_for(runtime.run(), timeout=900)
    except asyncio.TimeoutError:
        print("TIMEOUT: Runtime hung for 15 minutes!")
        state = runtime.state

    elapsed = time.time() - t0
    print(f"\nElapsed: {elapsed:.1f}s")

    print()
    print("=" * 60)
    print("RUN RESULTS")
    print("=" * 60)
    print(f"Rounds completed: {state.round_number}")
    print(f"Total defects: {state.defect_counter}")
    print(f"Total issues: {len(state.issues)}")
    print(f"Token used: {state.token_usage}")
    print(f"Budget exhausted: {state.is_budget_exhausted()}")
    print(f"Should stop: {state.should_stop()}")
    print(f"Events captured: {len(event_log)}")
    print()

    if state.defects:
        print(f"DEFECTS ({len(state.defects)}):")
        for i, d in enumerate(state.defects):
            if isinstance(d, dict):
                desc = str(d.get('description', '?'))[:80]
                print(f"  [{i+1}] type={d.get('defect_type', '?')} severity={d.get('severity', '?')} desc={desc}")
            else:
                desc = str(getattr(d, 'description', '?'))[:80]
                dtype = getattr(d, 'defect_type', '?')
                sev = getattr(d, 'severity', '?')
                print(f"  [{i+1}] type={dtype} severity={sev} desc={desc}")
    else:
        print("NO DEFECTS FOUND")

    print()

    if state.issues:
        print(f"ISSUES ({len(state.issues)}):")
        for i, issue in enumerate(state.issues):
            title = getattr(issue, 'title', str(issue))[:60]
            verified = getattr(issue, 'verification_status', '?')
            print(f"  [{i+1}] title={title} verified={verified}")
    else:
        print("NO ISSUES GENERATED")

    print()

    if state.execution_log:
        print(f"EXECUTION LOG ({len(state.execution_log)} entries, last 5):")
        for entry in state.execution_log[-5:]:
            print(f"  {entry}")

    print()
    print("=" * 60)
    print("VERDICT")
    print("=" * 60)

    defect_count = state.defect_counter
    if defect_count >= 2:
        print(f"PASS: Found {defect_count} real defects (requirement: >=2)")
    elif defect_count == 1:
        print(f"PARTIAL: Found {defect_count} real defect (requirement: >=2)")
    else:
        print(f"FAIL: Found {defect_count} real defects (requirement: >=2)")

    return state


if __name__ == "__main__":
    asyncio.run(run_system_e2e())
