from __future__ import annotations

import json

from pydantic_ai import RunContext

from src.models.state import FocusMode, UnifiedState, tool_meta
from src.tools.code.sandbox import DockerSandbox

_sandbox: DockerSandbox | None = None


def _get_sandbox() -> DockerSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = DockerSandbox()
    return _sandbox


@tool_meta(focus_modes=[FocusMode.EXECUTION, FocusMode.VERIFICATION], permission="execute", compress="results_only")
async def code_run_mre(
    ctx: RunContext[UnifiedState],
    mre_code: str,
    db_host: str = "localhost",
    db_port: int = 19530,
) -> str:
    try:
        sandbox = _get_sandbox()
    except Exception as e:
        return json.dumps({"success": False, "exit_code": -1, "stdout": "", "stderr": f"Sandbox unavailable: {e}", "timed_out": False})
    result = await sandbox.execute(mre_code)
    return json.dumps({
        "success": result.exit_code == 0,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
    })
