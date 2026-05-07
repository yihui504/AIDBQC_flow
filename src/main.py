from __future__ import annotations

import asyncio
import argparse
import logging
import sys

from src.config import AppConfig
from src.runtime import TestRuntime
from src.models.state import FocusMode

logger = logging.getLogger(__name__)

COMMANDS = {
    "p": "pause",
    "r": "resume",
    "s": "status",
    "skip": "skip",
    "stop": "stop",
    "focus": "focus <mode>",
}


async def _read_commands(runtime: TestRuntime) -> None:
    loop = asyncio.get_event_loop()
    while not runtime.state.should_stop():
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
        except (EOFError, KeyboardInterrupt):
            runtime.stop()
            break
        cmd = line.strip().lower()
        if not cmd:
            continue
        if cmd in ("p", "pause"):
            runtime.pause()
            print("[PAUSED] Type 'r' or 'resume' to continue")
        elif cmd in ("r", "resume"):
            runtime.resume()
            print("[RESUMED]")
        elif cmd in ("s", "status"):
            status = runtime.get_status()
            print(f"  Round: {status['round']}  Focus: {status['focus']}  "
                  f"Defects: {status['defects']}  Issues: {status['issues']}({status['verified']} verified)  "
                  f"Tokens: {status['tokens']} ({status['budget_pct']}%)  "
                  f"Paused: {status['paused']}  Flash: {status['flash_fallback']}")
        elif cmd == "skip":
            runtime.skip()
            print("[SKIPPING current round]")
        elif cmd == "stop":
            runtime.stop()
            print("[STOPPING...]")
            break
        elif cmd.startswith("focus "):
            focus = cmd[6:].strip()
            if runtime.set_focus(focus):
                print(f"[FOCUS set to: {focus}]")
            else:
                valid = ", ".join(m.value for m in FocusMode)
                print(f"[Invalid focus. Valid: {valid}]")
        elif cmd in ("h", "help"):
            for k, v in COMMANDS.items():
                print(f"  {k:6s} - {v}")
        else:
            print(f"  Unknown command: {cmd}. Type 'h' for help.")


async def run_interactive(runtime: TestRuntime) -> None:
    run_task = asyncio.create_task(runtime.run())
    cmd_task = asyncio.create_task(_read_commands(runtime))

    done, pending = await asyncio.wait(
        [run_task, cmd_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for t in pending:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass

    state = runtime.state
    print(f"\n{'='*60}")
    print(f"Run completed: {len(state.defects)} defects, {len(state.issues)} issues")
    verified = sum(1 for i in state.issues if i.verification_status.value == "final")
    print(f"Verified issues: {verified}")
    print(f"Total tokens: {state.token_usage}")
    print(f"Rounds executed: {state.round_number}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="AIDBQC v6.0 - AI-Driven Database Quality Control")
    parser.add_argument("--target", default="milvus", choices=["milvus", "qdrant", "weaviate", "pgvector"])
    parser.add_argument("--version", default="2.6.12")
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--safety-level", default="cautious", choices=["cautious", "aggressive"])
    parser.add_argument("--model", default="deepseek-chat", choices=["deepseek-chat", "deepseek-reasoner"])
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive console")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    config = AppConfig.from_yaml(args.config)
    config.database.default = args.target
    config.database.target_version = args.version
    config.harness.max_rounds = args.max_rounds
    config.harness.safety_level = args.safety_level

    if args.model == "deepseek-reasoner":
        config.llm.pro_model = "deepseek-reasoner"
    elif args.model == "deepseek-chat":
        config.llm.pro_model = "deepseek-chat"

    runtime = TestRuntime(config)

    if args.non_interactive:
        result = asyncio.run(runtime.run())
        print(f"\nRun completed: {len(result.defects)} defects, {len(result.issues)} issues")
    else:
        print("AIDBQC v6.0 Interactive Mode")
        print("Commands: p(ause) r(esume) s(tatus) skip stop focus <mode> h(elp)")
        print("-" * 60)
        asyncio.run(run_interactive(runtime))


if __name__ == "__main__":
    main()
