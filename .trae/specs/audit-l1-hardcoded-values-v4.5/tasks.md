# Tasks

- [x] Task 1: 修复 C1 — severity 阈值动态化 (agent3_executor.py:104,121)
  - 将两处 `"hard" if (dimension < 4 or dimension > 32768)` 改为从 dc_obj 动态获取 min/max
  - range 模式：hard 阈值 = dc_obj.min / dc_obj.max；list 模式：任何越界均为 hard
- [x] Task 2: 修复 C2 — 容器名动态解析 (agent3_executor.py:261-262)
  - 删除 container_map 硬编码字典，内联动态解析逻辑（与 Agent5 的 _resolve_container_name 一致）
- [x] Task 3: 修复 C3 — Milvus 硬限制动态化 (agent3_executor.py:358)
  - 将 `> 32768` 改为从 contract 的 dimension_constraint.max 获取
- [x] Task 4: 修正 I1-I3 — 三库 supported_metrics 文档验证与修正 (contract_fallbacks.py)
  - Milvus: 移除 BM25（全文搜索非向量度量），添加 TANIMOTO（二进制向量）
  - Qdrant/Weaviate: 值不变，新增文档来源注释
- [x] Task 5: 修正 I4-I5 — 三库 max_top_k 文档验证与修正 (contract_fallbacks.py)
  - 三库值均保持不变（无严格文档限制），新增注释说明来源
- [x] Task 6: 集成验证 — py_compile + 断言测试 (13/13 PASS)

# Task Dependencies
- Task 1, 2, 3 均修改 agent3_executor.py 不同位置 → 已顺序完成
- Task 4, 5 均修改 contract_fallbacks.py → 已并行完成
- Task 6 依赖所有前置任务 → 已通过
