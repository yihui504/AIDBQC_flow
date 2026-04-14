# 最终推荐提交的 Issue 列表

## 去重检查结果

| 数据库 | 搜索关键词 | 已有 Issue | 结论 |
|--------|-----------|-----------|------|
| Qdrant | dimension bypass | 0 | ✅ 无重复 |
| Qdrant | filter strict | 17 (不相关) | ✅ 无重复 |
| Qdrant | hybrid fusion | 4 (RRF相关，非bypass) | ✅ 无重复 |
| Milvus | dimension negative | 1 (feature request) | ✅ 无重复 |
| Weaviate | filter strictness | 0 | ✅ 无重复 |
| Weaviate | payload overflow | 0 | ✅ 无重复 |

---

## 推荐提交的 Issue（按优先级排序）

### 🔴 P0 - 最高优先级（Type-1 Illegal Success，17分）

这些是 **L1 门控绕过** 类型的 bug，系统接受了非法参数并返回成功，是最严重的问题。

#### Qdrant (13个)

| # | Case ID | 评分 | 文件路径 |
|---|---------|------|----------|
| 1 | CHAOS_SEQ_PRE_INSERT_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_CHAOS_SEQ_PRE_INSERT_001.md` |
| 2 | IBSA_COUNT_MISMATCH_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_COUNT_MISMATCH_001.md` |
| 3 | IBSA_FILTER_STRICT_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_FILTER_STRICT_001.md` |
| 4 | IBSA_FILTER_STRICT_002 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_FILTER_STRICT_002.md` |
| 5 | IBSA_HYBRID_FUSION_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_HYBRID_FUSION_001.md` |
| 6 | IBSA_HYBRID_RERANK_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_HYBRID_RERANK_001.md` |
| 7 | IBSA_IDEMPOTENCY_001_MUTATED | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_IDEMPOTENCY_001_MUTATED.md` |
| 8 | IBSA_METRIC_RANGE_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_METRIC_RANGE_001.md` |
| 9 | IBSA_RESULT_COUNT_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_RESULT_COUNT_001.md` |
| 10 | IBSA_SEMANTIC_DRIFT_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_SEMANTIC_DRIFT_001.md` |
| 11 | IBSA_SPARSE_BM25_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_IBSA_SPARSE_BM25_001.md` |
| 12 | NEG_TYPE1_BYPASS_DIM_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_NEG_TYPE1_BYPASS_DIM_001.md` |
| 13 | NEG_TYPE_001 | 17 | `.trae/runs/run_7f4a7e9d/GitHub_Issue_NEG_TYPE_001.md` |

**目标仓库**: https://github.com/qdrant/qdrant/issues

---

### 🟠 P1 - 高优先级（Type-1/Type-3，15分）

#### Milvus (6个 Type-1)

| # | Case ID | 评分 | 文件路径 |
|---|---------|------|----------|
| 14 | TC_003_INVALID_DIM_NEGATIVE | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_003_INVALID_DIM_NEGATIVE.md` |
| 15 | TC_006_CHAOTIC_SEQ_SEARCH_BEFORE_CREATE | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_006_CHAOTIC_SEQ_SEARCH_BEFORE_CREATE.md` |
| 16 | TC_103_DIM_OVERFLOW | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_103_DIM_OVERFLOW.md` |
| 17 | TC_105_DIM_ZERO | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_105_DIM_ZERO.md` |
| 18 | TC_L1_DIM_NEGATIVE_BYPASS | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_L1_DIM_NEGATIVE_BYPASS.md` |
| 19 | TC_L2_HNSW_INVALID_PARAM_M | 15 | `.trae/runs/run_5af0cc02/GitHub_Issue_TC_L2_HNSW_INVALID_PARAM_M.md` |

**目标仓库**: https://github.com/milvus-io/milvus/issues

#### Milvus (13个 Type-3 IBSA)

| # | Case ID | 评分 | 文件路径 |
|---|---------|------|----------|
| 20 | IBSA_COSINE_BOUNDARY | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_COSINE_BOUNDARY.md` |
| 21 | IBSA_COUNT_MISMATCH_EDGE | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_COUNT_MISMATCH_EDGE.md` |
| 22 | IBSA_COUNT_MISMATCH_TOP_K | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_COUNT_MISMATCH_TOP_K.md` |
| 23 | IBSA_FILTER_STRICTNESS_PRICE | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_FILTER_STRICTNESS_PRICE.md` |
| 24 | IBSA_IDEMPOTENCY_CHECK | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_IDEMPOTENCY_CHECK.md` |
| 25 | IBSA_IDEMPOTENCY_CONSISTENCY_CHECK | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_IDEMPOTENCY_CONSISTENCY_CHECK.md` |
| 26 | IBSA_IDEMPOTENCY_IDENTICAL_QUERY | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_IDEMPOTENCY_IDENTICAL_QUERY.md` |
| 27 | IBSA_IP_METRIC_NEGATIVE_DISTANCE | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_IP_METRIC_NEGATIVE_DISTANCE.md` |
| 28 | IBSA_IP_RANGE_NEGATIVE | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_IP_RANGE_NEGATIVE.md` |
| 29 | IBSA_METRIC_BOUNDARY_COSINE_MAX | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_METRIC_BOUNDARY_COSINE_MAX.md` |
| 30 | IBSA_METRIC_RANGE_COSINE_OVERFLOW | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_IBSA_METRIC_RANGE_COSINE_OVERFLOW.md` |
| 31 | L1_MAX_TOP_K_BOUNDARY | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_L1_MAX_TOP_K_BOUNDARY.md` |
| 32 | L2_CHAOTIC_SEARCH_BEFORE_CREATE | 15 | `.trae/runs/run_ea82f2ed/GitHub_Issue_L2_CHAOTIC_SEARCH_BEFORE_CREATE.md` |

#### Weaviate (2个)

| # | Case ID | 评分 | 文件路径 |
|---|---------|------|----------|
| 33 | tc_ibsa_filter_strictness | 15 | `.trae/runs/run_0609fc30/GitHub_Issue_tc_ibsa_filter_strictness.md` |
| 34 | tc_type1_payload_overflow | 15 | `.trae/runs/run_0609fc30/GitHub_Issue_tc_type1_payload_overflow.md` |

**目标仓库**: https://github.com/weaviate/weaviate/issues

---

## 提交建议

### 首批提交（最推荐）

建议优先提交以下 5 个最高价值的 issue：

1. **Qdrant: NEG_TYPE1_BYPASS_DIM_001** — 维度绕过，最严重
2. **Qdrant: IBSA_FILTER_STRICT_001** — 过滤器严格性问题
3. **Milvus: TC_103_DIM_OVERFLOW** — 维度溢出
4. **Milvus: TC_105_DIM_ZERO** — 零维度绕过
5. **Weaviate: tc_type1_payload_overflow** — Payload 溢出

### 注意事项

1. 提交前请检查目标仓库的 Issue 模板要求
2. 建议附上完整的 MRE 代码和环境信息
3. 如果 issue 被标记为 duplicate，请检查是否有相似 issue
4. Type-1 issue 通常会被优先处理，因为涉及安全/正确性问题
