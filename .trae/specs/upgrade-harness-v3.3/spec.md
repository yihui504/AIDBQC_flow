# AI-DB-QC 智能测试台升级规范 (v3.3)

## 为什么
在 v3.2 的审计中发现，当前的测试流水线存在严重的“认知断裂”：
1. **数据与意图脱节**：Agent 2 生成的查询意图与数据库中的 Mock 数据无关，导致 Oracle 产生大量假阳性。
2. **证据链质量下降**：由于降级使用 `httpx`，爬取内容经常遭遇 403 拦截或缺失关键 JS 渲染内容。
3. **Issue 不可复现**：生成的 MRE 代码缺乏自动化校验，存在大量无法复现的“幻觉 Bug”。

本升级旨在通过恢复 `Crawl4AI`、实现“意图-数据”闭环生成以及 MRE 自动验证，彻底解决这些问题。

## 变更内容
- **恢复 Crawl4AI (Agent 0)**：重新引入 `Crawl4AI` 进行深度爬取，但强制使用 `Chromium` 内核并开启 `headless` 模式，以消除与用户 Firefox 的冲突。增加 `magic_mode` 绕过 403 拦截。
- **意图-数据闭环生成 (Agent 2 & 3)**：
    - 修改 `TestCase` 模型，增加 `expected_ground_truth` 字段。
    - Agent 2 生成用例时，必须同步生成“预期应在库中存在的商品数据”。
    - Agent 3 在执行搜索前，精准注入这些 Ground Truth 数据。
- **MRE 自动化验证 (Agent 6)**：
    - Agent 6 生成 Issue 后，自动提取 MRE 代码并尝试在独立子进程中运行。
    - 仅当 MRE 真实复现了预期的异常或错误状态时，才允许导出 Issue 报告。
- **契约系统强化**：Agent 1 增加对 `state_constraints` 的深度解析逻辑。

## 影响
- Affected specs: `enhance-documentation-pipeline`, `project-audit-v3.2`.
- Affected code: `src/state.py`, `src/agents/agent0_env_recon.py`, `src/agents/agent2_test_generator.py`, `src/agents/agent3_executor.py`, `src/agents/agent6_verifier.py`.

## ADDED Requirements
### Requirement: 意图-数据协同生成
Agent 2 SHALL 产出包含具体数据样本的测试用例，这些样本必须能支撑查询意图。

#### Scenario: 闭环验证成功
- **WHEN** Agent 2 生成“查询高保真耳机”
- **THEN** `expected_ground_truth` 必须包含至少 2 条“高保真耳机”的商品记录
- **AND** Agent 3 注入该数据后，如果搜索失败，Oracle 判定为真实 Bug。

### Requirement: MRE 自动化自校验
Agent 6 SHALL 在 Issue 落盘前运行 MRE。

#### Scenario: 幻觉 Bug 拦截
- **WHEN** Agent 6 生成了一个无法运行或运行结果正常的 MRE
- **THEN** 系统 SHALL 自动作废该 Issue 并记录“验证失败”日志。

## MODIFIED Requirements
### Requirement: 浏览器爬取隔离
Agent 0 SHALL 恢复使用 `Crawl4AI`，但必须配置为 `browser_type="chromium"` 且 `headless=True`。

## REMOVED Requirements
### Requirement: 纯 HTTP 爬取 (降级方案)
**Reason**: 数据质量不足，无法支撑高质量 Issue。
**Migration**: 迁移回 `Crawl4AI` 强化版。
