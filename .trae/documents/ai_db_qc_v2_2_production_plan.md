# AI-DB-QC v2.2: 生产级重构与 Mock 剔除计划

## 0. 背景说明

在确认了系统是面向**真实生产场景**而非仅仅为了演示后，我们需要对现有的流水线进行一次彻底的“清道夫”行动。
通过全局扫描代码库（Grep 关键字 `mock`, `TODO`, `skip` 等），我们发现了多处“走捷径”的伪实现。v2.2 的核心目标是**剔除所有假数据、硬编码和绕过逻辑，实现真正的生产级智能体流水线**。

***

## 1. 核心痛点与遗留 Mock 分析

通过全局扫描，我们定位到以下几个致命的“伪实现”：

1. **Agent 0 的假文档 (Fake Documentation)**:

   * *文件*: `src/agents/agent0_env_recon.py:171`

   * *现状*: `docs_context = f"Mocked documentation for {db_info.db_name}..."`

   * *危害*: 这是整个流水线的源头。没有真实的官方文档，Agent 1 提取的 Contract 也是大模型瞎编的，导致整个测试失去了对特定版本的针对性。

2. **Agent 1 的薄弱契约 (Weak Contracts)**:

   * *文件*: `src/agents/agent1_contract_analyst.py:17`

   * *现状*: L1/L2 契约只定义了极其简单的字段（如 `expected_monotonicity: bool`），并且没有转化为可执行的断言代码。

   * *危害*: 无法拦截真实的脏数据，导致测试用例直接打到底层，引发无意义的报错。

3. **Agent 3 的 L1 门控绕过 (L1 Gating Bypass)**:

   * *文件*: `src/agents/agent3_executor.py:81`

   * *现状*: `l1_passed = True # Mocking L1 pass for now to ensure flow`

   * *危害*: 门控形同虚设，Agent 3 根本没有去校验 Agent 2 生成的用例是否符合 L1 契约。

4. **Token 计费的硬编码 (Hardcoded Token Tracking)**:
   - *文件*: `agent0, agent1, agent2, agent4, agent6`
   - *现状*: `state.total_tokens_used += 100 # Mocking token usage`
   - *危害*: 无法准确触发 v2.0 中设计的 Circuit Breaker (熔断机制)，在生产中可能导致 API 费用失控。

5. **缺少重试与兜底逻辑 (Missing Fallbacks & Retries)**:
   - *文件*: `src/agents/agent0_env_recon.py` (文档爬取) 和所有 LLM 结构化输出。
   - *现状*: 很多地方遇到异常直接 `pass` 或粗暴抛出。
   - *危害*: 在无人值守的生产环境，一次偶然的网络抖动就会导致整个工作流崩溃。

6. **配置的硬编码 (Hardcoded Configurations)**:
   - *文件*: `src/adapters/db_adapter.py:53`
   - *现状*: 写死了 `self.port = "19530"`。
   - *危害*: 丧失了跨环境部署的灵活性。

---

## 2. v2.2 改进方向与架构升级

### 2.1 真实的 RAG 文档检索 (Agent 0)

* **抛弃 Mock**：引入 `LangChain WebBaseLoader` 或 GitHub API，当用户输入 `Milvus v2.4` 时，动态抓取对应 Tag 下的 `limits.md` 和 `parameters.md`。

* **知识对齐**：通过真实文档构建上下文，确保大模型生成的变异策略是基于当前版本的真实约束。

### 2.2 生产级可执行契约 (Agent 1 & Agent 3)

* **强化 L1 契约**：除了维度，补充 `max_collection_name_length`、`supported_index_types`、`max_payload_size`。

* **可执行化门控**：在 Agent 3 中，不再写死 `l1_passed = True`。必须编写真实的 Python 校验逻辑（或动态生成的 JSON Schema validator）去硬性拦截非法用例。

### 2.3 真实的 Token 监控与回调

* **LangChain Callback**：利用 `get_openai_callback()` 或 Anthropic 的 Usage metadata，真实捕获每次 LLM 调用的 `prompt_tokens` 和 `completion_tokens`，彻底移除 `+= 100` 这种硬编码。

***

## 3. WBS 任务拆解 (v2.2 生产级重构)

### 阶段一：文档真实化与契约加固 (Week 1)

* [x] **WBS 1.1: Agent 0 真实爬虫集成**：集成 Tavily 或 WebLoader，实现对指定版本数据库官方文档的真实抓取与清洗。

* [x] **WBS 1.2: Agent 1 契约模型扩充**：重构 `L1Contract` 和 `L2Contract` 的 Pydantic 模型，增加生产级字段。

* [x] **WBS 1.3: Agent 3 L1 门控实装**：移除 `l1_passed = True`，编写真实的断言逻辑对比 TestCase 和 L1Contract。

### 阶段二：基建去伪存真 (Week 2)

* [x] **WBS 2.1: 真实 Token 计费器**：在所有调用 `chain.invoke()` 的地方，挂载 `get_openai_callback` (或自定义 Anthropic 计费拦截器)。

* [x] **WBS 2.2: 移除所有遗留 Mock 代码**：清理 `_mock_embed` 的后路逻辑，强制失败等。

* [x] **WBS 2.3: 生产级兜底机制**：处理当 TAVILY\_API\_KEY 缺失时，不再是 "Skipping actual search"，而是直接抛出生产级告警并终止非必要的增强分支。

