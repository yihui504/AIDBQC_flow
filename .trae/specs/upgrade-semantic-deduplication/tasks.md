# Tasks

- [x] 任务 1：统一缺陷报告数据模型
  - [x] 子任务 1.1：确保 `src/state.py` 中的 `DefectReport` 模型包含 `bug_type`, `root_cause_analysis`, `case_id` 等必要字段。
  - [x] 子任务 1.2：重构 `src/defects/enhanced_deduplicator.py` 中的 `DefectReport` 类，使其能直接从 `src/state.py` 的模型转换或复用。
- [x] 任务 2：实现基于向量的语义计算
  - [x] 子任务 2.1：在 `DefectSimilarityCalculator` 中集成 `sentence-transformers` (如 `all-MiniLM-L6-v2`) 进行文本编码。
  - [x] 子任务 2.2：使用余弦相似度（Cosine Similarity）替换原有的 Jaccard 相似度。
- [x] 任务 3：多维相似度加权调优
  - [x] 子任务 3.1：配置各个维度的权重（推荐：语义 0.5, 错误代码/消息 0.3, 操作 0.1, Bug 类型 0.1）。
  - [x] 子任务 3.2：实现 `shared_features` 和 `differentiating_features` 的自动提取。
- [x] 任务 4：集成到 Agent 6 (Verifier)
  - [x] 子任务 4.1：在 `Agent 6` 初始化时实例化 `EnhancedDefectDeduplicator`。
  - [x] 子任务 4.2：将 `_deduplicate` 方法重构为异步调用 `deduplicator.deduplicate()`。
  - [x] 子任务 4.3：记录并展示去重统计信息（如：总数 vs 去重后数）。

# Task Dependencies
- [任务 2] 依赖于 [任务 1] 的数据结构支持。
- [任务 4] 依赖于 [任务 3] 的相似度计算能力。
