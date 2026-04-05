# Upgrade Semantic Deduplication Spec

## Why
目前的缺陷去重逻辑过于简单（仅基于 `root_cause_analysis` 的前 50 个字符），这在长时间运行的压测中会导致生成大量重复的 GitHub Issue。为了提高缺陷报告的质量，我们需要升级为基于多维语义相似度的智能去重方案。

## What Changes
- **集成 `EnhancedDefectDeduplicator`**：将 `src/defects/enhanced_deduplicator.py` 中的多维相似度计算集成到 `Agent 6 (Verifier)` 中。
- **引入语义向量化**：使用 `sentence-transformers` 对缺陷描述和根本原因分析进行向量化，实现真正的语义相似度对比。
- **多维权重调优**：结合 `bug_type`、`operation`、`error_message` 和 `semantic` 四个维度进行加权评分。
- **结构化缺陷模型同步**：统一 `src/state.py` 和 `src/defects/enhanced_deduplicator.py` 中的缺陷数据结构。

## Impact
- Affected specs: `adversarial-fuzzing-v3.5` (后续运行将使用新去重逻辑)
- Affected code:
    - [agent6_verifier.py](file:///c:/Users/11428/Desktop/ralph/src/agents/agent6_verifier.py)
    - [enhanced_deduplicator.py](file:///c:/Users/11428/Desktop/ralph/src/defects/enhanced_deduplicator.py)
    - [state.py](file:///c:/Users/11428/Desktop/ralph/src/state.py)

## ADDED Requirements
### Requirement: 智能语义去重
系统应能识别语义相近但文字表达略有不同的缺陷报告。

#### Scenario: 语义相似缺陷合并
- **WHEN** 两个缺陷的根本原因分析（Root Cause Analysis）在语义上高度重合（相似度 > 0.8）
- **THEN** 系统应将其识别为重复项，仅保留其中一个作为代表性缺陷。

## MODIFIED Requirements
### Requirement: Agent 6 去重逻辑
- **OLD**: `rc_norm = d.root_cause_analysis.lower()[:50]`
- **NEW**: 调用 `EnhancedDefectDeduplicator.deduplicate()` 方法，基于多维相似度矩阵进行聚类去重。

## REMOVED Requirements
### Requirement: 字符截断去重
**Reason**: 误杀率高，且无法识别稍微改动后的重复缺陷。
**Migration**: 切换到向量空间模型。
