from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

from pydantic_ai import RunContext

from src.config import AppConfig
from src.models.state import FocusMode, UnifiedState, tool_meta

_config: AppConfig | None = None


def set_config(config: AppConfig) -> None:
    global _config
    _config = config


def _get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_yaml("config.yaml")
    return _config


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="execute", compress="summary")
async def source_clone_repo(
    ctx: RunContext[UnifiedState],
    repo_url: str = "",
    branch: str = "master",
) -> str:
    config = _get_config()
    url = repo_url or config.source_analysis.repo_url
    if not url:
        return json.dumps({"success": False, "path": "", "files_count": 0, "error": "No repo URL provided"})

    target = Path(config.source_analysis.target_dir)
    target.mkdir(parents=True, exist_ok=True)

    if (target / ".git").exists():
        proc = await asyncio.create_subprocess_exec(
            "git", "pull",
            cwd=str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timeout = 120
    else:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "-b", branch, url, str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timeout = 300

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return json.dumps({"success": False, "path": str(target), "files_count": 0, "error": "git operation timed out"})

    if proc.returncode != 0:
        err = stderr.decode(errors="ignore")[:500]
        return json.dumps({"success": False, "path": str(target), "files_count": 0, "error": err})

    files_count = sum(1 for _, _, files in os.walk(target) for _ in files)
    return json.dumps({"success": True, "path": str(target), "files_count": files_count})


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="read", compress="summary")
async def source_search(
    ctx: RunContext[UnifiedState],
    pattern: str,
    file_glob: str = "",
) -> str:
    config = _get_config()
    target = Path(config.source_analysis.target_dir)
    if not target.exists():
        return json.dumps({"success": False, "matches": [], "total": 0, "error": f"Target dir not found: {target}"})

    result = await asyncio.to_thread(_search_sync, config, target, pattern, file_glob)
    return result


def _search_sync(config: AppConfig, target: Path, pattern: str, file_glob: str) -> str:
    search_dirs = [target]
    if config.source_analysis.focus_dirs:
        search_dirs = [target / d for d in config.source_analysis.focus_dirs if (target / d).exists()]

    ext = ""
    if file_glob:
        ext_map = {
            "*.go": ".go", "*.py": ".py", "*.java": ".java",
            "*.ts": ".ts", "*.js": ".js", "*.rs": ".rs", "*.cpp": ".cpp",
        }
        ext = ext_map.get(file_glob, "")
        if not ext and file_glob.startswith("*."):
            ext = file_glob[1:]

    matches = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    for search_dir in search_dirs:
        for root, _, files in os.walk(search_dir):
            for fname in files:
                if ext and not fname.endswith(ext):
                    continue
                fpath = Path(root) / fname
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append({
                                    "file": str(fpath.relative_to(target)),
                                    "line": line_no,
                                    "content": line.strip()[:200],
                                })
                                if len(matches) >= 100:
                                    return json.dumps({"success": True, "matches": matches, "total": len(matches)})
                except (OSError, PermissionError):
                    continue

    return json.dumps({"success": True, "matches": matches, "total": len(matches)})


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="read", compress="full")
async def source_read(
    ctx: RunContext[UnifiedState],
    file_path: str,
    start_line: int = 1,
    end_line: int = 100,
) -> str:
    config = _get_config()
    target = Path(config.source_analysis.target_dir).resolve()
    full_path = (target / file_path).resolve()

    if not full_path.is_relative_to(target):
        return json.dumps({"success": False, "content": "", "total_lines": 0, "error": "Path traversal denied"})

    if not full_path.exists():
        return json.dumps({"success": False, "content": "", "total_lines": 0, "error": f"File not found: {file_path}"})

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, PermissionError) as e:
        return json.dumps({"success": False, "content": "", "total_lines": 0, "error": str(e)})

    total_lines = len(lines)
    selected = lines[start_line - 1 : end_line]
    return json.dumps({"success": True, "content": "".join(selected), "total_lines": total_lines})


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="read", compress="summary")
async def source_analyze_module(
    ctx: RunContext[UnifiedState],
    module_path: str,
) -> str:
    config = _get_config()
    target = Path(config.source_analysis.target_dir).resolve()
    module_dir = (target / module_path).resolve()

    if not module_dir.is_relative_to(target):
        return json.dumps({"success": False, "files": [], "exports": [], "error": "Path traversal denied"})

    if not module_dir.exists():
        return json.dumps({"success": False, "files": [], "exports": [], "error": f"Module not found: {module_path}"})

    result = await asyncio.to_thread(_analyze_module_sync, target, module_dir)
    return result


def _analyze_module_sync(target: Path, module_dir: Path) -> str:
    files = []
    exports = []

    go_export_re = re.compile(r"^func\s+([A-Z]\w*)")
    go_type_re = re.compile(r"^type\s+([A-Z]\w*)")
    go_iface_re = re.compile(r"^type\s+([A-Z]\w*)\s+interface")
    py_export_re = re.compile(r"^(class|def|async\s+def)\s+([A-Za-z_]\w*)")

    for root, _, fnames in os.walk(module_dir):
        for fname in fnames:
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(target))
            files.append(rel)

            if fname.endswith(".go") or fname.endswith(".py"):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            m = go_export_re.match(line)
                            if m:
                                exports.append({"name": m.group(1), "kind": "function", "file": rel})
                                continue
                            m = go_iface_re.match(line)
                            if m:
                                exports.append({"name": m.group(1), "kind": "interface", "file": rel})
                                continue
                            m = go_type_re.match(line)
                            if m:
                                exports.append({"name": m.group(1), "kind": "type", "file": rel})
                                continue
                            m = py_export_re.match(line)
                            if m and not m.group(2).startswith("_"):
                                exports.append({"name": m.group(2), "kind": m.group(1), "file": rel})
                except (OSError, PermissionError):
                    continue

    return json.dumps({"success": True, "files": files, "exports": exports})
