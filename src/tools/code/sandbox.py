from __future__ import annotations

import asyncio
import tempfile
import os
import threading
from dataclasses import dataclass
from typing import Optional

import docker


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-slim", timeout: int = 60,
                 memory_limit: str = "512m", cpu_limit: float = 1.0):
        self._image = image
        self._timeout = timeout
        self._memory_limit = memory_limit
        self._cpu_limit = cpu_limit
        self._client: Optional[docker.DockerClient] = None

    def _get_client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    async def execute(self, code: str, language: str = "python") -> SandboxResult:
        if language != "python":
            return SandboxResult(exit_code=-1, stdout="", stderr=f"Unsupported language: {language}")

        def _run():
            try:
                client = self._get_client()
                container = client.containers.run(
                    image=self._image,
                    command=["python", "-c", code],
                    mem_limit=self._memory_limit,
                    nano_cpus=int(self._cpu_limit * 1e9),
                    detach=True,
                    remove=False,
                    network_disabled=False,
                )
                timed_out = False
                try:
                    timer = threading.Timer(self._timeout, lambda: _kill_container(container))
                    timer.start()
                    result = container.wait()
                    timer.cancel()
                    exit_code = result.get("StatusCode", -1)
                    if exit_code == 137:
                        timed_out = True
                    stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                    stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                    return SandboxResult(exit_code=exit_code, stdout=stdout, stderr=stderr, timed_out=timed_out)
                except Exception:
                    timed_out = True
                    try:
                        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                    except Exception:
                        stdout = ""
                        stderr = "Container killed due to timeout"
                    return SandboxResult(exit_code=-1, stdout=stdout, stderr=stderr, timed_out=True)
                finally:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
            except Exception as e:
                return SandboxResult(exit_code=-1, stdout="", stderr=str(e))

        return await asyncio.to_thread(_run)

    async def build_image(self, dockerfile_content: str, tag: str = "aidbqc-sandbox") -> str:
        def _build():
            with tempfile.TemporaryDirectory() as tmpdir:
                df_path = os.path.join(tmpdir, "Dockerfile")
                with open(df_path, "w") as f:
                    f.write(dockerfile_content)
                client = self._get_client()
                image, logs = client.images.build(path=tmpdir, tag=tag, rm=True)
                return image.tags[0] if image.tags else tag

        return await asyncio.to_thread(_build)


def _kill_container(container) -> None:
    try:
        container.kill()
    except Exception:
        pass
