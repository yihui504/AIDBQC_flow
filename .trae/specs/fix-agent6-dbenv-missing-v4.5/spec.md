# Fix Agent6 db_env Missing Variable Spec

## Why
三库实战验收（run_b96069a5 / run_050949c7 / run_89fff289）全部失败于 Agent6 Issue 生成阶段。Weaviate 运行暴露了明确的错误信息：
```
Input to ChatPromptTemplate is missing variables {'db_env'}.
Expected: ['db_env', 'env_context', 'report', 'target_doc', 'validated_refs']
Received: ['report', 'target_doc', 'env_context', 'validated_refs']
```
根因：Agent6 的 `self.prompt` 模板中使用了 `{db_env}` 占位符（用于生成 GitHub Issue 的 Environment 段），但 `_generate_issue_for_defect()` 调用 `self.prompt.partial()` 时未传入该变量。`_get_db_template_fragments()` 返回的字典包含 `env_lines` 字段（内容正是 db_env 需要的数据），但键名不匹配。

## What Changes
- **修复 `_generate_issue_for_defect()` 中的变量传递缺失**：在 `self.prompt.partial()` 调用中补全 `db_env` 变量
- 方案选择：在 `_get_db_template_fragments()` 返回字典中增加 `db_env` 键（值为 `env_lines` 的内容），使 `**self._current_db_fragments` 展开时自动包含它。这是最小改动方案，不影响已有逻辑。

## Impact
- Affected code: `src/agents/agent6_verifier.py` 的 `_generate_issue_for_defect()` 方法（第 ~1073 行）和 `_get_db_template_fragments()` 方法（第 ~350 行）
- Affected capability: Agent6 GitHub Issue 生成全链路
- 不影响其他 Agent 或模块

## ADDED Requirements
### Requirement: db_env Variable Completion
系统 SHALL 在 Agent6 的 prompt 模板填充阶段提供 `db_env` 变量值。

#### Scenario: Successful Issue Generation
- **WHEN** Agent6 对任意缺陷调用 `_generate_issue_for_defect()`
- **THEN** `self.prompt.partial()` 收到完整的变量集合（含 `db_env`），LLM 正常返回 GitHubIssue 结构化输出
- **AND** 生成的 Issue markdown 中 `### Environment` 段包含正确的数据库版本和 SDK 信息

## MODIFIED Requirements
### Requirement: _get_db_template_fragments Return Value
`_get_db_template_fragments(db_name)` 方法返回的字典 SHALL 包含 `db_env` 键，其值为数据库特定的环境描述文本（如 `- **Milvus version**: {{db_version}}\n- **SDK/Client**: pymilvus`）。当前该方法已返回等价内容的 `env_lines` 键，新增 `db_env` 键与之同值。
