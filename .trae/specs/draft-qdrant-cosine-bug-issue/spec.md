# Qdrant Cosine Similarity Score Upper Bound Bug Spec

## Why
在对所有的现有 Issue 进行了自动化和手动交叉排查后，我们发现绝大部分由系统生成的 Issue 是伪阳性（如 Weaviate 查询不存在的集合、Milvus max top_k 和 Filter 逻辑，都在最新版本表现正常）。
然而，我们成功且 100% 稳定地复现了 Qdrant 中的一个严重数学契约破坏（Traditional Oracle Violation）：当使用 `Cosine` 距离进行完全一致的向量匹配时，Qdrant API 会返回 `1.0000001` 等超过 `1.0` 理论上限的分数。由于官方文档明确标明 Cosine score 的范围是 `[-1, 1]`，这可能导致下游业务逻辑在严格校验分界时崩溃，是非常值得向官方提交的真实 Bug。

## What Changes
- 草拟并生成符合 Qdrant 官方标准的 GitHub Bug 报告。
- 提取我们在排查时使用的 MRE (Minimal Reproducible Example) 脚本。
- 将 Bug 报告以 Markdown 格式保存到 `issues/qdrant/Qdrant_Bug_Report_Cosine_UpperBound.md` 中。

## Impact
- Affected specs: 无（仅新增文档）。
- Affected code: 新增 `issues/qdrant/Qdrant_Bug_Report_Cosine_UpperBound.md`。

## ADDED Requirements
### Requirement: Qdrant Official Bug Report
The system SHALL provide a highly structured Markdown file representing a Qdrant GitHub issue, containing precise version info, OS, SDK, reproducible Python code, expected/actual behavior, and documentation references.

#### Scenario: Success case
- **WHEN** the issue report is generated
- **THEN** users can directly copy and paste it into the Qdrant GitHub repository issues section.