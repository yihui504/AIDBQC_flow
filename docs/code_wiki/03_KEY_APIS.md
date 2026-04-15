# 关键类型与函数说明

本页聚焦“读代码时最先应该看哪些类型/函数”，以便快速建立心智模型。

## 状态与数据模型（src/state.py）

### WorkflowState

定义： [WorkflowState](file:///workspace/src/state.py#L122-L178)

用于 LangGraph 节点之间传递的全局状态，包含：

- 输入：`target_db_input`、`business_scenario`
- 上下文：`db_config`、`contracts`
- 运行数据：`current_test_cases`、`execution_results`、`oracle_results`
- 产物：`defect_reports`、`verified_defects`、`fuzzing_feedback`
- 预算与控制：`iteration_count`、`max_iterations`、`total_tokens_used`、`max_token_budget`、`should_terminate`
- L2 门控信号：`current_collection`、`data_inserted`

### TestCase

定义： [TestCase](file:///workspace/src/state.py#L31-L44)

字段要点：

- `case_id`：用例唯一 ID（会进入 defect/issue）
- `dimension`：目标向量维度（强影响 L1/L2 与 adapter 行为）
- `query_vector` / `query_text`：query 可由文本转 embedding（Agent3）
- `expected_l1_legal` / `expected_l2_ready`：用于 oracle/分类
- `is_adversarial` / `is_negative_test`：驱动分类与报告措辞

### ExecutionResult

定义： [ExecutionResult](file:///workspace/src/state.py#L45-L58)

- `l1_passed` / `l2_passed`：双层门控结果
- `error_message`：失败原因（issue 的核心证据之一）
- `underlying_logs`：从 Docker 抓取的深度日志（用于强证据）
- `l1_violation_details`：结构化 L1 违规信息（便于去重与报告）

### DefectReport

定义： [DefectReport](file:///workspace/src/state.py#L97-L121)

- 分类：`bug_type`（Type-1..4）、`evidence_level`
- 报告增强字段：`title`、`operation`、`error_message`、`database`、`l1_violation_details`
- 验证与去重：`is_verified`、`verification_status`、`verifier_verdict`、`reproduced_bug`

## 工作流编排（src/graph.py）

### build_workflow()

定义： [build_workflow](file:///workspace/src/graph.py#L40-L103)

作用：把“多 agent 的业务流程”变成 LangGraph StateGraph，并定义：

- 线性链路：agent0 → agent1 → agent2 → agent3 → rerank → agent4 → agent5 → coverage
- 条件边：
  - agent3：连续失败则 recovery，否则继续
  - coverage：fuzzing loop 继续或进入 verify

### should_continue_fuzzing()

定义： [should_continue_fuzzing](file:///workspace/src/graph.py#L21-L30)

作用：token budget 熔断与终止信号聚合，决定走 `fuzz` 或 `verify`。

## Runner（main.py）

### _enforce_real_run_configuration()

定义： [_enforce_real_run_configuration](file:///workspace/main.py#L76-L119)

作用：在 run_guard.enabled=true 时强制约束运行参数（目标 DB 版本、max_iterations、禁止“模拟/降级”标记）。

### main()

定义： [main](file:///workspace/main.py#L155)

作用：配置加载 → 初始化全局组件（错误处理/端口管理）→ 创建 WorkflowState → 执行 LangGraph 并写回状态。

## Agent3：执行与门控（src/agents/agent3_executor.py）

### ExecutionGatingAgent._l1_gating()

定义： [_l1_gating](file:///workspace/src/agents/agent3_executor.py#L88-L194)

要点：

- dimension 校验支持双模式：
  - `dimension_constraint`（list/range，结构化来自契约）
  - fallback：`allowed_dimensions`（旧式 list）
- 对非法 dimension/top_k：
  - 默认硬阻断（l1_hard_block_illegal_params=true）
  - 可配置为“warning pass-through”以捕获 Type-1（非法成功）类缺陷

### ExecutionGatingAgent._l2_gating()

定义： [_l2_gating](file:///workspace/src/agents/agent3_executor.py#L195-L230)

要点：

- 必须存在 `state.current_collection`
- 必须有 `state.data_inserted=true`
- 失败将被分类为 Type-2.PF 或被误写为语义类问题（issue 筛选时要特别警惕）

## Adapter 接口（src/adapters/db_adapter.py）

### VectorDBAdapter（抽象接口）

定义： [VectorDBAdapter](file:///workspace/src/adapters/db_adapter.py#L7-L45)

统一了三类数据库的关键动作：

- `connect` / `disconnect`
- `setup_harness` / `teardown_harness`
- `initialize_collection` / `insert_data`
- `search_async`

### MilvusAdapter（示例实现）

定义： [MilvusAdapter](file:///workspace/src/adapters/db_adapter.py#L46)

要点：

- `_lazy_init()`：运行时导入 pymilvus，避免未安装时报错影响整体 import
- collection pooling：以 dimension 为 key 复用 collection（降低重复创建成本）

## Agent6：验证与 Issue 生成（src/agents/agent6_verifier.py）

### IsolatedCodeRunner.execute_code()

定义： [execute_code](file:///workspace/src/agents/agent6_verifier.py#L90-L203)

要点：

- 默认隔离执行（Docker），并禁用 network
- `isolated_mre.enabled=false` 或 Docker 不可用会 fail-closed（拒绝执行）

### EnhancedDefectDeduplicator

定义： [EnhancedDefectDeduplicator](file:///workspace/src/defects/enhanced_deduplicator.py)（类较大，建议从 DefectSimilarityCalculator 开始读）

要点：

- 多维相似度（semantic/structural/behavioral/contextual）用于聚类与去重
- 默认离线安全：仅在显式开启 AI_DB_QC_ENABLE_EMBEDDINGS 时尝试加载嵌入模型（见 [enhanced_deduplicator.py:L218-L232](file:///workspace/src/defects/enhanced_deduplicator.py#L218-L232)）

