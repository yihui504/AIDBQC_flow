# Verify Documentation References Spec

## Why
在之前的实战运行中发现，Agent 6 生成的 GitHub Issue 中存在文档引用幻觉（虚构了不存在的 URL 和引用内容）。虽然已经实施了修复（引入了 PRE-VALIDATED 引用机制），但需要通过一次中等规模的实战运行来验证修复效果，确保生成的每一个引用都真实可靠。

## What Changes
- **运行实战测试**：执行 5 轮迭代的模糊测试。
- **重点审查 Evidence 环节**：验证 Agent 6 是否严格遵守了“仅使用经过验证的引用”这一约束。
- **配置调整**：暂时将 `main.py` 中的 `max_iterations` 调整为 5 轮。

## Impact
- Affected specs: `upgrade-semantic-deduplication` (进一步验证去重与验证器的协同)
- Affected code:
    - [agent6_verifier.py](file:///c:/Users/11428/Desktop/ralph/src/agents/agent6_verifier.py)
    - [main.py](file:///c:/Users/11428/Desktop/ralph/main.py)

## ADDED Requirements
### Requirement: 引用真实性校验
系统生成的 GitHub Issue 中，`Official Docs Reference` 必须来源于 `raw_docs.json` 中的真实文本，且 `Reference URL` 必须是抓取到的真实地址。

#### Scenario: 修复验证
- **WHEN** 流水线发现缺陷并生成 Issue
- **THEN** Issue 中的引用部分应显示 PRE-VALIDATED 传递的内容，若无相关文档则明确标注。

## MODIFIED Requirements
### Requirement: 迭代上限
- **OLD**: 8 轮
- **NEW**: 5 轮 (仅限本次验证任务)
