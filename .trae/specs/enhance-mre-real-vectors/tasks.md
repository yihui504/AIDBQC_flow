# 增强 MRE 真实语义向量 - 任务列表

## [x] Task 1：实现 `_inject_real_vectors()` 方法
- **优先级**：P0
- **依赖**：None
- **状态**：✅ 已完成（2026-04-04）
- **子任务**：
  - [x] 1.1：在 `agent6_verifier.py` 中新增 `_inject_real_vectors(self, mre_code, defect)` 方法（L505-L609）
  - [x] 1.2：实现占位符模式检测（uniform fill / random / 手写简单列表 3 种）
  - [x] 1.3：从 defect.operation 提取查询文本作为 embedding 输入
  - [x] 1.4：调用 EmbeddingGenerator.generate_search_vector_code() 获取真实向量代码并替换
  - [x] 1.5：Fallback 路径正常（模型未加载/无匹配时不崩溃）

## [x] Task 2：集成到 execute() 流程中
- **优先级**：P0
- **依赖**：Task 1 ✅
- **状态**：✅ 已完成
- **子任务**：
  - [x] 2.1：在 execute() 第952行，_extract_mre_code() 之后调用 _inject_real_vectors()
  - [x] 2.2：注入后的 MRE 更新回 defect.mre_code

## [x] Task 3：重新生成 12 个 Issue 并验证
- **优先级**：P0
- **依赖**：Task 2 ✅
- **状态**：✅ 已完成（2026-04-04）
- **子任务**：
  - [x] 3.1：执行 _regenerate_issues.py
  - [x] 3.2：验证 12/12 成功生成
  - [x] 3.3：检查 MRE 真实向量注入率（实际 2/12 = 16.7%，TC_002=384维, TC_102=2维）

## [x] Task 4：更新评估报告
- **优先级**：P1
- **依赖**：Task 3 ✅
- **状态**：✅ 已完成（2026-04-04）
- **子任务**：
  - [x] 4.1：EVALUATION_REPORT.md 追加第十一章（MRE 真实向量增强）
  - [x] 4.2：评分从 3.47 更新至 3.57，MRE 真实向量 0→1.5/5
