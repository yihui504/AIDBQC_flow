# Issue 筛选建议（用于对外提交）

本仓库已生成的 Issue Markdown 位于 [issues/](file:///workspace/issues)。这些文件的价值不完全一致：一部分是“真实数据库行为异常”，另一部分更像是“环境未就绪/门控导致的误报”或“基于 harness 假设的契约不一定是官方约束”。

本页给出：

- 筛选标准（可复用）
- 最建议优先提交的候选（基于当前 issues/ 目录的快速质量审阅）
- 不建议提交/需重写的常见模式

## 筛选标准（建议你按此复核后再提交）

优先级从高到低：

1) **可复现且自洽**
- MRE 能直接运行（imports 完整，端口/URL 与 compose 一致）
- 有明确的断言或可观察的差异输出（如 `assert` / 计数/范围检查）

2) **引用“官方契约”，而非仅引用 harness 生成的 vector_config**
- issue 里出现的上限/枚举/范围，最好能在官方文档/API schema 中找到明确条款

3) **Actual Behavior 有具体证据**
- 返回值片段、错误码、日志、距离/score 的具体数值，而不是笼统的 “oracle violation”

4) **避免环境/门控误报**
- issue 中出现 `L2 Gating Failed: Database not ready or disconnected`、`No active collection` 等，通常意味着并未触达数据库真实逻辑，优先排除

## 最建议优先提交的候选（Top）

这些候选的共同点是：MRE 相对完整、问题描述与数学/逻辑预言机一致、且不依赖“harness 自定义 max_top_k 等约束”。

### Milvus

- [GitHub_Issue_IBSA_METRIC_RANGE_COSINE_OVERFLOW.md](file:///workspace/issues/milvus/GitHub_Issue_IBSA_METRIC_RANGE_COSINE_OVERFLOW.md)
  - 主题：COSINE 度量下，“插入向量与查询向量完全相同”时返回距离异常（文档上 COSINE 语义清晰，且用 `assert` 定义了可验收标准）
  - 提交前复核要点：
    - 确认 Milvus 对 COSINE 返回的是 distance 还是 similarity（不同实现可能用不同方向的 score）
    - 在复现日志中粘贴实际 `dist` 数值与版本号（不要只写“> 1.0”）

### Qdrant

- [GitHub_Issue_tc_bypass_topk.md](file:///workspace/issues/qdrant/GitHub_Issue_tc_bypass_topk.md)
  - 主题：search 返回结果数量大于请求 `limit`（如果可复现，这是硬性 bug）
  - 提交前复核要点：
    - 复现时把 `Requested limit` 与 `Actual results returned` 的真实输出贴进 issue
    - 确认不是客户端侧重复追加/分页逻辑导致（建议最小化代码：只 create → upsert → search → len）

## 建议暂缓提交（或需要重写后再提交）的模式

以下模式在当前 issues/ 中出现频率较高，建议不要原样提交到上游仓库：

1) **L2 门控/环境错误伪装成数据库 bug**
- 典型特征：Actual Behavior 包含 `L2 Gating Failed: Database not ready or disconnected`
- 例子：[GitHub_Issue_L1_DIMENSION_UNDERFLOW_ILLEGAL.md](file:///workspace/issues/milvus/GitHub_Issue_L1_DIMENSION_UNDERFLOW_ILLEGAL.md)

2) **缺少关键 imports/符号导致 MRE 无法运行**
- 典型特征：代码片段里使用 `wvc.*` 但没有 `import weaviate.classes as wvc` 或其它必要导入
- 例子：[GitHub_Issue_TC_BOUND_001.md](file:///workspace/issues/weaviate/GitHub_Issue_TC_BOUND_001.md)

3) **把“harness 合同假设”当成“官方约束”**
- 典型特征：声称存在 `max_top_k=10000` 等上限，但引用的官方文档并未给出该硬上限
- 例子：[GitHub_Issue_tc_l1_bypass_002.md](file:///workspace/issues/qdrant/GitHub_Issue_tc_l1_bypass_002.md)

4) **误解度量语义（尤其是 IP/Cosine 的 score 方向）**
- 例如将 IP 的负值当作“距离不应为负”的 bug，通常会上游判定为“预期行为/文档解释问题”
- 例子：[GitHub_Issue_IBSA_IP_METRIC_NEGATIVE_DISTANCE.md](file:///workspace/issues/milvus/GitHub_Issue_IBSA_IP_METRIC_NEGATIVE_DISTANCE.md)

## 对外提交前的最小检查清单

- 运行 compose 拉起目标数据库并记录版本号（包含 build hash 更好）
- 运行 MRE 并把 stdout/stderr 的关键行粘贴进 issue
- 如果是“范围/边界类 bug”，给出明确的数学解释或官方文档引用
- 如果上游存在相似 issue：用链接标注差异点（避免被 close as duplicate）

