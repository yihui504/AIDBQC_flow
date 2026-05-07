from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.panel import Panel

from src.config import AppConfig
from src.hook_runner import TestHookRunner, HookResult, create_default_hooks
from src.safety_guard import TestSafetyGuard, SafetyLevel
from src.session import TestSession, TestState
from src.state import Stage, FuzzingFeedback, WorkflowState
from src.tools.db_operator import MilvusOperator
from src.tools.doc_analyzer import DocAnalyzer
from src.tools.code_runner import CodeRunner
from src.tools.web_searcher import WebSearcher
from src.tools.source_analyzer import SourceAnalyzer
from src.tools.internal_prober import InternalProber
from src.tools.contract_refiner import ContractRefiner
from src.tools.defect_verifier import DefectVerifier
from src.telemetry import telemetry_sink, TelemetryEvent
from src.compaction import TestRoundCompaction, CompactionConfig, CompactionResult
from src.compression import ToolOutputCompressor, CompressionConfig
from src.events import TestEventEmitter, TestEvent, TestEventType, Provenance, create_logging_emitter
from src.recovery import TestRecoveryEngine, RecoveryResult, FaultScenario, EscalationPolicy
from src.ui.display import AgentDisplay
from src.ui.input_handler import AsyncInputHandler, UserCommand

logger = logging.getLogger(__name__)
console = Console()

SYSTEM_PROMPT = """\
You are an AI Database Quality Control (AI-DB-QC) expert agent. Your mission is to perform deep gray-box/white-box testing on Milvus vector databases and produce high-quality, reproducible bug issues.

## 5-Stage Framework

You MUST follow these 5 stages in order. Each stage has specific goals and available tools. Use the `update_stage` tool to transition between stages when you have completed the current stage's work.

### Stage 1: UNDERSTANDING
- Crawl and analyze Milvus official documentation
- Extract contract rules (L1: API contracts, L2: Semantic contracts, L3: Application contracts)
- Search web for known issues and version-specific bugs
- Clone and analyze Milvus source code for internal mechanisms
- Use source_analyze_module to understand index algorithms, search logic, data coordination
- Build a comprehensive understanding of the target Milvus version
- Output: A set of validated contracts with confidence scores
- When done, call update_stage("generation")

### Stage 2: GENERATION
- Based on contracts from Stage 1, generate targeted test cases
- Focus on 5 test categories:
  1. API layer: parameter boundaries, error handling, state transitions
  2. Index algorithm: IVF/HNSW/DISKANN specific behaviors, nprobe/ef parameter sensitivity
  3. Vector computation: L2/IP/COSINE distance precision and consistency
  4. Distributed consistency: write-then-read consistency, failure recovery
  5. Data consistency: concurrent writes, upsert/delete search accuracy
- Use contract_validate_source to verify contracts against source code
- Use structured feedback from previous rounds to focus on weak points
- Generate MRE (Minimal Reproducible Example) code for each test case
- Output: Test cases with MRE code targeting specific contracts
- When done, call update_stage("execution")

### Stage 3: EXECUTION
- Execute test cases against the Milvus instance
- Create test collections (with qc_test_ prefix), insert data, run searches
- Use probe_* tools to inspect internal state (segments, indexes, metrics)
- Record all operations: request parameters, response data, timing, database state
- Capture Docker logs if available
- Output: Execution results with full evidence chain
- When done, call update_stage("verification")

### Stage 4: VERIFICATION
- Verify defects found in Stage 3
- Run MRE code in clean environment if possible
- Use contract_tri_validate for tri-source validation (doc + source + behavior)
- Perform developer-perspective review: is this bug reproducible? Is the evidence chain complete?
- Check ANN whitelist: is this an expected approximation behavior?
- Calculate false positive risk for each defect
- Generate structured FuzzingFeedback for the next round using generate_feedback
- Output: Verified defects with confidence scores and FuzzingFeedback
- When done, call update_stage("reporting")

### Stage 5: REPORTING
- Generate bug issues in Markdown format following Milvus bug report template
- Include: MRE code, documentation references, execution logs, Docker logs, database state snapshots
- Only output issues that pass developer review (false positive risk < 30%)
- Output: Final bug issues ready for submission
- When done, call generate_feedback to prepare for the next round

## Key Principles

1. **Contract-Driven Testing**: Every test must target a specific contract. If no contract exists, create one first.
2. **Evidence Chain Completeness**: Every defect must have: doc reference + execution log + MRE code + Docker logs. Incomplete evidence = not a valid defect.
3. **False Positive Governance**: Apply 4-level governance:
   - P0: Contract extraction accuracy (multi-source validation with contract_tri_validate)
   - P1: MRE code quality (clean environment verification)
   - P2: Oracle accuracy (reasoning + traditional oracle + ANN whitelist)
   - P3: Over-interpretation governance (developer review + ANN whitelist)
4. **ANN Approximation Awareness**: ANN algorithms (HNSW, IVF, DISKANN) are approximate by nature. recall < 100% is NOT a bug unless the documentation guarantees exact results. Key thresholds:
   - HNSW: recall >= 95% is normal (ef_search dependent)
   - IVF_FLAT: recall >= 90% is normal (nprobe dependent)
   - IVF_PQ: recall >= 85% is normal (highly approximate)
   - DISKANN: recall >= 90% is normal
   - COSINE metric: small floating-point epsilon differences are expected
5. **Test Collection Isolation**: All test collections MUST use the "qc_test_" prefix. Never touch production collections.
6. **Structured Feedback**: After each round, generate FuzzingFeedback to guide the next round's testing strategy.
7. **Deep Gray-Box Testing**: Use source_analyze_module and probe_* tools to understand internal mechanisms, not just API behavior.

## Tool Usage Guidelines

- Use `db_operator` tools for all Milvus operations (create, insert, search, query, etc.)
- Use `doc_analyzer` tools to search and validate documentation references
- Use `code_runner` tools to execute MRE code and verify defects
- Use `web_searcher` tools to find known issues and version-specific information
- Use `source_*` tools to clone, search, read, and analyze Milvus source code
- Use `probe_*` tools to inspect Milvus internal state (health, metrics, segments, indexes)
- Use `contract_*` tools to validate contracts against source code and behavior
- Always record tool call results in your reasoning for evidence chain

## Output Format

When reporting a defect, always include:
- Defect type (TYPE1_ILLEGAL_SUCCESS, TYPE2_DIAGNOSTIC_GAP, TYPE2PF_PRECONDITION_FAIL, TYPE3_TRADITIONAL, TYPE4_SEMANTIC_VIOLATION)
- Severity (critical, high, medium, low)
- Contract violated (with source URL)
- MRE code
- Expected vs Actual behavior
- Evidence completeness score
- ANN approximation check result (if applicable)
"""

_STAGE_ALLOWED_TOOLS = {
    Stage.UNDERSTANDING: {"doc_search", "doc_validate_reference", "web_search", "web_crawl", "update_stage", "generate_feedback", "db_health_check", "db_list_collections", "source_clone_repo", "source_search", "source_read", "source_analyze_module", "probe_health", "probe_metrics", "contract_validate_source"},
    Stage.GENERATION: {"doc_search", "doc_validate_reference", "web_search", "web_crawl", "update_stage", "generate_feedback", "db_health_check", "db_list_collections", "db_get_collection_info", "source_search", "source_read", "source_analyze_module", "probe_collection_info", "probe_index_state", "contract_validate_source", "contract_validate_behavior"},
    Stage.EXECUTION: {"db_create_collection", "db_insert_data", "db_search", "db_query", "db_upsert_data", "db_flush", "db_load_collection", "db_release_collection", "db_create_partition", "db_delete_data", "db_drop_collection", "db_get_collection_info", "db_list_collections", "db_health_check", "code_run_mre", "update_stage", "generate_feedback", "probe_health", "probe_metrics", "probe_collection_info", "probe_index_state", "probe_segment_info"},
    Stage.VERIFICATION: {"code_run_mre", "db_search", "db_query", "db_get_collection_info", "db_list_collections", "db_health_check", "update_stage", "generate_feedback", "record_defect", "probe_health", "probe_collection_info", "probe_index_state", "probe_segment_info", "contract_validate_source", "contract_validate_behavior", "contract_tri_validate", "verify_defect"},
    Stage.REPORTING: {"record_defect", "update_stage", "generate_feedback", "db_health_check", "contract_validate_source", "contract_validate_behavior", "contract_tri_validate", "verify_defect"},
}


@dataclass
class TestRoundSummary:
    round_id: str = ""
    stage: str = ""
    tool_calls: int = 0
    defects_found: int = 0
    token_usage: int = 0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""


@dataclass
class UsageTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens


class TestRuntime:
    def __init__(
        self,
        config: AppConfig,
        session: Optional[TestSession] = None,
        safety_guard: Optional[TestSafetyGuard] = None,
        hook_runner: Optional[TestHookRunner] = None,
    ):
        self.config = config
        self.session = session or TestSession()
        self.safety_guard = safety_guard or TestSafetyGuard()
        self.hook_runner = hook_runner or create_default_hooks()
        self.usage_tracker = UsageTracker()

        self.db_operator = MilvusOperator(config)
        self.doc_analyzer = DocAnalyzer(config)
        self.code_runner = CodeRunner(timeout=config.harness.mre_timeout)
        self.web_searcher = WebSearcher()
        self.source_analyzer = SourceAnalyzer(config)
        self.internal_prober = InternalProber(config=config, db_operator=self.db_operator)
        self.contract_refiner = ContractRefiner(config)
        self.defect_verifier = DefectVerifier(config=config, code_runner=self.code_runner)
        self.compactor = TestRoundCompaction()
        self.compressor = ToolOutputCompressor()
        self.event_emitter = create_logging_emitter()
        self.recovery_engine = TestRecoveryEngine(event_emitter=self.event_emitter, db_operator=self.db_operator, compactor=self.compactor)
        self.display = AgentDisplay(self.event_emitter)
        self.input_handler = AsyncInputHandler()

        self._agent: Optional[Agent] = None
        self._defect_counter = 0
        self._max_test_iterations = 50
        self._workflow_state: Optional[WorkflowState] = None
        self._stage_iterations = 0

    def _create_agent(self) -> Agent:
        model = self.config.create_pro_model()
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            deps_type=WorkflowState,
            retries=self.config.llm.max_retries,
        )
        self._register_tools(agent)
        return agent

    def _check_stage_guard(self, tool_name: str) -> Optional[str]:
        ts = self.session.test_state
        allowed = _STAGE_ALLOWED_TOOLS.get(ts.current_stage, set())
        if tool_name not in allowed:
            return f"Tool '{tool_name}' is not available in {ts.current_stage.value} stage. Available tools: {', '.join(sorted(allowed))}"
        return None

    async def _execute_with_guard(self, tool_name: str, args: dict, fn, ctx: RunContext[WorkflowState]) -> str:
        stage_error = self._check_stage_guard(tool_name)
        if stage_error:
            return json.dumps({"success": False, "error": stage_error})

        hook_result = self.hook_runner.run_pre_hooks(tool_name, args)
        if not hook_result.proceed:
            return json.dumps({"success": False, "error": f"Blocked by safety hook: {hook_result.message}"})

        if not self.safety_guard.check_execution(tool_name, args):
            return json.dumps({"success": False, "error": f"Blocked by safety guard: operation exceeds active safety level ({self.safety_guard.active_level.value})"})

        effective_args = hook_result.modified_args or args

        self.event_emitter.emit(TestEvent(
            event_type=TestEventType.TOOL_INVOKED,
            session_id=self.session.session_id,
            round_id=f"R{self.session.test_state.current_round:03d}",
            data={"tool": tool_name, "args_summary": json.dumps(args)[:80]},
        ))

        tool_start = time.time()
        try:
            result = await asyncio.get_running_loop().run_in_executor(None, lambda: fn(effective_args))
            if hasattr(result, 'model_dump_json'):
                json_result = result.model_dump_json()
            elif isinstance(result, dict):
                json_result = json.dumps(result)
            else:
                json_result = str(result)
        except Exception as e:
            self.hook_runner.run_post_failure_hooks(tool_name, args)
            self.event_emitter.emit(TestEvent(
                event_type=TestEventType.TOOL_COMPLETED,
                session_id=self.session.session_id,
                round_id=f"R{self.session.test_state.current_round:03d}",
                data={"tool": tool_name, "success": False, "error": str(e)[:80], "duration_ms": (time.time() - tool_start) * 1000},
            ))
            return json.dumps({"success": False, "error": str(e)})

        try:
            parsed = json.loads(json_result)
            if not (isinstance(parsed, dict) and parsed.get("success") is False):
                compressed = self.compressor.compress(tool_name, json_result)
                if len(compressed) < len(json_result):
                    json_result = compressed
        except (json.JSONDecodeError, ValueError):
            json_result = self.compressor.compress(tool_name, json_result)

        ctx.deps.context.add_tool_call(tool_name, args, json_result[:200])
        self.hook_runner.run_post_hooks(tool_name, args)

        self.event_emitter.emit(TestEvent(
            event_type=TestEventType.TOOL_COMPLETED,
            session_id=self.session.session_id,
            round_id=f"R{self.session.test_state.current_round:03d}",
            data={"tool": tool_name, "success": True, "duration_ms": (time.time() - tool_start) * 1000},
        ))

        return json_result

    def _build_stage_prompt(self) -> str:
        ts = self.session.test_state
        parts = [
            f"Current state: Round {ts.current_round}/{ts.max_rounds}, Stage: {ts.current_stage.value}",
            f"Target: Milvus {ts.target_version}",
        ]
        if ts.scenario:
            parts.append(f"Scenario: {ts.scenario}")
        parts.append(f"Contracts found: {len(ts.contracts.all_rules())}")
        parts.append(f"Defects found: {len(ts.defects)}")
        parts.append(f"Issues generated: {len(ts.issues)}")
        parts.append(f"Token usage: {ts.token_usage}/{ts.max_token_budget}")

        if ts.feedback.weak_points:
            parts.append(f"\nFuzzing feedback from last round:")
            parts.append(ts.feedback.to_prompt_text())

        stage_prompts = {
            Stage.UNDERSTANDING: "\nYou are in the UNDERSTANDING stage. Your task: Analyze Milvus documentation and extract contract rules. Use doc_search and web_search tools to gather information. When you have enough contracts, call update_stage('generation').",
            Stage.GENERATION: "\nYou are in the GENERATION stage. Your task: Based on contracts, generate targeted test cases with MRE code. Focus on weak points from feedback. When ready to execute, call update_stage('execution').",
            Stage.EXECUTION: "\nYou are in the EXECUTION stage. Your task: Execute test cases against Milvus using db_* tools. Create collections, insert data, run searches. Record all results. When done, call update_stage('verification').",
            Stage.VERIFICATION: "\nYou are in the VERIFICATION stage. Your task: Verify defects using code_run_mre. Review evidence chains. Call generate_feedback when ready. Then call update_stage('reporting').",
            Stage.REPORTING: "\nYou are in the REPORTING stage. Your task: Generate final bug issues using record_defect. Only report defects with strong evidence (completeness > 50%). Call generate_feedback to prepare for next round.",
        }
        parts.append(stage_prompts.get(ts.current_stage, ""))

        return "\n".join(parts)

    def _register_tools(self, agent: Agent) -> None:
        runtime = self

        @agent.tool
        async def db_create_collection(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            dimension: int = 128,
            index_type: str = "IVF_FLAT",
            metric_type: str = "L2",
        ) -> str:
            args = {"collection_name": collection_name, "dimension": dimension, "index_type": index_type, "metric_type": metric_type}
            return await runtime._execute_with_guard("db_create_collection", args,
                lambda a: runtime.db_operator.create_collection(**a), ctx)

        @agent.tool
        async def db_insert_data(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            count: int = 100,
            dimension: int = 128,
            distribution: str = "normal",
        ) -> str:
            args = {"collection_name": collection_name, "count": count, "dimension": dimension}
            def _fn(a):
                data = runtime.code_runner.generate_test_data(dimension=a.get("dimension", dimension), count=a.get("count", count), distribution=distribution)
                return runtime.db_operator.insert_data(collection_name=a.get("collection_name", collection_name), vectors=data["vectors"])
            return await runtime._execute_with_guard("db_insert_data", args, _fn, ctx)

        @agent.tool
        async def db_search(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            dimension: int = 128,
            top_k: int = 10,
            metric_type: str = "L2",
        ) -> str:
            import numpy as np
            query_vector = np.random.randn(dimension).astype(np.float32).tolist()
            args = {"collection_name": collection_name, "top_k": top_k, "metric_type": metric_type}
            return await runtime._execute_with_guard("db_search", args,
                lambda a: runtime.db_operator.search(collection_name=a.get("collection_name", collection_name), query_vector=query_vector, top_k=a.get("top_k", top_k), metric_type=a.get("metric_type", metric_type)), ctx)

        @agent.tool
        async def db_query(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            filter_expr: str,
            output_fields: str = "id",
            limit: int = 100,
        ) -> str:
            args = {"collection_name": collection_name, "filter_expr": filter_expr, "output_fields": output_fields, "limit": limit}
            return await runtime._execute_with_guard("db_query", args,
                lambda a: runtime.db_operator.query(collection_name=a.get("collection_name", collection_name), filter_expr=a.get("filter_expr", filter_expr), output_fields=[f.strip() for f in a.get("output_fields", output_fields).split(",")], limit=a.get("limit", limit)), ctx)

        @agent.tool
        async def db_delete_data(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            filter_expr: Optional[str] = None,
            ids: Optional[str] = None,
        ) -> str:
            args = {"collection_name": collection_name}
            def _fn(a):
                cn = a.get("collection_name", collection_name)
                id_list = [x.strip() for x in ids.split(",")] if ids else None
                return runtime.db_operator.delete_data(collection_name=cn, filter_expr=filter_expr, ids=id_list)
            return await runtime._execute_with_guard("db_delete_data", args, _fn, ctx)

        @agent.tool
        async def db_upsert_data(
            ctx: RunContext[WorkflowState],
            collection_name: str,
            count: int = 10,
            dimension: int = 128,
            start_id: int = 1,
        ) -> str:
            args = {"collection_name": collection_name, "count": count, "dimension": dimension, "start_id": start_id}
            def _fn(a):
                data = runtime.code_runner.generate_test_data(dimension=a.get("dimension", dimension), count=a.get("count", count))
                ids = list(range(a.get("start_id", start_id), a.get("start_id", start_id) + a.get("count", count)))
                return runtime.db_operator.upsert_data(collection_name=a.get("collection_name", collection_name), vectors=data["vectors"], ids=ids)
            return await runtime._execute_with_guard("db_upsert_data", args, _fn, ctx)

        @agent.tool
        async def db_flush(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("db_flush", {"collection_name": collection_name},
                lambda a: runtime.db_operator.flush(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def db_load_collection(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("db_load_collection", {"collection_name": collection_name},
                lambda a: runtime.db_operator.load_collection(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def db_release_collection(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("db_release_collection", {"collection_name": collection_name},
                lambda a: runtime.db_operator.release_collection(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def db_get_collection_info(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("db_get_collection_info", {"collection_name": collection_name},
                lambda a: runtime.db_operator.get_collection_info(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def db_list_collections(ctx: RunContext[WorkflowState]) -> str:
            return await runtime._execute_with_guard("db_list_collections", {},
                lambda a: runtime.db_operator.list_collections(), ctx)

        @agent.tool
        async def db_drop_collection(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("db_drop_collection", {"collection_name": collection_name},
                lambda a: runtime.db_operator.drop_collection(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def db_create_partition(ctx: RunContext[WorkflowState], collection_name: str, partition_name: str) -> str:
            return await runtime._execute_with_guard("db_create_partition", {"collection_name": collection_name, "partition_name": partition_name},
                lambda a: runtime.db_operator.create_partition(collection_name=a["collection_name"], partition_name=a["partition_name"]), ctx)

        @agent.tool
        async def db_health_check(ctx: RunContext[WorkflowState]) -> str:
            return await runtime._execute_with_guard("db_health_check", {},
                lambda a: runtime.db_operator.health_check(), ctx)

        @agent.tool
        async def doc_search(ctx: RunContext[WorkflowState], query: str, max_results: int = 10) -> str:
            return await runtime._execute_with_guard("doc_search", {"query": query, "max_results": max_results},
                lambda a: runtime.doc_analyzer.search_docs(query=a.get("query", query), max_results=a.get("max_results", max_results)), ctx)

        @agent.tool
        async def doc_validate_reference(ctx: RunContext[WorkflowState], url: str, claim: str) -> str:
            args = {"url": url, "claim": claim}
            def _fn(a):
                result = runtime.doc_analyzer.validate_reference(url=a.get("url", url), claim=a.get("claim", claim))
                return json.dumps(result)
            return await runtime._execute_with_guard("doc_validate_reference", args, _fn, ctx)

        @agent.tool
        async def code_run_mre(
            ctx: RunContext[WorkflowState],
            mre_code: str,
            milvus_host: str = "localhost",
            milvus_port: int = 19530,
        ) -> str:
            args = {"mre_code": mre_code, "milvus_host": milvus_host, "milvus_port": milvus_port}
            def _fn(a):
                return runtime.code_runner.run_mre(
                    mre_code=a.get("mre_code", mre_code),
                    milvus_host=a.get("milvus_host", milvus_host),
                    milvus_port=a.get("milvus_port", milvus_port),
                )
            return await runtime._execute_with_guard("code_run_mre", args, _fn, ctx)

        @agent.tool
        async def web_search(ctx: RunContext[WorkflowState], query: str, max_results: int = 5) -> str:
            args = {"query": query, "max_results": max_results}
            return await runtime._execute_with_guard("web_search", args,
                lambda a: runtime.web_searcher.search_web(query=a.get("query", query), max_results=a.get("max_results", max_results)), ctx)

        @agent.tool
        async def web_crawl(ctx: RunContext[WorkflowState], url: str) -> str:
            args = {"url": url}
            def _fn(a):
                result = runtime.web_searcher.crawl_url_sync(url=a.get("url", url))
                if result is None:
                    return {"success": False, "error": "Failed to crawl URL", "url": a.get("url", url)}
                return {"success": True, "content": result[:5000], "url": a.get("url", url)}
            return await runtime._execute_with_guard("web_crawl", args, _fn, ctx)

        @agent.tool
        async def source_clone_repo(
            ctx: RunContext[WorkflowState],
            url: str = "https://github.com/milvus-io/milvus.git",
            branch: str = "master",
        ) -> str:
            args = {"url": url, "branch": branch}
            return await runtime._execute_with_guard("source_clone_repo", args,
                lambda a: runtime.source_analyzer.clone_repo(url=a.get("url", url), branch=a.get("branch", branch)), ctx)

        @agent.tool
        async def source_search(ctx: RunContext[WorkflowState], pattern: str, max_results: int = 20) -> str:
            args = {"pattern": pattern, "max_results": max_results}
            def _fn(a):
                results = runtime.source_analyzer.search_source(pattern=a.get("pattern", pattern), max_results=a.get("max_results", max_results))
                return [{"file_path": r.file_path, "line": r.line_number, "content": r.content[:100]} for r in results]
            return await runtime._execute_with_guard("source_search", args, _fn, ctx)

        @agent.tool
        async def source_read(ctx: RunContext[WorkflowState], file_path: str, start_line: int = 1, end_line: int = 100) -> str:
            args = {"file_path": file_path, "start_line": start_line, "end_line": end_line}
            return await runtime._execute_with_guard("source_read", args,
                lambda a: runtime.source_analyzer.read_source(file_path=a.get("file_path", file_path), start_line=a.get("start_line", start_line), end_line=a.get("end_line", end_line)), ctx)

        @agent.tool
        async def source_analyze_module(ctx: RunContext[WorkflowState], module_path: str) -> str:
            args = {"module_path": module_path}
            return await runtime._execute_with_guard("source_analyze_module", args,
                lambda a: runtime.source_analyzer.extract_internal_mechanisms(module_path=a.get("module_path", module_path)), ctx)

        @agent.tool
        async def probe_health(ctx: RunContext[WorkflowState]) -> str:
            return await runtime._execute_with_guard("probe_health", {},
                lambda a: runtime.internal_prober.check_health(), ctx)

        @agent.tool
        async def probe_metrics(ctx: RunContext[WorkflowState]) -> str:
            return await runtime._execute_with_guard("probe_metrics", {},
                lambda a: runtime.internal_prober.get_metrics(), ctx)

        @agent.tool
        async def probe_collection_info(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("probe_collection_info", {"collection_name": collection_name},
                lambda a: runtime.internal_prober.describe_collection(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def probe_index_state(ctx: RunContext[WorkflowState], collection_name: str, field_name: str = "vector") -> str:
            args = {"collection_name": collection_name, "field_name": field_name}
            return await runtime._execute_with_guard("probe_index_state", args,
                lambda a: runtime.internal_prober.get_index_state(collection_name=a["collection_name"], field_name=a.get("field_name", field_name)), ctx)

        @agent.tool
        async def probe_segment_info(ctx: RunContext[WorkflowState], collection_name: str) -> str:
            return await runtime._execute_with_guard("probe_segment_info", {"collection_name": collection_name},
                lambda a: runtime.internal_prober.get_segment_info(collection_name=a["collection_name"]), ctx)

        @agent.tool
        async def contract_validate_source(
            ctx: RunContext[WorkflowState],
            contract_content: str,
            module_path: str,
        ) -> str:
            args = {"contract_content": contract_content, "module_path": module_path}
            def _fn(a):
                from src.models.contract import ContractRule, ContractWithConfidence, ContractLevel, ContractSource
                rule = ContractRule(rule_id=f"CR-dyn-{id(a)}", level=ContractLevel.L2_SEMANTIC, content=a.get("contract_content", contract_content), constraint="dynamic_validation")
                contract = ContractWithConfidence(rule=rule, confidence_score=0.5, sources=[ContractSource.DOCUMENTATION])
                analysis = runtime.source_analyzer.extract_internal_mechanisms(module_path=a.get("module_path", module_path))
                result = runtime.contract_refiner.validate_contract_with_source(contract, analysis)
                return {"valid": result.valid, "confidence": result.confidence, "agree": result.sources_agree, "disagree": result.sources_disagree, "notes": result.notes}
            return await runtime._execute_with_guard("contract_validate_source", args, _fn, ctx)

        @agent.tool
        async def contract_validate_behavior(
            ctx: RunContext[WorkflowState],
            contract_content: str,
            test_success: bool,
            actual_behavior: str = "",
            expected_behavior: str = "",
        ) -> str:
            args = {"contract_content": contract_content, "test_success": test_success, "actual_behavior": actual_behavior, "expected_behavior": expected_behavior}
            def _fn(a):
                from src.models.contract import ContractRule, ContractWithConfidence, ContractLevel, ContractSource
                rule = ContractRule(rule_id=f"CR-dyn-{id(a)}", level=ContractLevel.L2_SEMANTIC, content=a.get("contract_content", contract_content), constraint="dynamic_validation")
                contract = ContractWithConfidence(rule=rule, confidence_score=0.5, sources=[ContractSource.DOCUMENTATION])
                test_result = {"success": a.get("test_success", test_success), "actual_behavior": a.get("actual_behavior", actual_behavior), "expected_behavior": a.get("expected_behavior", expected_behavior)}
                result = runtime.contract_refiner.validate_contract_with_behavior(contract, test_result)
                return {"valid": result.valid, "confidence": result.confidence, "agree": result.sources_agree, "disagree": result.sources_disagree, "notes": result.notes}
            return await runtime._execute_with_guard("contract_validate_behavior", args, _fn, ctx)

        @agent.tool
        async def contract_tri_validate(
            ctx: RunContext[WorkflowState],
            contract_content: str,
            module_path: str,
            test_success: bool,
            actual_behavior: str = "",
            expected_behavior: str = "",
        ) -> str:
            args = {"contract_content": contract_content, "module_path": module_path, "test_success": test_success, "actual_behavior": actual_behavior, "expected_behavior": expected_behavior}
            def _fn(a):
                from src.models.contract import ContractRule, ContractWithConfidence, ContractLevel, ContractSource
                rule = ContractRule(rule_id=f"CR-dyn-{id(a)}", level=ContractLevel.L2_SEMANTIC, content=a.get("contract_content", contract_content), constraint="dynamic_validation")
                contract = ContractWithConfidence(rule=rule, confidence_score=0.5, sources=[ContractSource.DOCUMENTATION])
                source_analysis = runtime.source_analyzer.extract_internal_mechanisms(module_path=a.get("module_path", module_path))
                behavior_result = {"success": a.get("test_success", test_success), "actual_behavior": a.get("actual_behavior", actual_behavior), "expected_behavior": a.get("expected_behavior", expected_behavior)}
                result = runtime.contract_refiner.tri_source_validate(contract, source_analysis, behavior_result)
                return {"valid": result.valid, "confidence": result.confidence, "agree": result.sources_agree, "disagree": result.sources_disagree, "notes": result.notes}
            return await runtime._execute_with_guard("contract_tri_validate", args, _fn, ctx)

        @agent.tool
        async def verify_defect(
            ctx: RunContext[WorkflowState],
            defect_id: str,
            verify_mre: bool = True,
        ) -> str:
            args = {"defect_id": defect_id, "verify_mre": verify_mre}
            def _fn(a):
                from src.models.issue import BugIssue, VerificationStatus
                did = a.get("defect_id", defect_id)
                ts = ctx.deps.core
                target_defect = None
                for d in ts.defects:
                    if d.defect_id == did:
                        target_defect = d
                        break
                if target_defect is None:
                    return {"success": False, "error": f"Defect {did} not found"}

                review = runtime.defect_verifier.developer_review(
                    BugIssue(
                        issue_id=did.replace("DEF-", "ISS-"),
                        title=target_defect.title,
                        defect_type=target_defect.defect_type,
                        severity=target_defect.severity,
                        mre_code=target_defect.evidence_chain.mre_code if target_defect.evidence_chain else "",
                        expected_behavior="",
                        actual_behavior=target_defect.description,
                        evidence_chain=target_defect.evidence_chain,
                        doc_reference_url=target_defect.source_url,
                        verification_status=VerificationStatus.PENDING,
                        milvus_version=ts.target_version,
                    )
                )

                mre_result = None
                if a.get("verify_mre", verify_mre) and target_defect.evidence_chain and target_defect.evidence_chain.mre_code:
                    mre_result = runtime.defect_verifier.verify_mre_in_clean_env(
                        target_defect.evidence_chain.mre_code,
                        milvus_host=next((i.host for i in runtime.config.database.instances if i.type == "milvus"), "localhost"),
                        milvus_port=next((i.port for i in runtime.config.database.instances if i.type == "milvus"), 19530),
                    )

                evidence_check = runtime.defect_verifier.check_evidence_completeness(target_defect)

                return {
                    "success": True,
                    "defect_id": did,
                    "review_passed": review.passed,
                    "false_positive_risk": review.false_positive_risk,
                    "reproducibility": review.reproducibility,
                    "evidence_completeness": review.evidence_completeness,
                    "problem_clarity": review.problem_clarity,
                    "reference_authenticity": review.reference_authenticity,
                    "reasoning": review.reasoning,
                    "mre_verification": {"status": mre_result.status, "success": mre_result.success, "duration_ms": mre_result.duration_ms} if mre_result else None,
                    "evidence_check": evidence_check,
                }
            return await runtime._execute_with_guard("verify_defect", args, _fn, ctx)

        @agent.tool
        async def update_stage(ctx: RunContext[WorkflowState], stage: str) -> str:
            try:
                new_stage = Stage(stage)
            except ValueError:
                return json.dumps({"success": False, "error": f"Invalid stage: {stage}"})
            old_stage = ctx.deps.core.current_stage
            stage_order = [Stage.UNDERSTANDING, Stage.GENERATION, Stage.EXECUTION, Stage.VERIFICATION, Stage.REPORTING]
            old_idx = stage_order.index(old_stage)
            new_idx = stage_order.index(new_stage)
            if new_idx < old_idx:
                return json.dumps({"success": False, "error": f"Cannot go backwards from {old_stage.value} to {new_stage.value}"})
            if new_idx > old_idx + 1:
                return json.dumps({"success": False, "error": f"Cannot skip stages from {old_stage.value} to {new_stage.value}. Next stage is {stage_order[old_idx + 1].value}"})
            ctx.deps.core.current_stage = new_stage
            runtime.session.test_state.current_stage = new_stage
            runtime._stage_iterations = 0
            ctx.deps.context.add_execution_log(f"Stage transition: {old_stage.value} -> {new_stage.value}")
            telemetry_sink.log_event(TelemetryEvent(
                trace_id=ctx.deps.core.run_id, node_name="stage_transition",
                event_type="STAGE_CHANGE", state_delta={"from": old_stage.value, "to": new_stage.value},
            ))

            runtime.event_emitter.emit(TestEvent(
                event_type=TestEventType.STAGE_TRANSITION,
                session_id=runtime.session.session_id,
                round_id=f"R{ctx.deps.core.current_round:03d}",
                data={"from": old_stage.value, "to": new_stage.value},
            ))

            return json.dumps({"success": True, "from": old_stage.value, "to": new_stage.value})

        @agent.tool
        async def record_defect(
            ctx: RunContext[WorkflowState],
            defect_type: str,
            severity: str,
            title: str,
            description: str,
            mre_code: str,
            expected_behavior: str,
            actual_behavior: str,
            doc_reference_url: str = "",
        ) -> str:
            from src.models.defect import DefectReport, DefectType, EvidenceChain, Severity, DocReference, ExecutionStep
            from src.models.issue import BugIssue, VerificationStatus

            stage_error = runtime._check_stage_guard("record_defect")
            if stage_error:
                return json.dumps({"success": False, "error": stage_error})

            runtime.event_emitter.emit(TestEvent(
                event_type=TestEventType.TOOL_INVOKED,
                session_id=runtime.session.session_id,
                round_id=f"R{ctx.deps.core.current_round:03d}",
                data={"tool": "record_defect", "args_summary": f"{severity}/{defect_type}: {title[:40]}"},
            ))

            try:
                dt = DefectType(defect_type)
                sev = Severity(severity)
            except ValueError as e:
                return json.dumps({"success": False, "error": f"Invalid enum value: {e}"})

            runtime._defect_counter += 1
            defect_id = f"DEF-{ctx.deps.core.run_id}-{runtime._defect_counter:03d}"
            issue_id = f"ISS-{ctx.deps.core.run_id}-{runtime._defect_counter:03d}"

            doc_refs = []
            if doc_reference_url:
                doc_refs.append(DocReference(url=doc_reference_url, title="Contract Reference", snippet=description[:200], relevance_score=0.5))

            exec_steps = []
            for i, log_entry in enumerate(ctx.deps.context.execution_log[-20:]):
                exec_steps.append(ExecutionStep(step_number=i + 1, action=str(log_entry)[:200]))

            evidence = EvidenceChain(mre_code=mre_code, execution_log=exec_steps, doc_references=doc_refs)
            defect = DefectReport(
                defect_id=defect_id, defect_type=dt, severity=sev, title=title,
                description=description, evidence_chain=evidence, source_url=doc_reference_url or None,
            )
            ctx.deps.core.defects.append(defect)
            runtime.session.test_state.defects.append(defect)

            issue = BugIssue(
                issue_id=issue_id, title=title, defect_type=dt, severity=sev,
                mre_code=mre_code, expected_behavior=expected_behavior, actual_behavior=actual_behavior,
                evidence_chain=evidence, doc_reference_url=doc_reference_url or None,
                verification_status=VerificationStatus.PENDING, milvus_version=ctx.deps.core.target_version,
            )
            ctx.deps.core.issues.append(issue)
            runtime.session.test_state.issues.append(issue)

            ctx.deps.context.add_execution_log(f"Recorded defect: [{sev.value}] {title}")
            runtime.hook_runner.run_post_defect_hooks("record_defect", {"title": title, "defect_id": defect_id})

            telemetry_sink.log_event(TelemetryEvent(
                trace_id=ctx.deps.core.run_id, node_name="record_defect",
                event_type="DEFECT_RECORDED", state_delta={"defect_id": defect_id, "severity": sev.value, "title": title},
            ))

            runtime.event_emitter.emit(TestEvent(
                event_type=TestEventType.DEFECT_DISCOVERED,
                session_id=runtime.session.session_id,
                round_id=f"R{ctx.deps.core.current_round:03d}",
                data={"defect_id": defect_id, "severity": sev.value, "title": title, "defect_type": defect_type},
            ))

            runtime.event_emitter.emit(TestEvent(
                event_type=TestEventType.TOOL_COMPLETED,
                session_id=runtime.session.session_id,
                round_id=f"R{ctx.deps.core.current_round:03d}",
                data={"tool": "record_defect", "success": True},
            ))

            return json.dumps({"success": True, "defect_id": defect_id, "issue_id": issue_id, "evidence_completeness": evidence.completeness_score()})

        @agent.tool
        async def generate_feedback(ctx: RunContext[WorkflowState]) -> str:
            defects = ctx.deps.core.defects
            weak_points = list(set(d.defect_type.value for d in defects))
            tested_ops = [tc["tool"] for tc in ctx.deps.context.tool_call_history]
            all_ops = ["db_create_collection", "db_insert_data", "db_search", "db_query", "db_delete_data", "db_upsert_data", "db_flush", "db_load_collection", "db_release_collection"]
            coverage_gaps = [op for op in all_ops if op not in tested_ops]

            mutation_strategies = []
            if weak_points:
                mutation_strategies.append(f"Focus on: {', '.join(weak_points)}")
            if coverage_gaps:
                mutation_strategies.append(f"Test untested operations: {', '.join(coverage_gaps)}")
            mutation_strategies.extend(["Test boundary parameter values", "Test concurrent operations", "Verify index rebuild behavior"])

            feedback = FuzzingFeedback(
                weak_points=weak_points, mutation_strategies=mutation_strategies,
                coverage_gaps=coverage_gaps, round_number=ctx.deps.core.current_round,
            )
            ctx.deps.core.feedback = feedback
            ctx.deps.context.feedback_history.append(feedback)
            runtime.session.test_state.feedback = feedback
            return feedback.to_prompt_text()

    async def run_test_round(self, user_input: str) -> TestRoundSummary:
        start_time = time.time()
        ts = self.session.test_state
        round_id = f"R{ts.current_round:03d}"

        summary = TestRoundSummary(round_id=round_id, stage=ts.current_stage.value)

        if self._agent is None:
            self._agent = self._create_agent()

        if self._workflow_state is None:
            self._workflow_state = WorkflowState()

        ws = self._workflow_state
        ws.core.run_id = ts.run_id or self.session.session_id
        ws.core.current_stage = ts.current_stage
        ws.core.current_round = ts.current_round
        ws.core.max_rounds = ts.max_rounds
        ws.core.target_version = ts.target_version
        ws.core.scenario = ts.scenario
        ws.core.token_usage = ts.token_usage
        ws.core.contracts = ts.contracts
        ws.core.defects = ts.defects
        ws.core.issues = ts.issues
        ws.core.feedback = ts.feedback

        defects_before = len(ts.defects)

        self.recovery_engine.set_round(ts.current_round)

        self.event_emitter.emit(TestEvent(
            event_type=TestEventType.ROUND_STARTED,
            session_id=self.session.session_id,
            round_id=round_id,
            data={"round": ts.current_round, "stage": ts.current_stage.value},
        ))

        try:
            result = await self._agent.run(
                user_prompt=user_input,
                deps=ws,
            )

            usage = result.usage()
            input_tokens = getattr(usage, 'input_tokens', getattr(usage, 'request_tokens', 0))
            output_tokens = getattr(usage, 'output_tokens', getattr(usage, 'response_tokens', 0))
            self.usage_tracker.add(input_tokens, output_tokens)
            ts.token_usage += input_tokens + output_tokens
            ts.consecutive_failures = 0

            ts.current_stage = ws.core.current_stage
            ts.contracts = ws.core.contracts
            ts.feedback = ws.core.feedback
            ts.defects = ws.core.defects
            ts.issues = ws.core.issues
            ts.coverage_score = ws.core.coverage_score
            ts.consecutive_failures = ws.core.consecutive_failures
            ts.should_terminate = ws.core.should_terminate

            summary.token_usage = input_tokens + output_tokens
            summary.defects_found = len(ts.defects) - defects_before
            summary.success = True

            output_text = result.output[:500] if len(result.output) > 500 else result.output
            console.print(Panel(output_text, title="Agent Response", border_style="green"))

            telemetry_sink.log_event(TelemetryEvent(
                trace_id=ts.run_id or self.session.session_id,
                node_name=f"round_{ts.current_round}_{ts.current_stage.value}",
                event_type="END", token_usage=input_tokens + output_tokens,
            ))

        except Exception as e:
            ts.consecutive_failures += 1
            summary.success = False
            summary.error = str(e)
            console.print(f"[red]Agent error:[/red] {e}")
            logger.error(f"Agent run failed: {e}", exc_info=True)

            recovery_result = self.recovery_engine.attempt_recovery(e, {"round": ts.current_round, "stage": ts.current_stage.value})
            if recovery_result.action_taken:
                console.print(f"[yellow]Recovery attempted: {recovery_result.action_taken}[/yellow]")
            if recovery_result.escalated and recovery_result.escalation_reason == "max_retries_exceeded":
                self.recovery_engine.reset_attempts()

            telemetry_sink.log_event(TelemetryEvent(
                trace_id=ts.run_id or self.session.session_id,
                node_name=f"round_{ts.current_round}_{ts.current_stage.value}",
                event_type="ERROR", state_delta={"error": str(e)[:200], "recovery": recovery_result.action_taken},
            ))

        if ts.current_stage == Stage.REPORTING:
            ts.advance_stage()
            self._stage_iterations = 0
        elif ts.consecutive_failures >= ts.max_consecutive_failures:
            console.print(f"[red]Too many consecutive failures ({ts.consecutive_failures}), advancing stage[/red]")
            ts.advance_stage()
            self._stage_iterations = 0

        self._stage_iterations += 1
        if self._stage_iterations > self._max_test_iterations:
            logger.warning(f"Stage {ts.current_stage.value} exceeded max iterations ({self._max_test_iterations}), forcing advance")
            ts.advance_stage()
            self._stage_iterations = 0

        if self.compactor.should_compact(self.session):
            compaction_result = self.compactor.compact(self.session)
            console.print(f"[yellow]Context compacted: removed {compaction_result.removed_message_count} messages, tokens {compaction_result.estimated_tokens_before} -> {compaction_result.estimated_tokens_after}[/yellow]")
            telemetry_sink.log_event(TelemetryEvent(
                trace_id=ts.run_id or self.session.session_id,
                node_name="compaction",
                event_type="COMPACTION_APPLIED",
                state_delta={"removed": compaction_result.removed_message_count, "tokens_before": compaction_result.estimated_tokens_before, "tokens_after": compaction_result.estimated_tokens_after},
            ))

        summary.duration_ms = (time.time() - start_time) * 1000

        self.event_emitter.emit(TestEvent(
            event_type=TestEventType.ROUND_COMPLETED,
            session_id=self.session.session_id,
            round_id=round_id,
            data={"round": ts.current_round, "stage": ts.current_stage.value, "success": summary.success, "defects_found": summary.defects_found, "duration_ms": summary.duration_ms},
        ))

        return summary

    async def run(
        self,
        target_version: str = "2.6.12",
        scenario: str = "",
        max_rounds: Optional[int] = None,
        session_dir: Optional[str] = None,
    ) -> TestSession:
        ts = self.session.test_state
        ts.run_id = self.session.session_id
        ts.target_version = target_version
        ts.scenario = scenario
        ts.max_rounds = max_rounds or self.config.harness.max_rounds
        self._defect_counter = 0
        self._stage_iterations = 0

        if not self.config.llm.api_key:
            self.display.print_error("DeepSeek API key not configured. Set DEEPSEEK_API_KEY env var or add to config.yaml")
            return self.session

        session_path = None
        if session_dir:
            sp = Path(session_dir)
            sp.mkdir(parents=True, exist_ok=True)
            session_path = sp / f"{self.session.session_id}.jsonl"

        self.display.set_session_info(self.session.session_id, ts.max_rounds)
        self.display.print_banner(target_version, self.config.llm.pro_model)

        self.input_handler.start()

        health = await asyncio.get_running_loop().run_in_executor(None, self.db_operator.health_check)
        self.display.print_milvus_status(
            connected=health.success,
            info=str(health.data) if health.success else str(health.error),
        )

        paused = False
        user_focus = ""

        while not ts.should_stop():
            for user_input in self.input_handler.get_all_pending():
                if user_input.command == UserCommand.PAUSE:
                    paused = True
                    self.display.set_paused(paused)
                    self.display.print_paused()
                elif user_input.command == UserCommand.RESUME:
                    paused = False
                    self.display.set_paused(paused)
                    self.display.print_resumed()
                elif user_input.command == UserCommand.STOP:
                    self.display.print_info("User requested stop")
                    ts.should_terminate = True
                    break
                elif user_input.command == UserCommand.SKIP:
                    ts.advance_stage()
                    self._stage_iterations = 0
                    self.display.print_info(f"Skipped to stage: {ts.current_stage.value}")
                elif user_input.command == UserCommand.FOCUS:
                    user_focus = user_input.argument
                    self.display.print_user_instruction(f"Focus on: {user_focus}")
                elif user_input.command == UserCommand.STATUS:
                    console.print(f"  [cyan]{self.display.build_status_line()}[/cyan]")

            if ts.should_terminate:
                break

            if paused:
                await asyncio.sleep(0.5)
                continue

            prompt = self._build_stage_prompt()
            if user_focus:
                prompt += f"\n\nUser instruction: Focus on {user_focus}"
                user_focus = ""

            round_summary = await self.run_test_round(prompt)

            if session_path:
                self.session.save_round(session_path, {
                    "messages": self.session.messages,
                    "test_state": ts.model_dump(mode="json"),
                })
                self.event_emitter.emit(TestEvent(
                    event_type=TestEventType.SESSION_SAVED,
                    session_id=self.session.session_id,
                    round_id=f"R{ts.current_round:03d}",
                    data={"path": str(session_path)},
                ))

        self.input_handler.stop()
        self._print_summary()

        return self.session

    def _print_summary(self) -> None:
        ts = self.session.test_state
        self.display.print_summary(
            session_id=self.session.session_id,
            rounds=ts.current_round,
            contracts=len(ts.contracts.all_rules()),
            defects=len(ts.defects),
            issues=len(ts.issues),
            tokens=ts.token_usage,
            input_tokens=self.usage_tracker.total_input_tokens,
            output_tokens=self.usage_tracker.total_output_tokens,
        )
