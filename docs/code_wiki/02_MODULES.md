# 主要模块职责

## 入口与编排

### Runner（main.py）

- 配置加载与运行约束：[_enforce_real_run_configuration](file:///workspace/main.py#L76-L119)
- 安全防护：禁止“降级/模拟”路径（state_update 关键字段扫描），见 [_enforce_no_degraded_runtime_paths](file:///workspace/main.py#L121-L151)
- 执行模型：`app.stream(initial_state.model_dump(), config=...)`，逐节点消费 LangGraph 输出并回写到 `WorkflowState`，见 [main.py:L272-L318](file:///workspace/main.py#L272-L318)
- 异常处置：MRE 生成、根因分析、标准化报告、关键错误快速停机，见 [main.py:L319-L406](file:///workspace/main.py#L319-L406)

### 工作流编排（src/graph.py）

- 工作流定义：StateGraph + 节点注册 + 边/条件边（fuzzing loop / circuit breaker / verification），见 [build_workflow](file:///workspace/src/graph.py#L40-L103)
- 关键路由：
  - agent3_executor 后：按连续失败进入 recovery，见 [check_circuit_breaker](file:///workspace/src/graph.py#L32-L37)
  - coverage_monitor 后：按 token budget/terminate 信号决定继续 fuzz 还是进入 verify，见 [should_continue_fuzzing](file:///workspace/src/graph.py#L21-L30)

## 状态与数据模型（src/state.py）

- Pydantic 数据模型（流水线的“schema contract”）：
  - 用例：[TestCase](file:///workspace/src/state.py#L31-L44)
  - 执行结果：[ExecutionResult](file:///workspace/src/state.py#L45-L58)
  - 缺陷报告：[DefectReport](file:///workspace/src/state.py#L97-L121)
  - 全局状态：[WorkflowState](file:///workspace/src/state.py#L122-L178)
- 向量压缩/规范化：CompressionUtils（用于状态体积优化与回放），见 [CompressionUtils](file:///workspace/src/state.py#L179)

## Agent 层（src/agents/）

### Agent0：环境侦察与文档预处理

- 目标：拉起/探测数据库环境、抓取并缓存官方文档，为契约分析提供上下文。
- 入口文件：[agent0_env_recon.py](file:///workspace/src/agents/agent0_env_recon.py)

### Agent1：契约分析（L1/L2/L3）

- 目标：从文档与业务场景提炼 L1 API 约束、L2 语义/状态约束、L3 应用级契约。
- 入口文件：[agent1_contract_analyst.py](file:///workspace/src/agents/agent1_contract_analyst.py)

### Agent2：测试生成（含对抗/负向）

- 目标：根据契约与反馈生成新一轮 test cases，支持多轮迭代与变异。
- 入口文件：[agent2_test_generator.py](file:///workspace/src/agents/agent2_test_generator.py)

### Agent3：执行与双层门控（L1/L2）

- L1（抽象合法性）：dimension/metric/top_k 等契约校验，支持 hard block 或 warning pass-through，见 [_l1_gating](file:///workspace/src/agents/agent3_executor.py#L88-L194)
- L2（运行就绪性）：collection/data 是否 ready，见 [_l2_gating](file:///workspace/src/agents/agent3_executor.py#L195-L230)
- 执行：通过 DB Adapter 调用数据库（异步 search），并在失败时抓取 Docker 深度日志作为证据（见 [agent3_executor.py](file:///workspace/src/agents/agent3_executor.py) 后续实现）

### Reranker：结果重排

- 目标：在 oracle 之前对候选结果做语义重排（cross-encoder/降级策略）。
- 入口文件：[agent_reranker.py](file:///workspace/src/agents/agent_reranker.py)

### Agent4：预言机（传统 + 语义）

- 目标：对执行结果做分层校验（单调性、一致性、语义相关性等），输出 oracle_results。
- 入口文件：[agent4_oracle.py](file:///workspace/src/agents/agent4_oracle.py)

### Agent5：诊断与分类

- 目标：将执行/预言机异常归类为 Type-1..4，并产出 fuzzing_feedback 驱动下一轮生成。
- 入口文件：[agent5_diagnoser.py](file:///workspace/src/agents/agent5_diagnoser.py)

### Agent6：可复现验证 + 去重 + Issue 生成

- 目标：对缺陷进行语义/结构去重、抽取 MRE、隔离环境执行验证，并输出 GitHub Issue Markdown。
- 入口文件：[agent6_verifier.py](file:///workspace/src/agents/agent6_verifier.py)
- 安全策略：隔离执行禁用 host fallback（fail-closed），见 [agent6_verifier.py:L108-L115](file:///workspace/src/agents/agent6_verifier.py#L108-L115)

### Reflection / Recovery / WebSearch（辅助节点）

- Reflection：收敛总结与产物输出，见 [agent_reflection.py](file:///workspace/src/agents/agent_reflection.py)
- Recovery：连续失败时的恢复路径，见 [agent_recovery.py](file:///workspace/src/agents/agent_recovery.py)
- Web Search：补充外部知识驱动下一轮生成，见 [agent_web_search.py](file:///workspace/src/agents/agent_web_search.py)

## 适配层（src/adapters/db_adapter.py）

- 抽象接口：[VectorDBAdapter](file:///workspace/src/adapters/db_adapter.py#L7-L45)
- 具体实现：
  - Milvus：[MilvusAdapter](file:///workspace/src/adapters/db_adapter.py#L46)
  - Qdrant / Weaviate：同文件内（用于统一 connect / setup_harness / search_async 等调用形态）

## 去重、可观测性与安全防护

### 缺陷去重（src/defects/enhanced_deduplicator.py）

- 多维相似度：语义/结构/行为/上下文四维评分，见 [DefectSimilarityCalculator](file:///workspace/src/defects/enhanced_deduplicator.py#L198)
- 设计目标：减少“相同根因、不同表述”的重复 issue，提高提交命中率。

### Telemetry & 性能监控

- Telemetry：节点级事件日志（jsonl），用于复盘 token、状态变更与耗时，见 [telemetry.py](file:///workspace/src/telemetry.py)
- 性能：内存/CPU 采样与快照，见 [performance.py](file:///workspace/src/performance.py)

### Critical Error Handler / Port Manager

- 关键错误分类与快速停机：[critical_error_handler.py](file:///workspace/src/critical_error_handler.py)
- Docker 端口分配与孤儿清理：[docker_port_manager.py](file:///workspace/src/docker_port_manager.py)

## Dashboard（src/dashboard/）

- Streamlit 应用入口：[app.py](file:///workspace/src/dashboard/app.py)
- 目标：展示运行状态、产物、路径与关键指标（具体交互以代码为准）。

