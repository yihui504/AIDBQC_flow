from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_MILVUS_KEY_DIRS = [
    "internal/core/index",
    "internal/core/search",
    "internal/datacoord",
    "internal/datanode",
    "internal/querynode",
    "internal/proxy",
    "internal/rootcoord",
    "internal/storage",
    "pkg/util",
]


@dataclass
class SourceSearchResult:
    file_path: str = ""
    line_number: int = 0
    content: str = ""
    context: str = ""


@dataclass
class ModuleAnalysis:
    module_path: str = ""
    summary: str = ""
    key_functions: list[str] = field(default_factory=list)
    key_types: list[str] = field(default_factory=list)
    error_handling_patterns: list[str] = field(default_factory=list)


class SourceAnalyzer:
    def __init__(self, config=None):
        self.config = config
        self._repo_path: Optional[str] = None

    def clone_repo(self, url: str = "https://github.com/milvus-io/milvus.git",
                   branch: str = "master", target_dir: Optional[str] = None) -> dict:
        if target_dir is None:
            target_dir = os.path.join(os.getcwd(), "milvus_source")

        if os.path.exists(os.path.join(target_dir, ".git")):
            self._repo_path = target_dir
            return {"success": True, "path": target_dir, "status": "already_exists"}

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, url, target_dir],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                return {"success": False, "error": result.stderr[:500]}
            self._repo_path = target_dir
            return {"success": True, "path": target_dir, "status": "cloned"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Clone timed out after 300s"}
        except FileNotFoundError:
            return {"success": False, "error": "git not found in PATH"}

    def search_source(self, pattern: str, path: Optional[str] = None,
                      max_results: int = 20) -> list[SourceSearchResult]:
        search_dir = path or self._repo_path
        if not search_dir or not os.path.exists(search_dir):
            return []

        results = []
        try:
            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "vendor", "third_party"}]
                for fname in files:
                    if not fname.endswith((".go", ".py", ".java")):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            for line_num, line in enumerate(f, 1):
                                if pattern.lower() in line.lower():
                                    results.append(SourceSearchResult(
                                        file_path=os.path.relpath(fpath, search_dir),
                                        line_number=line_num,
                                        content=line.strip()[:200],
                                        context=line.strip()[:500],
                                    ))
                                    if len(results) >= max_results:
                                        return results
                    except (OSError, PermissionError):
                        continue
        except OSError:
            return []

        return results

    def read_source(self, file_path: str, start_line: int = 1,
                    end_line: int = 100) -> dict:
        full_path = file_path
        if self._repo_path and not os.path.isabs(file_path):
            full_path = os.path.join(self._repo_path, file_path)

        if not os.path.exists(full_path):
            return {"success": False, "error": f"File not found: {full_path}"}

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            selected = lines[start_line - 1:end_line]
            return {
                "success": True,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": min(end_line, len(lines)),
                "total_lines": len(lines),
                "content": "".join(selected),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_module(self, module_path: str) -> ModuleAnalysis:
        full_path = module_path
        if self._repo_path and not os.path.isabs(module_path):
            full_path = os.path.join(self._repo_path, module_path)

        if not os.path.exists(full_path):
            return ModuleAnalysis(module_path=module_path, summary="Path not found")

        go_files = list(Path(full_path).rglob("*.go"))
        if not go_files:
            return ModuleAnalysis(module_path=module_path, summary="No Go source files found")

        key_functions = []
        key_types = []
        error_patterns = []

        for gf in go_files[:20]:
            try:
                content = gf.read_text(encoding="utf-8", errors="replace")
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("func ") and len(key_functions) < 30:
                        func_sig = stripped[:120]
                        key_functions.append(func_sig)
                    elif stripped.startswith("type ") and len(key_types) < 20:
                        type_sig = stripped[:120]
                        key_types.append(type_sig)
                    if "errors." in stripped or "fmt.Errorf" in stripped:
                        if len(error_patterns) < 10:
                            error_patterns.append(stripped[:120])
            except Exception:
                continue

        summary = (
            f"Module: {module_path}, Files: {len(go_files)}, "
            f"Functions: {len(key_functions)}, Types: {len(key_types)}"
        )
        return ModuleAnalysis(
            module_path=module_path,
            summary=summary,
            key_functions=key_functions,
            key_types=key_types,
            error_handling_patterns=error_patterns,
        )

    def extract_internal_mechanisms(self, module_path: str) -> dict:
        analysis = self.analyze_module(module_path)
        return {
            "success": True,
            "module_path": module_path,
            "summary": analysis.summary,
            "key_functions": analysis.key_functions[:15],
            "key_types": analysis.key_types[:10],
            "error_handling_patterns": analysis.error_handling_patterns[:5],
        }

    def get_key_directories(self) -> list[str]:
        if not self._repo_path:
            return []
        existing = []
        for d in _MILVUS_KEY_DIRS:
            full = os.path.join(self._repo_path, d)
            if os.path.exists(full):
                existing.append(d)
        return existing
