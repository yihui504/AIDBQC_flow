# AI-DB-QC 智能测试台重构规范 (v3.4)

## Why
在 v3.3 的审计中发现，当前的测试流水线在验证精确度、文档覆盖度及数据纯净度上仍存在缺陷：
1. **验证网关漏洞**：MRE 验证无法区分“代码本身错误”与“真实业务 Bug”，导致虚假复现。
2. **爬虫策略僵化**：严苛的 URL 过滤导致在官方文档无法获取时，整个证据链条断裂。
3. **语料库噪声**：Mock 数据中混入了强干扰性的业务背景文本，污染了向量搜索的语义空间。

本重构旨在通过精细化异常拦截、放宽爬虫回退机制以及清洗语料库，将 Issue 的真实有效性提升至工业级水平。

## What Changes
- **精细化 MRE 验证 (Agent 6)**：重构 `_verify_mre` 逻辑，增加对 `SyntaxError`、`IndentationError` 等代码质量错误的拦截。只有当代码运行逻辑正确但结果违背契约时，才允许标记为 `SUCCESS`。
- **自适应爬虫回退 (Agent 0)**：修改 `_fetch_documentation` 逻辑。若官方域名过滤后结果为空，自动放宽过滤条件，尝试抓取 GitHub Wiki 或高权重技术社区（如 StackOverflow、Medium）的相关内容。
- **语料库去噪 (Data Generator)**：修改 `ControlledDataGenerator`，移除所有硬编码的“We are building...”等项目背景文本，确保生成的 Mock 数据语义纯净。

## Impact
- Affected specs: `upgrade-harness-v3.3`, `project-audit-v3.3`.
- Affected code: `src/agents/agent6_verifier.py`, `src/agents/agent0_env_recon.py`, `src/data_generator.py`.

## ADDED Requirements
### Requirement: MRE 代码质量校验
验证逻辑 SHALL 区分执行失败的类型。
- 如果是语法错误（IndentationError, SyntaxError），状态设为 `INVALID_CODE`。
- 如果是逻辑报错且与预期 Bug 一致，状态设为 `SUCCESS`。

### Requirement: 爬虫二级回退
当一级官方源（Official Docs）失效时，系统 SHALL 自动激活二级源（Community/Wiki）进行补全。

## MODIFIED Requirements
### Requirement: 纯净语料生成
数据生成器 SHALL 仅生成与业务领域（如 e-commerce）直接相关的实体数据，严禁注入框架背景描述。

## REMOVED Requirements
无。
