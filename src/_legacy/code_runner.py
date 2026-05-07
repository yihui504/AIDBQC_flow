from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import textwrap
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$")
_SANDBOXED_BUILTINS = {
    "print", "len", "range", "int", "float", "str", "bool", "list", "dict",
    "tuple", "set", "enumerate", "zip", "map", "filter", "sorted", "min",
    "max", "abs", "round", "isinstance", "type", "hasattr", "getattr",
    "True", "False", "None",
}


class CodeRunResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0
    error: Optional[str] = None


def _validate_hostname(host: str) -> str:
    if not _HOSTNAME_RE.match(host):
        raise ValueError(f"Invalid hostname: {host!r}")
    return host


class CodeRunner:
    def __init__(self, timeout: int = 60, working_dir: Optional[str] = None):
        self.timeout = timeout
        self.working_dir = working_dir or os.getcwd()

    def run_python(self, code: str, timeout: Optional[int] = None) -> CodeRunResult:
        import time
        start = time.time()
        actual_timeout = timeout or self.timeout

        tmp_dir = tempfile.mkdtemp(prefix="aidbqc_run_")
        temp_path = os.path.join(tmp_dir, "script.py")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(code)

            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": self.working_dir,
                "HOME": os.environ.get("HOME", ""),
                "USERPROFILE": os.environ.get("USERPROFILE", ""),
                "MILVUS_HOST": os.environ.get("MILVUS_HOST", "localhost"),
                "MILVUS_PORT": os.environ.get("MILVUS_PORT", "19530"),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            }
            safe_env = {k: v for k, v in safe_env.items() if v}

            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                cwd=self.working_dir,
                env=safe_env,
            )
            duration = (time.time() - start) * 1000
            return CodeRunResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10000],
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            return CodeRunResult(
                success=False, error=f"Timeout after {actual_timeout}s",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CodeRunResult(
                success=False, error=str(e), duration_ms=duration,
            )
        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    def run_mre(self, mre_code: str, milvus_host: str = "localhost", milvus_port: int = 19530) -> CodeRunResult:
        safe_host = _validate_hostname(milvus_host)
        if not isinstance(milvus_port, int) or not (1 <= milvus_port <= 65535):
            raise ValueError(f"Invalid port: {milvus_port}")

        indented_code = textwrap.indent(mre_code, "    ")
        wrapper = (
            "try:\n"
            "    import sys\n"
            "    import traceback\n"
            "\n"
            f"    MILVUS_HOST = {safe_host!r}\n"
            f"    MILVUS_PORT = {milvus_port}\n"
            "\n"
            f"{indented_code}\n"
            '    print("MRE_EXECUTION: SUCCESS")\n'
            "except Exception as e:\n"
            "    traceback.print_exc()\n"
            '    print(f"MRE_EXECUTION: FAILED - {type(e).__name__}: {e}")\n'
            "    sys.exit(1)\n"
        )
        return self.run_python(wrapper, timeout=self.timeout)

    def generate_test_data(self, dimension: int = 128, count: int = 100, distribution: str = "normal") -> dict:
        import numpy as np

        if not isinstance(dimension, int) or dimension < 1 or dimension > 32768:
            raise ValueError(f"Invalid dimension: {dimension}")
        if not isinstance(count, int) or count < 1 or count > 100000:
            raise ValueError(f"Invalid count: {count}")
        if distribution not in ("normal", "uniform", "zeros"):
            distribution = "normal"

        np.random.seed(None)
        if distribution == "normal":
            vectors = np.random.randn(count, dimension).astype(np.float32).tolist()
        elif distribution == "uniform":
            vectors = np.random.uniform(-1, 1, (count, dimension)).astype(np.float32).tolist()
        elif distribution == "zeros":
            vectors = np.zeros((count, dimension), dtype=np.float32).tolist()
        else:
            vectors = np.random.randn(count, dimension).astype(np.float32).tolist()

        return {
            "dimension": dimension,
            "count": count,
            "distribution": distribution,
            "vectors": vectors,
        }
