# Tasks

## P0 Tasks (Critical - Must Fix)

- [x] Task 1: **Agent5 IBSA 分类修正** — 修复 `classify_defect_v2()` 中 IBSA 用例被错误归类为 Type-2 的问题
  - 在 classify_defect_v2() 入口处检测 case_id 是否含 `ibsa_` 前缀
  - 对 IBSA 用例：检查 execution_result 是否无 SDK 异常（非 ParamError/MilvusException 等）
  - 若 IBSA 用例执行完成且无 SDK 异常 → 跳过 Type-2 分支，强制进入 Oracle 违规判定（Type-3/Type-4）
  - 验证：Milvus 的 8 个 IBSA 缺陷在重新分类后不再为 Type-2

- [x] Task 2: **Agent6 Issue MRE 完整性** — 确保生成的 GitHub Issue 包含完整可复现代码
  - 检查 `_generate_issue_for_defect()` 返回的 GitHubIssue 对象 body_markdown 字段
  - 若 body 过短（< 200 字符），增加后处理逻辑或强化 prompt 指引
  - 确保 LLM 输出的 issue 包含完整的 Steps To Reproduce + Python MRE 代码块
  - 验证：生成的 .md 文件 > 50 行且包含 ```python 代码块

- [x] Task 3: **误报过滤** — 在 pipeline 或 Agent6 execute 中过滤 `false_positive=True` 缺陷
  - 在 Agent6.execute() 返回前，或 graph.py 收集 issues 时增加过滤逻辑
  - 条件：`verdict == "expected_rejection" and false_positive == True` → 不写入 github_issues 列表
  - 但保留在 state.json 中（标记 filtered=True）供分析追踪
  - 验证：Weaviate 的 10 个 expected_rejection 缺陷不出现在最终 Issue 列表中

## P1 Tasks (Important - Should Fix)

- [x] Task 4: **l1_violation_details 传播** — 将 ExecutionResult 的 L1 违约详情传递到 DefectReport
  - 在 Agent5 创建 DefectReport 时，从对应的 execution_result 中读取 l1_violation_details 并复制到 defect_report
  - 在 DefectReport 数据类中确认该字段存在（若不存在则添加）
  - 验证：三库缺陷报告中 l1_violation_details 非空率 > 80%

- [x] Task 5: **Agent6 pending 处理改进** — 解决 Milvus/Qdrant 全部 pending 问题
  - 分析 pending 根因：是超时？LLM 返回格式错误？还是验证步骤被跳过？
  - 增加对 pending 状态缺陷的降级处理（至少输出基础 Issue 而非完全跳过）
  - 增加 per-defect timeout 和重试逻辑
  - 验证：Milvus/Qdrant 的 pending 率从 100% 降至 < 30%

- [x] Task 6: **Milvus Type-2 主导根因分析** — 调试为何 Milvus 全部为 Type-2
  - 对比 Milvus vs Qdrant/Weaviate 的 execution_result.error 格式差异
  - 检查 Agent5 决策树中 Milvus 特定分支是否将所有错误归为 Poor Diagnostics
  - 如发现分支逻辑问题则修复
  - 验证：Milvus 缺陷类型分布中出现 Type-1 或 Type-3

# Task Dependencies
- Task 1 (IBSA fix) 应最先执行 — 它可能同时解决 Task 6 (Milvus Type-2 问题)
- Task 2 (Issue quality) 和 Task 3 (FP filter) 可并行
- Task 4 (propagation) 可与 Task 1 同时做（同一文件 agent5）
- Task 5 (pending) 和 Task 6 (Milvus debug) 依赖前面的修复结果来验证
