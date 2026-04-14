# Post-Verification Optimization Assessment & Design Spec

## Why
三库实战验收（run_e8cb71af / run_67572d8e / run_0609fc30）已完成，Type-1 检测从 0% 突破到 Qdrant 15%/Weaviate 74%。但深度分析揭示了 **5 个关键质量问题**，如不修复将导致：
1. 缺陷分类准确率低（Weaviate 74% Type-1 中 37% 为误报）
2. GitHub Issue 质量差（无 MRE 代码，仅 11 行模板头）
3. Milvus IBSA 用例全部降级为 Type-2（应产生 Type-3/4）
4. Agent6 验证流程不完整（Milvus/Qdrant 全部 pending）
5. `l1_violation_details` 字段未向 DefectReport 传播

## Deep Analysis Findings

### Finding F1: Weaviate Type-1 存在大量误报（CRITICAL）

| Verdict | 数量 | 占比 | 含义 |
|---------|------|------|------|
| `expected_rejection` + fp=True | **10** | **37%** | DB 正确拒绝了非法输入，**不是 bug** |
| `invalid_report` | **14** | 52% | Agent6 无法验证（报告格式问题） |
| `reproduced_bug` + verified=True | **3** | **11%** | **真正的 Type-1 bug** |

**真实 Type-1 检出率 = 11%**，而非表面上的 74%。

### Finding F2: Milvus IBSA 用例全部分类错误（HIGH）

Milvus 的 8 个 IBSA 用例（idempotency, cosine boundary, count mismatch, L2 negative dist, IP range violation, filter strictness, empty result garbage, hybrid RRF）**全部被归类为 Type-2 (Poor Diagnostics)**。

按设计，IBSA 用例应在 L1/L2 合法的情况下触发 Oracle 违规 → 应为 Type-3 或 Type-4。Agent5 决策树对 Milvus 存在特殊路径问题。

### Finding F3: GitHub Issue 质量严重不足（HIGH）

| 数据库 | .md 文件数 | 平均行数 | 有 Environment | 有 MRE 代码 | 有 Steps |
|--------|-----------|----------|---------------|-------------|----------|
| Milvus | 14 | ~11 行 | ✅ | ❌ | ❌ |
| Qdrant | 4 | ~11 行 | ✅ | ❌ | ❌ |
| Weaviate | 3 | ~12 行 | ✅ | ❌ | ❌ |

所有 Issue 文件仅有标题和 Environment 头部，**缺少 MRE 可复现代码和复现步骤**。这意味着生成的 Issue 无法直接用于开发者复现 bug。

### Finding F4: Agent6 验证不完整（MEDIUM）

| 数据库 | pending | invalid_report | expected_rejection | reproduced_bug |
|--------|---------|----------------|-------------------|----------------|
| Milvus | **14 (100%)** | 0 | 0 | 0 |
| Qdrant | **13 (100%)** | 0 | 0 | 0 |
| Weaviate | 0 | 14 (52%) | 10 (37%) | 3 (11%) |

Milvus 和 Qdrant 的全部缺陷验证状态为 `pending` — Agent6 可能因超时或错误未完成验证步骤就返回了。

### Finding F5: l1_violation_details 未传播（MEDIUM）

三库共 54 个缺陷中 **0 个包含 `l1_violation_details`**。该字段在 P1-a 阶段已添加到 ExecutionResult，但未被 Agent5 或 pipeline 传递到 DefectReport 中，导致下游 Agent6 无法利用 severity 信息做更精细的判断。

## Optimization Opportunity Matrix

| # | 方向 | 影响 | 复杂度 | ROI | 推荐 |
|---|------|------|--------|-----|------|
| O1 | **Agent5 决策树修正：IBSA→Type-3/4 分类路径** | 高 | 中 | ⭐⭐⭐⭐ | **P0** |
| O2 | **Agent6 Issue 质量：MRE 代码注入完整性** | 高 | 中 | ⭐⭐⭐⭐ | **P0** |
| O3 | **Type-1 误报过滤：expected_rejection 剔除** | 高 | 低 | ⭐⭐⭐⭐⭐ | **P0** |
| O4 | **l1_violation_details 向 DefectReport 传播** | 中 | 低 | ⭐⭐⭐ | **P1** |
| O5 | **Agent6 验证超时/pending 处理改进** | 中 | 中 | ⭐⭐⭐ | **P1** |
| O6 | **Milvus 特殊决策树分支调试** | 中 | 中 | ⭐⭐⭐ | **P1** |

## What Changes

### Change O1: Agent5 Decision Tree - IBSA Classification Fix
**File**: `src/agents/agent5_diagnoser.py`
- 在 `classify_defect_v2()` 中增加 IBSA 用例识别逻辑
- 当 case_id 包含 `ibsa_` 前缀且 execution_result 无 SDK 异常时 → 强制走 Type-3/Type-4 判定路径
- 不再让 IBSA 用例落入 "Poor Diagnostics" 分支

### Change O2: Agent6 Issue Quality - Full MRE Injection  
**File**: `src/agents/agent6_verifier.py`
- 当前 `_generate_issue_for_defect()` 生成的 Issue 仅含模板头部
- 需要确保 LLM 输出的 GitHubIssue 对象的 body_markdown 包含完整的 MRE Python 代码
- 可能需要增加 prompt 中的 MRE 代码生成指引，或增加后处理步骤补全长 Issue

### Change O3: False Positive Filtering in Pipeline
**File**: `src/agents/agent6_verifier.py` (execute method) 或 `graph.py`
- 在 defect_reports → github_issues 转换阶段增加过滤
- 将 `verifier_verdict == "expected_rejection" AND false_positive == True` 的缺陷从最终 Issue 列表中移除
- 但保留在 state.json 中（标记为 filtered）以供分析

### Change O4: l1_violation_details Propagation
**Files**: `src/agents/agent5_diagnoser.py`, possibly `graph.py`
- 确保 Agent5 读取 execution_result.l1_violation_details 并写入 defect_report
- Agent6 在验证时可利用此信息判断 severity

### Change O5: Agent6 Pending/Timeout Handling
**File**: `src/agents/agent6_verifier.py`
- 对 pending 状态的缺陷增加重试或降级逻辑
- 设置合理的 per-defect timeout（当前可能一个缺陷超时导致全部 pending）

### Change O6: Milvus-Specific Debug
- 分析为何 Milvus 所有缺陷都归为 Type-2
- 可能原因：Milvus execution_result 的 error 信息格式与 Qdrant/Weaviate 不同，导致 Agent5 决策树走了不同分支

## Impact
- Affected code:
  - `src/agents/agent5_diagnoser.py` (O1, O4, O6)
  - `src/agents/agent6_verifier.py` (O2, O3, O5)
  - Possibly `src/graph.py` or main orchestration (O3)
- Affected capability: Defect classification accuracy, Issue quality, False positive rate
- Estimated effort: P0 items = 1-2 days; P1 items = 1 day

## ADDED Requirements

### Requirement: IBSA-Aware Defect Classification
系统 SHALL 根据测试用例的 case_id 前缀（`ibsa_`）和执行结果特征，将边界内语义异常用例正确分类为 Type-3 或 Type-4，而非 Type-2。

#### Scenario: IBSA Case Correctly Classified
- **WHEN** 一个 case_id 以 `ibsa_` 开头的用例在合法参数下执行完成
- **THEN** 其缺陷类型应为 Type-3（Traditional Oracle Violation）或 Type-4（Semantic Violation），绝不为 Type-2

### Requirement: Complete GitHub Issue with MRE
系统 SHALL 为每个确认的缺陷生成包含完整可复现 MRE 代码的 GitHub Issue，Issue markdown 文件长度应 > 50 行（含完整代码块）。

#### Scenario: Issue Contains Reproducible Code
- **WHEN** Agent6 生成 GitHub Issue
- **THEN** Issue body 包含 `### Steps To Reproduce` 段落，内含完整 Python 代码块（使用对应 DB 的 SDK）

### Requirement: False Positive Filtering
系统 SHALL 在最终输出前过滤掉被 Agent6 标记为 `false_positive=True` 且 `verdict=expected_rejection` 的缺陷，使其不出现在最终 GitHub Issue 列表中。

## MODIFIED Requirements

### Requirement: Defect Report Completeness
DefectReport 数据结构 SHALL 包含从 ExecutionResult 传播过来的 `l1_violation_details` 字段，使下游 Agent 能获取 L1 违约违规的详细信息。
