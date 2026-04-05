# Tasks

- [ ] 任务 1：重构生成器 (Agent 2) 为“攻击模式”
  - [ ] 子任务 1.1：在 `TestCase` 模型中增加 `is_negative_test: bool` 字段。
  - [ ] 子任务 1.2：重构 Agent 2 提示词，引入“违约攻击”指令（故意违反 L1 限制）。
  - [ ] 子任务 1.3：实现“时序破坏”逻辑：生成包含 `drop_collection` 后紧跟 `search` 的非法序列。
- [ ] 任务 2：执行器 (Agent 3) 透传与压力升级
  - [ ] 子任务 2.1：修改 `_execute_single_case`，移除 L1 拦截逻辑，允许 `is_negative_test` 用例通过。
  - [ ] 子任务 2.2：实现“压力注入”接口：支持生成万级维度的填充向量（Zero Padding 攻击）。
  - [ ] 子任务 2.3：增加执行层日志，详细记录非法请求下数据库返回的原始 `ErrorCode` 和 `Reason`。
- [ ] 任务 3：诊断器 (Agent 5) 四型全量判定重构
  - [ ] 子任务 3.1：重写 Agent 5 逻辑：若 `expected_l1_legal == False` 且 `success == True` -> 判定为 **Type-1**。
  - [ ] 子任务 3.2：实现错误深度审计：若 `success == False` 且报错信息模糊 -> 判定为 **Type-2**。
  - [ ] 子任务 3.3：集成 `DockerLogsProbe`：在 Type-3 判定时自动回溯 C++ 底层堆栈信息。
- [ ] 任务 4：引入重排序节点 (Reranker Node)
  - [ ] 子任务 4.1：创建 `src/agents/agent_reranker.py`，使用 `cross-encoder/ms-marco-MiniLM-L-6-v2`。
  - [ ] 子任务 4.2：在 `src/graph.py` 中将 Reranker 插入在 Executor 和 Oracle 之间。
- [ ] 任务 5：全量攻击性实战回归
  - [ ] 子任务 5.1：运行 12 轮压测，验证是否成功挖掘出 Type-1 或 Type-2 Bug。
  - [ ] 子任务 5.2：核查评估报告，确认 Type-4 的假阳性是否因 Reranker 而显著下降。

# Task Dependencies
- [任务 3] 依赖于 [任务 1] 和 [任务 2] 提供的攻击数据流。
- [任务 4] 旨在优化 [任务 3] 发现的语义误判。
