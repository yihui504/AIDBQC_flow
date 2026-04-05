import os
import time
from typing import Dict, Any, List, Optional, Tuple

from src.agents.agent_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

from src.state import WorkflowState, DefectReport
from src.validators.reference_validator import ReferenceValidator
from src.defects.enhanced_deduplicator import EnhancedDefectDeduplicator, InternalDefectReport
from src.rate_limiter import global_llm_rate_limiter
from langchain_community.callbacks.manager import get_openai_callback

class EmbeddingGenerator:
    """生成真实的语义嵌入向量用于 MRE 代码"""
    
    def __init__(self):
        self.model = None
        self._init_model()
    
    def _init_model(self):
        """延迟加载嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[EmbeddingGenerator] Model loaded successfully")
        except Exception as e:
            print(f"[EmbeddingGenerator] Warning: Could not load model ({e})")
            self.model = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """生成文本的嵌入向量"""
        if self.model:
            embedding = self.model.encode(text)
            return embedding.tolist()
        else:
            import numpy as np
            np.random.seed(hash(text) % (2**32))
            return np.random.randn(384).tolist()
    
    def generate_search_vector_code(self, query_text: str, dimension: int = 384) -> str:
        """生成用于 MRE 的搜索向量代码"""
        embedding = self.generate_embedding(query_text)
        embedding_str = ", ".join([f"{x:.6f}" for x in embedding[:dimension]])
        return f"# 使用真实语义向量 (由 SentenceTransformer 生成)\nsearch_vector = [{embedding_str}]"

class IsolatedCodeRunner:
    """
    Isolated code execution runner using Docker containers.
    
    Features:
    - Execute code in isolated Docker containers
    - Resource limits (CPU, memory, network)
    - Timeout control
    - Automatic container cleanup
    """
    
    def __init__(self, docker_client=None, image: str = "python:3.11-slim", timeout_seconds: int = 30):
        self.image = image
        self.timeout_seconds = timeout_seconds
        self.enabled = False
        self.config = None
        
        if docker_client is None:
            try:
                import docker
                self.docker_client = docker.from_env()
            except Exception as e:
                print(f"[IsolatedCodeRunner] Failed to initialize Docker client: {e}")
                self.docker_client = None
        else:
            self.docker_client = docker_client
    
    def set_config(self, config):
        """Set configuration loader and check if isolated execution is enabled."""
        self.config = config
        self.enabled = config.get_bool("isolated_mre.enabled", default=False)
        if self.enabled:
            print(f"[IsolatedCodeRunner] Isolated execution enabled (timeout: {self.timeout_seconds}s)")
        else:
            print("[IsolatedCodeRunner] Isolated execution disabled")
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute code in isolated container.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dictionary with execution results:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "timeout": bool,
                "error": str | None
            }
        """
        if not self.enabled or not self.docker_client:
            return self._execute_fallback(code)
        
        container = None
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            
            tmp_dir = os.path.dirname(tmp_path)
            tmp_filename = os.path.basename(tmp_path)
            
            volume_mapping = {tmp_dir: {'bind': '/workspace', 'mode': 'rw'}}
            
            container = self.docker_client.containers.create(
                image=self.image,
                command=f"python /workspace/{tmp_filename}",
                volumes=volume_mapping,
                network_disabled=True,
                mem_limit="512m",
                cpu_quota=100000,
                cpu_period=100000,
                detach=True
            )
            
            container.start()
            
            exit_status = container.wait(timeout=self.timeout_seconds)
            
            if exit_status["StatusCode"] is None:
                container.stop(timeout=5)
                container.remove()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "timeout": True,
                    "error": f"Execution timed out after {self.timeout_seconds}s"
                }
            
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            container.stop(timeout=5)
            container.remove()
            
            stdout = ""
            stderr = ""
            
            try:
                logs_bytes = container.logs(stdout=True, stderr=True).decode('utf-8')
                stdout, stderr = self._parse_container_logs(logs_bytes)
            except:
                pass
            
            exit_code = exit_status["StatusCode"]
            
            return {
                "success": exit_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "timeout": False,
                "error": None if exit_code == 0 else f"Exit code: {exit_code}"
            }
            
        except Exception as e:
            if container:
                try:
                    container.stop(timeout=5)
                    container.remove()
                except:
                    pass
            print(f"[IsolatedCodeRunner] Error executing code: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "timeout": False,
                "error": str(e)
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
    
    def _parse_container_logs(self, logs: str) -> Tuple[str, str]:
        """Parse container logs into stdout and stderr."""
        lines = logs.split('\n')
        stdout_lines = []
        stderr_lines = []
        
        for line in lines:
            if line.startswith('[STDERR]'):
                stderr_lines.append(line[8:])
            elif line.startswith('[STDOUT]'):
                stdout_lines.append(line[8:])
            else:
                stdout_lines.append(line)
        
        return '\n'.join(stdout_lines), '\n'.join(stderr_lines)
    
    def _execute_fallback(self, code: str) -> Dict[str, Any]:
        """Fallback to subprocess execution when Docker is not available."""
        import subprocess
        import sys
        import tempfile
        import textwrap
        
        print(f"[IsolatedCodeRunner] Using subprocess fallback (Docker not available)")
        
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        
        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "timeout": False,
                "error": None if result.returncode == 0 else f"Exit code: {result.returncode}"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "timeout": True,
                "error": f"Execution timed out after {self.timeout_seconds}s"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "timeout": False,
                "error": str(e)
            }
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

class GitHubIssue(BaseModel):
    title: str = Field(description="Issue title (e.g. '[Bug]: <Brief Description>')")
    body_markdown: str = Field(description="Full markdown body of the issue, strictly following the official Milvus bug report template.")

class DefectVerifierAgent:
    """
    Agent 6: Defect Verifier & Deduplicator
    Responsibilities:
    1. Deduplicate found defects based on semantic similarity.
    2. Extract MRE (Minimal Reproducible Example).
    3. Generate a GitHub Issue markdown file for verified defects.
    """
    
    def __init__(self):
        self.llm = get_llm(model_name="glm-4.7", temperature=0.1)
        self.parser = JsonOutputParser(pydantic_object=GitHubIssue)

        # Initialize reference validator for filtering low-relevance docs
        self.ref_validator = ReferenceValidator(threshold=0.6)
        
        # NEW: Initialize enhanced deduplicator
        self.deduplicator = EnhancedDefectDeduplicator(similarity_threshold=0.7)
        
        # NEW: Initialize embedding generator for real semantic vectors
        self.embedding_generator = EmbeddingGenerator()
        self.runs_root = os.path.join(".trae", "runs")
        
        # Following standard GitHub Bug Report Templates for databases
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Senior QA Engineer responsible for converting internal defect reports into professional, community-ready GitHub Issues for the Milvus vector database.

### Format Instructions
{format_instructions}

### Verification Protocol
1. **Categorize by Bug Type**:
    - **Hard API Bugs (Type-1)**: You MUST prioritize finding the "Official Docs Reference" within the 'Target Document' or 'Validated References'. Verify quotes verbatim.
    - **Semantic/Logic Bugs (Type-4, Type-2)**: Documentation support is often unavailable for abstract logic violations. For these types, you MAY SKIP the "Official Docs Reference" if no direct match is found. Focus instead on the **logical consistency** of the reproduction and why the behavior violates the intended contract.
2. **Verify Quote Authenticity (For Type-1)**: You MUST verify that any quote used as an "Official Docs Reference" exists verbatim (or near-verbatim) in the provided documents.
3. **Fallback Mechanism**: If evidence is required but not found in 'Target Document', search 'Validated References' or the full `docs_context`.

Your output MUST strictly follow this official-style GitHub Issue Markdown template:

```markdown
### Is there an existing issue for this?
- [x] I have searched the existing issues

### Environment
- **Milvus version**: {{db_version}}
- **Deployment mode**: Docker Standalone
- **OS**: Windows / Linux
- **SDK/Client**: pymilvus
- **Vector config**: {{vector_config}}

### Describe the bug
[A clear and concise description of what the bug is.]

### Steps To Reproduce
[A clear, standalone, and concise Minimal Reproducible Example (MRE) in Python using the pymilvus SDK.
The code MUST include:
1. Connection logic (connections.connect)
2. Collection creation with specific parameters.
3. The exact operation that triggered the failure.
4. **CRITICAL**: For semantic search bugs, use REAL semantic vectors (not random vectors).
]
```python
# MRE code here
```

### Expected Behavior
[What you expected to happen according to the contract or documentation]

### Actual Behavior
[What actually happened, including the raw error message]

### Evidence & Documentation
- **Violated Contract Type**: [e.g., Type-1 (L1 Crash/Error), Type-4 (Semantic Violation)]
- **Official Docs Reference**: [For Type-1: Quote the relevant sentence. For Type-4: State "Semantic logic violation; direct documentation reference not applicable" if no specific quote exists.]
- **Reference URL**: [The exact URL where the quote was found, or "N/A" for semantic logic bugs.]
- **Verification Status**: [State "Quote Verified", "Reference Fallback Used", or "Logic Verified (No Doc Reference Needed)"]
```

Use the provided defect report, environment context, target document, and PRE-VALIDATED references to fill in the template accurately. 
You MUST generate real Python code for the MRE based on the case_id and parameters. 
CRITICAL: ONLY use the provided documentation context for the Evidence section. If no references are provided and no target document is available, state "No direct documentation reference found".
"""),
            ("human", "Defect Report:\n{report}\n\nTarget Document (from source_url):\n{target_doc}\n\nEnvironment Context:\n{env_context}\n\nValidated References (Source of Truth):\n{validated_refs}")
        ])

    def _parse_docs_context(self, docs_context: str) -> Dict[str, str]:
        """Parse docs context into URL -> content mapping."""
        docs_map = {}
        sections = docs_context.split("Source: ")

        for section in sections[1:]:  # Skip empty first section
            lines = section.split("\n", 2)
            if len(lines) >= 2:
                url = lines[0].strip()
                content = "\n".join(lines[1:])
                docs_map[url] = content

        return docs_map

    def _get_relevant_docs_for_defect(self, defect, docs_map: Dict[str, str], max_chars: int = 8000) -> str:
        """Extract relevant document fragments for a specific defect, staying within char limit."""
        if not docs_map:
            return ""
        
        import re
        
        # Extract keywords from defect for relevance matching
        keywords = set()
        
        # From case_id (e.g., "TC_001_MAX_DIM_BOUNDARY" → "MAX", "DIM", "BOUNDARY")
        if defect.case_id:
            parts = re.split(r'[_\-]', defect.case_id.upper())
            for p in parts:
                if len(p) > 2 and not p.startswith('TC') and not p.isdigit():
                    keywords.add(p)
        
        # From operation (e.g., "wireless noise cancelling headphones" → key terms)
        if defect.operation:
            op_words = re.findall(r'[a-zA-Z]{3,}', defect.operation.lower())
            keywords.update(op_words[:8])
        
        # From root_cause_analysis - extract important terms
        if defect.root_cause_analysis:
            # Look for Milvus-specific terms
            milvus_terms = re.findall(r'(?:collection|index|search|dimension|vector|embedding|metric|load|partition|schema|field|filter|top_k|nprobe|ef|nlist|mmap)', 
                                       defect.root_cause_analysis.lower())
            keywords.update(milvus_terms)
            
            # Look for API terms
            api_terms = re.findall(r'(?:create_collection|insert|search|query|delete|upsert|flush|compact|load_collection|release)',
                                    defect.root_cause_analysis.lower())
            keywords.update(api_terms)
        
        # Also add bug_type keywords
        if defect.bug_type:
            bt_keywords = re.findall(r'[a-zA-Z]{3,}', defect.bug_type.lower())
            keywords.update(bt_keywords[:5])
        
        # Score each doc section by keyword overlap
        scored_docs = []
        for url, content in docs_map.items():
            if not content or len(content.strip()) < 50:
                continue
            
            content_lower = content.lower()
            score = 0
            for kw in keywords:
                if kw.lower() in content_lower:
                    score += 1
                    # Count occurrences for bonus
                    count = content_lower.count(kw.lower())
                    if count > 1:
                        score += min(count - 1, 3)  # Cap bonus per keyword
            
            if score > 0:
                scored_docs.append((score, url, content))
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Build truncated context within budget
        result_parts = []
        total_chars = 0
        header = "[Truncated for API limit - showing most relevant sections]\n\n"
        total_chars += len(header)
        
        for score, url, content in scored_docs:
            available = max_chars - total_chars
            if available <= 100:
                break
            
            # Take a chunk from this doc (prefer beginning which usually has the most relevant info)
            chunk_size = min(len(content), available)
            chunk = content[:chunk_size]
            if chunk_size < len(content):
                chunk += "\n... [truncated]"
            
            part = f"### Source: {url}\n{chunk}\n\n"
            if total_chars + len(part) > max_chars:
                break
                
            result_parts.append(part)
            total_chars += len(part)
        
        if not result_parts:
            # Fallback: return first N chars of first doc
            for url, content in docs_map.items():
                if content and len(content) > 100:
                    return header + f"### Source: {url}\n{content[:max_chars - len(header) - 50]}\n... [truncated]"
            return ""
        
        return header + "".join(result_parts)

    def _deduplicate(self, defects: List[DefectReport]) -> List[DefectReport]:
        """Enhanced deduplication based on multi-dimensional similarity."""
        if not defects:
            return []

        print(f"[Agent 6] Starting enhanced deduplication for {len(defects)} defects...")
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Convert state DefectReport to InternalDefectReport
        internal_defects = [InternalDefectReport.from_state(d) for d in defects]
        
        # Run async deduplication
        unique_internal, clusters = loop.run_until_complete(
            self.deduplicator.deduplicate(internal_defects)
        )
        
        # Map back to state DefectReport
        # We only keep those whose case_id matches the representative_defect_id in clusters
        # or those that were not clustered (unique_internal)
        unique_ids = {d.defect_id for d in unique_internal}
        unique_defects = [d for d in defects if d.case_id in unique_ids]
        
        print(f"[Agent 6] Enhanced deduplication finished. {len(defects)} -> {len(unique_defects)}")
        if clusters:
            print(f"[Agent 6] Found {len(clusters)} duplicate clusters.")
            for cluster in clusters:
                print(f"  - Cluster {cluster.cluster_id}: {len(cluster.defect_ids)} items, type: {cluster.cluster_type}")

        return unique_defects

    def _extract_mre_code(self, markdown: str) -> Optional[str]:
        """Extract Python code block from markdown."""
        import re
        pattern = r"```python\n(.*?)```"
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _inject_real_vectors(self, mre_code: str, defect) -> str:
        """Replace placeholder vectors in MRE code with real semantic embeddings."""
        import re

        if not self.embedding_generator or not self.embedding_generator.model:
            print("[Agent 6] EmbeddingGenerator model not loaded, skipping vector injection")
            return mre_code

        # Extract query text from defect for embedding generation
        query_text = ""
        if hasattr(defect, 'operation') and defect.operation:
            query_text = defect.operation
        elif hasattr(defect, 'title') and defect.title:
            query_text = defect.title
        elif hasattr(defect, 'description') and defect.description:
            query_text = defect.description[:200]

        if not query_text.strip():
            return mre_code

        modified_code = mre_code
        injection_count = 0

        # Pattern 1: [constant] * N  (uniform fill)
        # Matches: search_vector = [0.1] * 768, vec = [0.2] * dim, etc.
        uniform_pattern = re.compile(
            r'^(\s*)(\w+)\s*=\s*\[([0-9.]+)\]\s*\*\s*(\w+)',
            re.MULTILINE
        )

        def replace_uniform(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            constant = float(m.group(3))
            dim_ref = m.group(4)

            # Try to resolve dimension from context
            dim = self._resolve_dimension(modified_code, dim_ref)
            if dim and dim > 10:  # Only replace if it looks like a real vector dimension
                try:
                    real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                    injection_count += 1
                    return f"{indent}{var_name} = {real_vector_code.split('=', 1)[1].strip()}"
                except Exception as e:
                    print(f"[Agent 6] Vector injection failed for {var_name}: {e}")
            return m.group(0)

        modified_code = uniform_pattern.sub(replace_uniform, modified_code)

        # Pattern 2: np.random.rand(N) / np.random.randn(N)
        random_pattern = re.compile(
            r'^(\s*)(\w+)\s*=\s*np\.random\.(?:rand|randn)\s*\(\s*(\w+)\s*\)',
            re.MULTILINE
        )

        def replace_random(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            dim_ref = m.group(3)

            dim = self._resolve_dimension(modified_code, dim_ref)
            if dim and dim > 10:
                try:
                    real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                    injection_count += 1
                    return f"{indent}{var_name} = {real_vector_code.split('=', 1)[1].strip()}"
                except Exception as e:
                    print(f"[Agent 6] Vector injection failed for {var_name}: {e}")
            return m.group(0)

        modified_code = random_pattern.sub(replace_random, modified_code)

        # Pattern 3: Short hand-crafted placeholder lists — ONLY match lines that look like numeric vectors
        # Must have: variable name containing 'vector'/'embedding'/'query', AND content is purely numeric
        simple_list_pattern = re.compile(
            r'^(\s*)((?:search_vector|query_vector|embedding|vec|data_vec|query_vec)\w*)\s*=\s*\[([^\]]{5,500})\]',
            re.MULTILINE | re.IGNORECASE
        )

        def replace_simple_list(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            list_content = m.group(3).strip()
            
            # Parse and validate: must be ALL numeric values (floats/integers)
            try:
                numbers = [float(x.strip()) for x in list_content.split(',')]
                if len(numbers) < 2:
                    return m.group(0)  # Too short to be a real vector
                
                # Check if values are suspiciously uniform/placeholder-like
                # (all same value, or evenly spaced small set)
                is_placeholder = False
                if len(numbers) <= 20:  # Only check short lists
                    unique_vals = set(round(v, 4) for v in numbers)
                    if len(unique_vals) <= 2:  # All same or alternating between 2 values
                        is_placeholder = True
                    elif len(unique_vals) == len(numbers) and len(numbers) >= 3:
                        # Check for arithmetic progression (like 0.1, 0.2, 0.3...)
                        diffs = [round(numbers[i+1] - numbers[i], 6) for i in range(len(numbers)-1)]
                        if len(set(diffs)) == 1 and diffs[0] != 0:
                            is_placeholder = True
                
                if is_placeholder:
                    dim = len(numbers)
                    try:
                        real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                        injection_count += 1
                        return f"{indent}{var_name} = {real_vector_code.split('=', 1)[1].strip()}"
                    except Exception as e:
                        print(f"[Agent 6] Vector injection failed for {var_name}: {e}")
                
                return m.group(0)
            except (ValueError, TypeError):
                # Not a numeric list, skip
                return m.group(0)

        modified_code = simple_list_pattern.sub(replace_simple_list, modified_code)

        # Pattern 4: List comprehension vector generation — [np.random.rand(N) for _ in range(M)]
        # Also handles: [np.random.randn(dim).astype(np.float32) for _ in range(n)]
        list_comp_pattern = re.compile(
            r'^(\s*)(\w+)\s*=\s*\[\s*np\.random\.(rand|randn)\s*\(\s*(\w+)\s*\)'
            r'(?:\s*\.\w+(?:\([^)]*\)))*'  # .astype(np.float32) etc.
            r'\s+for\s+\w+\s+in\s+range\s*\(\s*(\w+)\s*\)\s*\]',
            re.MULTILINE
        )

        def replace_list_comp(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            rand_func = m.group(3)  # 'rand' or 'randn'
            inner_dim_ref = m.group(4)  # dimension reference (could be number or variable)
            count_ref = m.group(5)     # range() argument

            # Resolve count first
            try:
                count = int(count_ref)
            except ValueError:
                count = self._resolve_dimension(modified_code, count_ref)

            if not count or count < 1 or count > 20:
                return m.group(0)  # Safety limit

            # Resolve inner dimension
            dim = self._resolve_dimension(modified_code, inner_dim_ref)
            if not dim or dim < 2:
                return m.group(0)

            try:
                lines = []
                for i in range(count):
                    real_vector_code = self.embedding_generator.generate_search_vector_code(
                        f"{query_text} #{i+1}", dim
                    )
                    vec_value = real_vector_code.split('=', 1)[1].strip()
                    if i == 0:
                        lines.append(f"{indent}{var_name} = [")
                    lines.append(f"{indent}    {vec_value},  # real embedding {i+1}/{count}")

                lines.append(f"{indent}]")
                result = '\n'.join(lines)

                # Safety check: don't let single injection exceed 25KB
                if len(result) > 25000:
                    return m.group(0)

                injection_count += count  # Count each vector as an injection
                return result
            except Exception as e:
                print(f"[Agent 6] List comprehension injection failed for {var_name}: {e}")
                return m.group(0)

        modified_code = list_comp_pattern.sub(replace_list_comp, modified_code)

        # Pattern 5: Nested vectors inside dict/list structures — {"vector": np.random.rand(N)} or {"embedding": [...]}
        nested_vector_pattern = re.compile(
            r'["\'](?:vector|embedding|query_vec|search_vec)\s*["\']\s*:\s*'
            r'(?:np\.random\.(?:rand|randn)\s*\(\s*(\w+)\s*\)|\[([^\]]{10,500})\])',
            re.MULTILINE | re.IGNORECASE
        )

        def replace_nested(m):
            nonlocal injection_count

            # Case A: np.random.rand(N) / np.random.randn(N)
            if m.group(1):
                dim_ref = m.group(1)
                dim = self._resolve_dimension(modified_code, dim_ref)
                if dim and dim > 10:
                    try:
                        real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                        vec_value = real_vector_code.split('=', 1)[1].strip()
                        injection_count += 1
                        key_part = m.group(0).split(':', 1)[0]
                        return f"{key_part}: {vec_value}"
                    except Exception as e:
                        print(f"[Agent 6] Nested vector injection failed: {e}")

            # Case B: Short placeholder list like [0.1, 0.2, ...]
            elif m.group(2):
                list_content = m.group(2).strip()
                try:
                    numbers = [float(x.strip()) for x in list_content.split(',')]
                    if 2 <= len(numbers) <= 20:
                        unique_vals = set(round(v, 4) for v in numbers)
                        if len(unique_vals) <= 2:  # Placeholder-like
                            dim = len(numbers)
                            real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                            vec_value = real_vector_code.split('=', 1)[1].strip()
                            injection_count += 1
                            key_part = m.group(0).split(':', 1)[0]
                            return f"{key_part}: {vec_value}"
                except (ValueError, TypeError):
                    pass

            return m.group(0)

        modified_code = nested_vector_pattern.sub(replace_nested, modified_code)

        # Pattern 5b: Uniform fill inside dict/list — "vector": [0.1] * 768
        nested_uniform_pattern = re.compile(
            r'["\'](?:vector|embedding|query_vec|search_vec)\s*["\']\s*:\s*'
            r'\[([0-9.]+)\]\s*\*\s*(\w+)',
            re.MULTILINE | re.IGNORECASE
        )

        def replace_nested_uniform(m):
            nonlocal injection_count
            constant = float(m.group(1))
            dim_ref = m.group(2)
            
            dim = self._resolve_dimension(modified_code, dim_ref)
            if dim and dim > 10:
                try:
                    real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, dim)
                    vec_value = real_vector_code.split('=', 1)[1].strip()
                    injection_count += 1
                    key_part = m.group(0).split(':', 1)[0]
                    return f"{key_part}: {vec_value}"
                except Exception as e:
                    print(f"[Agent 6] Nested uniform injection failed: {e}")
            return m.group(0)

        modified_code = nested_uniform_pattern.sub(replace_nested_uniform, modified_code)

        # Pattern 6: Python built-in random module — [random.random() for _ in range(N)]
        # Also handles: [random.uniform(a, b) for _ in range(n)], [random.gauss(mu, sigma) for _ in range(n)]
        # Also handles: [[random.random() for _ in range(dim)]] (nested, common in Milvus MREs)
        builtin_random_pattern = re.compile(
            r'^(\s*)(\w+)\s*=\s*(?:\[\s*)?'  # Optional outer [] for nested lists
            r'\[random\.(?:random|randn|uniform|gauss|randint)\s*\([^)]*\)'
            r'\s+for\s+\w+\s+in\s+range\s*\(\s*(\w+)\s*\)'
            r'(?:\s*\])?'  # Optional closing ] for nested lists
            r'\s*(?:\])?',  # Trailing optional ]
            re.MULTILINE
        )

        def replace_builtin_random(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            count_ref = m.group(3)

            count = None
            try:
                count = int(count_ref)
            except ValueError:
                count = self._resolve_dimension(modified_code, count_ref)

            if not count or count < 2 or count > 4096:
                return m.group(0)

            try:
                real_vector_code = self.embedding_generator.generate_search_vector_code(query_text, count)
                vec_value = real_vector_code.split('=', 1)[1].strip()
                injection_count += 1
                return f"{indent}{var_name} = {vec_value}"
            except Exception as e:
                print(f"[Agent 6] Builtin random injection failed for {var_name}: {e}")
                return m.group(0)

        modified_code = builtin_random_pattern.sub(replace_builtin_random, modified_code)

        # Pattern 6b: np.random.* with .tolist() suffix — [np.random.rand(N).tolist() for _ in range(M)]
        numpy_tolists_pattern = re.compile(
            r'^(\s*)(\w+)\s*=\s*\['
            r'np\.random\.(?:rand|randn)\s*\(\s*(\w+)\s*\)\.tolist\(\)'
            r'\s+for\s+\w+\s+in\s+range\s*\(\s*(\w+)\s*\)\s*\]',
            re.MULTILINE
        )

        def replace_numpy_tolists(m):
            nonlocal injection_count
            indent = m.group(1)
            var_name = m.group(2)
            dim_ref = m.group(3)
            count_ref = m.group(4)

            dim = self._resolve_dimension(modified_code, dim_ref)
            if not dim or dim < 2:
                return m.group(0)

            try:
                count = int(count_ref)
            except ValueError:
                count = self._resolve_dimension(modified_code, count_ref)

            if not count or count < 1 or count > 20:
                return m.group(0)

            try:
                lines = []
                for i in range(count):
                    real_vector_code = self.embedding_generator.generate_search_vector_code(
                        f"{query_text} #{i+1}", dim
                    )
                    vec_value = real_vector_code.split('=', 1)[1].strip()
                    if i == 0:
                        lines.append(f"{indent}{var_name} = [")
                    lines.append(f"{indent}    {vec_value},  # real embedding {i+1}/{count}")
                lines.append(f"{indent}]")
                result = '\n'.join(lines)
                if len(result) > 25000:
                    return m.group(0)
                injection_count += count
                return result
            except Exception as e:
                print(f"[Agent 6] Numpy tolist injection failed for {var_name}: {e}")
                return m.group(0)

        modified_code = numpy_tolists_pattern.sub(replace_numpy_tolists, modified_code)

        if injection_count > 0:
            print(f"[Agent 6] Injected real vectors into {injection_count} placeholder(s) for {getattr(defect, 'case_id', '?')}")

        return modified_code

    def _resolve_dimension(self, code: str, dim_ref: str) -> Optional[int]:
        import re

        # If it's already a number literal
        try:
            val = int(dim_ref)
            if val > 0:
                return val
        except ValueError:
            pass

        # Search for direct assignment of the referenced variable
        direct_match = re.search(rf'{re.escape(dim_ref)}\s*=\s*(\d+)', code, re.IGNORECASE)
        if direct_match:
            return int(direct_match.group(1))

        # Search common dimension variable names: dim, dimension, d, vec_dim, embed_dim, etc.
        dim_patterns = [
            r'(?:^|\n)\s*(?:dim|dimension|d|vec_dim|embed_dim|embedding_dim|vector_dim)\s*[=:]\s*(\d+)',
            r'DEFAULT_DIM\s*[=:]\s*(\d+)',
            r'EMBEDDING_DIM\s*[=:]\s*(\d+)',
            r'VECTOR_DIM\s*[=:]\s*(\d+)',
        ]
        for pattern in dim_patterns:
            matches = list(re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE))
            if matches:
                return int(matches[-1].group(1))  # Use last assignment

        # Search for FieldSchema with dim parameter
        schema_match = re.search(
            r'(?:FieldSchema|fields?\.\w+)\s*\([^)]*\bdim\s*=\s*(\d+)',
            code[:3000], re.IGNORECASE
        )
        if schema_match:
            return int(schema_match.group(1))

        # Search for create_collection or similar calls with dimension
        create_match = re.search(
            r'(?:create_collection|add_field|add_vector)[^)]*\b(?:dim|dimension)\s*=\s*(\d+)',
            code[:3000], re.IGNORECASE
        )
        if create_match:
            return int(create_match.group(1))

        # Common model dimension hints from context
        model_hints = self._get_model_dimension_hint(code)
        if model_hints:
            return model_hints

        return None

    def _infer_dim_from_context(self, code: str, position: int) -> Optional[int]:
        import re

        context_start = max(0, position - 2000)
        context = code[context_start:position]

        patterns = [
            r'dim(?:ension)?\s*[=:]\s*(\d+)',
            r'FLOAT_VECTOR.*?dim\s*=\s*(\d+)',
            r'Dimension.*?(\d{2,4})',
            r'embedding.*?(\d{2,4})\s*-?d',
            r'vector.*?size.*?(\d{2,4})',
        ]
        for pattern in patterns:
            matches = list(re.finditer(pattern, context, re.IGNORECASE))
            if matches:
                return int(matches[-1].group(1))

        return None

    def _get_model_dimension_hint(self, code: str) -> Optional[int]:
        """Try to infer a reasonable default dimension from model names mentioned in code."""
        import re

        model_dim_map = {
            'minilm': 384,
            'mini-lm': 384,
            'all-minilm': 384,
            'ada': 1536,
            'ada-002': 1536,
            'text-embedding-ada': 1536,
            'bge-large': 1024,
            'bge-base': 768,
            'bge-small': 384,
            'sentence-transformers': 384,
            'paraphrase': 768,
            'mpnet': 768,
            'roberta': 768,
            'distilbert': 768,
            'gte': 1024,
            'e5': 1024,
            'e5-large': 1024,
            'cohere': 1024,
            'voyage': 1024,
        }

        code_lower = code.lower()
        for model_name, dim in model_dim_map.items():
            if model_name in code_lower:
                return dim

        if 'milvus' in code_lower or 'collection' in code_lower:
            float_vec_match = re.search(r'FLOAT_VECTOR.*?(\d{3,4})', code)
            if float_vec_match:
                return int(float_vec_match.group(1))

        return None

    def _is_illegal_success_bug_type(self, bug_type: Optional[str]) -> bool:
        bt = (bug_type or "").lower()
        return ("illegal success" in bt) or ("illegal_success" in bt)

    def _verify_mre(self, code: str, case_id: str, bug_type: Optional[str] = None) -> Tuple[str, str]:
        """
        Run MRE code in a subprocess and return (status, log).
        Statuses: SUCCESS, EXPECTED_REJECTION, INVALID_CODE, FAILED
        """
        import subprocess
        import sys
        import tempfile
        import textwrap
        
        print(f"[Agent 6] Verifying MRE for {case_id}...")
        
        # Indent the code to fit into the try-except block
        indented_code = textwrap.indent(code, "    ")
        
        # Create a temporary file for the MRE
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as tmp:
            # Inject small wrapper to catch and print specific errors
            wrapped_code = f"""
import sys
try:
{indented_code}
    print("MRE_EXECUTION_SUCCESS")
except Exception as e:
    # Print the exception type and message to stderr
    print(f"MRE_EXECUTION_FAILED: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
            tmp.write(wrapped_code)
            tmp_path = tmp.name

        try:
            # Run the MRE using the same python interpreter
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30 # 30s timeout
            )
            
            output = result.stdout + "\n" + result.stderr
            expects_exit_zero_success = self._is_illegal_success_bug_type(bug_type)
            
            # 1. Check for Syntax or Indentation errors (these happen before execution)
            # Subprocess might fail to even start or fail during parsing
            if "IndentationError" in output or "SyntaxError" in output or "NameError" in output:
                return "INVALID_CODE", f"MRE contains code quality errors:\n{output}"

            if result.returncode != 0:
                if "MilvusException" in output or "AssertionError" in output or "MRE_EXECUTION_FAILED" in output:
                    if any(err in output for err in ["AttributeError", "TypeError", "ImportError"]):
                         return "INVALID_CODE", f"MRE failed due to implementation error (not a bug):\n{output}"
                    if expects_exit_zero_success:
                        return (
                            "EXPECTED_REJECTION",
                            f"Reproduction Not Found: Request was rejected as expected (Illegal Success not reproduced).\nOutput:\n{output}",
                        )
                    return "SUCCESS", f"Reproduction Successful!\nOutput:\n{output}"
                return "FAILED", f"Reproduction Failed: Unknown error occurred.\nOutput:\n{output}"
            else:
                if expects_exit_zero_success:
                    return "SUCCESS", f"Reproduction Successful: Illegal Success reproduced (exit 0).\nOutput:\n{output}"
                return "FAILED", f"Reproduction Failed: Code executed without error (did not reproduce the bug).\nOutput:\n{output}"
                
        except subprocess.TimeoutExpired:
            return "FAILED", "Reproduction Failed: MRE timed out."
        except Exception as e:
            return "FAILED", f"Verification system error: {e}"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _generate_issue_for_defect(
        self,
        defect: DefectReport,
        env_context: Dict[str, Any],
        target_doc: Optional[str] = None
    ) -> Tuple[Optional[GitHubIssue], int]:
        import tenacity
        import json
        import re

        # We use raw output and manual parsing for maximum robustness with GLM models
        # instead of relying solely on JsonOutputParser which is brittle with markdown-heavy prompts
        chain = self.prompt.partial(format_instructions=self.parser.get_format_instructions()) | self.llm

        @tenacity.retry(
            stop=tenacity.stop_after_attempt(3),
            wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        def _invoke_with_retry():
            with get_openai_callback() as cb:
                v_refs = getattr(defect, "validated_references", [])
                
                # Get truncated relevant docs for this defect (avoids 6.6MB docs_context overflow)
                docs_map_for_defect = getattr(self, '_docs_map', {})
                relevant_docs = self._get_relevant_docs_for_defect(defect, docs_map_for_defect, max_chars=8000)
                
                # Truncate target_doc to safe size (max 3000 chars)
                target_doc_truncated = target_doc or "Not provided (source_url missing)"
                if len(target_doc_truncated) > 3000:
                    target_doc_truncated = target_doc_truncated[:3000] + "\n... [truncated for API limit]"
                
                input_data = {
                    "report": str(defect.model_dump()),
                    "target_doc": target_doc_truncated,
                    "env_context": {
                        "db_version": env_context.get("db_version", "Unknown") if isinstance(env_context, dict) else str(env_context),
                        "vector_config": env_context.get("vector_config", "Unknown") if isinstance(env_context, dict) else "",
                        "docs_context": relevant_docs,
                    },
                    "validated_refs": str(v_refs),
                }
                
                response = chain.invoke(input_data)
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Try to parse as JSON directly
                try:
                    res_dict = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Try to extract JSON from markdown blocks
                    json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
                    if json_match:
                        try:
                            res_dict = json.loads(json_match.group(1).strip())
                        except:
                            raise ValueError(f"Found JSON block but failed to parse: {content[:200]}...")
                    else:
                        # Last resort: look for anything that looks like a JSON object
                        json_match = re.search(r"(\{.*\})", content, re.DOTALL)
                        if json_match:
                            try:
                                res_dict = json.loads(json_match.group(1).strip())
                            except:
                                raise ValueError(f"Found something like JSON but failed to parse: {content[:200]}...")
                        else:
                            raise ValueError(f"No valid JSON found in response: {content[:200]}...")
                
                # Ensure result is a GitHubIssue object
                res = GitHubIssue(**res_dict)
                return res, cb.total_tokens

        return _invoke_with_retry()

    def _apply_verifier_outcome(self, defect: DefectReport, status: str, v_log: str) -> None:
        status_lower = (status or "").lower()
        defect.verification_status = status_lower or "failed"
        defect.verification_log = v_log or ""

        if status_lower == "success":
            defect.reproduced_bug = True
            defect.is_verified = True
            defect.false_positive = False
            defect.verifier_verdict = "reproduced_bug"
            return

        defect.reproduced_bug = False
        defect.is_verified = False

        if status_lower == "expected_rejection":
            defect.false_positive = True
            defect.verifier_verdict = "expected_rejection"
            return

        if status_lower == "invalid_code":
            defect.false_positive = False
            defect.verifier_verdict = "invalid_report"
            return

        log_lower = (v_log or "").lower()
        if "did not reproduce" in log_lower or "executed without error" in log_lower:
            defect.false_positive = True
            defect.verifier_verdict = "false_positive"
            return

        if "no mre code block found" in log_lower:
            defect.false_positive = False
            defect.verifier_verdict = "invalid_report"
            return

        defect.false_positive = False
        defect.verifier_verdict = "inconclusive"

    def execute(self, state: WorkflowState) -> WorkflowState:
        print(f"[Agent 6] Verifying and deduplicating {len(state.defect_reports)} defects...")
        
        # Deduplicate
        unique_defects = self._deduplicate(state.defect_reports)
        print(f"[Agent 6] After deduplication: {len(unique_defects)} unique defects.")
        
        # WBS 2.0: Load full docs from snapshot if state is truncated
        full_docs_context = state.db_config.docs_context if state.db_config else "No docs available"
        if "<TRUNCATED" in full_docs_context:
            try:
                import json
                doc_path = os.path.join(".trae", "runs", state.run_id, "raw_docs.json")
                if os.path.exists(doc_path):
                    with open(doc_path, "r", encoding="utf-8") as f:
                        doc_data = json.load(f)
                        full_docs_context = doc_data.get("full_docs", full_docs_context)
                        print(f"[Agent 6] Successfully loaded full evidence from {doc_path}")
            except Exception as e:
                print(f"[Agent 6] Warning: Failed to load raw_docs.json: {e}")

        run_dir = os.path.join(self.runs_root, state.run_id)
        os.makedirs(run_dir, exist_ok=True)
        
        # Build environment context from state (DO NOT include large docs_context here to avoid API token overflow)
        env_context = {
            "db_version": f"{state.db_config.db_name} {state.db_config.version}" if state.db_config else "Unknown",
            "docs_context": "(see target_doc and validated_refs for evidence)",
            "vector_config": str(state.contracts.l1_api) if state.contracts else "Unknown"
        }
        
        # NEW: Validate documentation references before generating issues
        # Parse full docs into map and store as instance variable for per-defect truncation
        docs_map = self._parse_docs_context(full_docs_context)
        self._docs_map = docs_map  # Store for _generate_issue_for_defect to use
        validated_references_count = 0
        for defect in unique_defects:
            # SKIP reference search for semantic/logic bugs (Type-4, Type-2)
            # as they usually don't have direct documentation proof.
            bug_type = (defect.bug_type or "").lower()
            is_semantic = "type-4" in bug_type or "type-2" in bug_type or "semantic" in bug_type or "consistency" in bug_type
            
            if is_semantic:
                print(f"[Agent 6] Case {defect.case_id}: Skipping doc search for semantic/logic bug ({defect.bug_type})")
                continue

            try:
                if docs_map:
                    # Get relevant references using validator
                    relevant_refs = self.ref_validator.get_relevant_references(
                        defect.root_cause_analysis,
                        docs_map
                    )

                    if relevant_refs:
                        # Store validated references on defect
                        if not hasattr(defect, 'validated_references'):
                            defect.validated_references = []
                        defect.validated_references = relevant_refs
                        validated_references_count += 1
                        print(f"[Agent 6] Case {defect.case_id}: Found {len(relevant_refs)} relevant doc references")
                    else:
                        print(f"[Agent 6] Case {defect.case_id}: No relevant doc references found (all filtered)")
            except Exception as e:
                print(f"[Agent 6] Case {defect.case_id}: Reference validation failed: {e}")

        print(f"[Agent 6] Validated references for {validated_references_count} defects")

        for defect in unique_defects:
            print(f"[Agent 6] Generating GitHub Issue for Case {defect.case_id}...")
            try:
                # Load target document if available
                target_doc = docs_map.get(defect.source_url) if defect.source_url else None
                if target_doc:
                    print(f"[Agent 6] Case {defect.case_id}: Providing target document from {defect.source_url}")
                
                issue, tokens_used = self._generate_issue_for_defect(defect, env_context, target_doc)
                
                if issue is None:
                    print(f"[Agent 6] Warning: LLM returned None for Case {defect.case_id}. Skipping Issue generation.")
                    self._apply_verifier_outcome(defect, "failed", "Issue generation returned None; cannot verify MRE.")
                    continue
                    
                state.total_tokens_used += tokens_used
                
                mre_code = self._extract_mre_code(issue.body_markdown)
                if mre_code:
                    mre_code = self._inject_real_vectors(mre_code, defect)
                    defect.mre_code = mre_code
                    status, v_log = self._verify_mre(mre_code, defect.case_id, defect.bug_type)
                    self._apply_verifier_outcome(defect, status, v_log)
                else:
                    self._apply_verifier_outcome(defect, "failed", "No MRE code block found in generated issue.")

                if defect.reproduced_bug:
                    filename = os.path.join(run_dir, f"GitHub_Issue_{defect.case_id}.md")
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(f"# {issue.title}\n\n")
                        f.write(issue.body_markdown)
                    defect.issue_url = filename
                else:
                    defect.issue_url = None
                
            except Exception as e:
                print(f"[Agent 6] Failed to generate issue for {defect.case_id}: {e}")
                self._apply_verifier_outcome(defect, "failed", f"Issue generation/verification failed: {e}")
                defect.issue_url = None
                
        state.defect_reports = unique_defects
        state.verified_defects = [d for d in unique_defects if getattr(d, "reproduced_bug", False)]
        return state

def agent6_defect_verifier(state: WorkflowState) -> WorkflowState:
    """Wrapper function for LangGraph Node."""
    agent = DefectVerifierAgent()
    return agent.execute(state)
