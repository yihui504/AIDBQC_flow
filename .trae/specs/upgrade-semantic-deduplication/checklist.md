# Checklist

- [x] 缺陷报告模型统一：`src/state.py` 和 `src/defects/enhanced_deduplicator.py` 的数据模型已对齐或具有映射关系。
- [x] 向量化语义对比：`EnhancedDefectDeduplicator` 能够加载 `sentence-transformers` 编码文本，并计算余弦相似度。
- [x] 多维加权评分：各个维度的相似度得分（语义、结构、上下文）已根据配置权重正确汇总。
- [x] 聚类去重有效性：对包含语义相近但文字表达不同的缺陷进行去重，且仅保留一个代表性缺陷。
- [x] Agent 6 集成：`agent6_verifier.py` 中的 `_deduplicate` 逻辑已重构为调用增强型去重器，且代码可正常运行。
- [x] 验证输出：GitHub Issue 生成前，已执行去重，防止生成重复报告。
