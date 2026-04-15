# 组会首次报告 HTML（基于 Code Wiki）Spec

## Why
现有 `docs/code_wiki/` 已覆盖仓库架构与关键机制，但直接以 Markdown 形式用于组会汇报不利于“投屏讲述 + 节奏控制”。需要生成一个离线可用的 HTML 报告页，把 Wiki 内容重组为更适合口头报告的叙事主线，并保留 Wiki 作为可折叠附录以支持 Q&A。

## What Changes
- 新增组会报告页：`/workspace/group_meeting_report.html`（单页长文 + 侧边目录）
- 新增本地静态资源目录：`/workspace/assets/group_meeting_report/`（离线可用，无外部 CDN）
- 报告页内容以 `docs/code_wiki/*.md` 为主要素材来源，并在不改变事实含义的前提下重组为“痛点→方案→验证”的讲述主线
- 报告页复用既有介绍页（project-overview-html 相关产物）的视觉语言与交互组件（如目录、折叠、卡片样式），但不要求与其内容一致

## Impact
- Affected specs: 文档/演示物料生成（不改动核心业务逻辑）
- Affected code: 无核心代码改动；新增/调整的仅为 HTML 与静态资源（以及可选的生成脚本）

## ADDED Requirements

### Requirement: 交付物与离线可用
系统 SHALL 产出一个可直接打开的报告页 `group_meeting_report.html`，并在无网络环境下完整渲染。

#### Scenario: 离线打开
- **WHEN** 断网后在浏览器中打开 `group_meeting_report.html`
- **THEN** 页面样式与交互正常、图示与代码高亮正常、无任何外部网络请求

### Requirement: 页面结构（单页长文 + 目录）
页面 SHALL 采用单页长滚动结构，并提供固定侧边目录（锚点跳转）。

#### Scenario: 快速定位章节
- **WHEN** 用户点击侧边目录任一项
- **THEN** 页面滚动到对应章节，并在滚动过程中高亮当前章节

### Requirement: 讲述主线（痛点→方案→验证）
页面内容 SHALL 以“痛点→方案→验证”的叙事组织，章节顺序至少包含：
- 痛点（向量数据库测试难点、现有方法不足）
- 方案（架构总览、核心机制：三层契约、L1/L2 门控、预言机、去重与验证）
- 验证（cross-db 运行与产物、Issue 筛选方法、每库 1 个代表性案例）

#### Scenario: 组会讲述节奏
- **WHEN** 报告人按目录自上而下讲述
- **THEN** 每章都有明确的“本章要回答的问题”和“本章结论/Takeaways”

### Requirement: 讲稿提示（Speaker Notes）
页面 SHALL 为每个一级章节提供讲稿提示，格式为 3-5 条要点。

#### Scenario: 现场照读要点
- **WHEN** 报告人展开章节
- **THEN** 能在章节顶部看到精炼要点列表以辅助讲述

### Requirement: 交互能力（折叠 + 演示大字号）
页面 SHALL 支持：
- 细节默认折叠（例如代码片段、附录内容、长表格）
- “演示大字号”切换（提高字号、行距、留白，适配投屏）

#### Scenario: 投屏可读性
- **WHEN** 开启“演示大字号”
- **THEN** 关键段落、要点列表、标题在投屏距离下可读性显著提升

### Requirement: 图示范围（增强讲解）
页面 SHALL 在保留核心架构图的基础上，额外提供 1-2 张“讲解增强图”，用于解释关键概念之间关系（例如：L1/L2 门控与缺陷类型的对应关系）。

#### Scenario: 概念解释
- **WHEN** 报告人讲到 L1/L2 门控与缺陷分类
- **THEN** 页面提供直观图示帮助听众建立映射关系

### Requirement: 代码片段范围（必看片段）
页面 SHALL 重点展示以下 4 类代码片段（默认折叠，支持语法高亮）：
- 工作流编排：`src/graph.py`（build_workflow 与关键路由）
- 全局状态模型：`src/state.py`（WorkflowState 与关键数据结构）
- L1/L2 门控：`src/agents/agent3_executor.py`（_l1_gating / _l2_gating）
- 验证与去重：`src/agents/agent6_verifier.py`（隔离执行策略与去重相关片段）

#### Scenario: 代码引用展示
- **WHEN** 用户展开任一代码片段
- **THEN** 看到高亮后的代码块与对应“文件路径 + 行号范围”的文本引用（不做可点击链接）

### Requirement: 附录（保留原始 Code Wiki）
页面 SHALL 以可折叠附录形式保留 `docs/code_wiki/00_INDEX.md` 至 `06_ISSUE_CURATION.md` 的内容，便于组会 Q&A 时按需展开细节。

#### Scenario: Q&A 定位细节
- **WHEN** 听众追问某个实现细节
- **THEN** 报告人可在附录中快速展开对应章节并定位到相关段落

### Requirement: 静态资源与第三方库
页面 SHALL 不依赖外部 CDN。所需第三方前端库（如 mermaid、代码高亮、Markdown 渲染）应以本地静态文件方式随仓库分发，并从 `assets/group_meeting_report/` 引用。

#### Scenario: 无外部请求
- **WHEN** 浏览器开发者工具监控网络请求
- **THEN** 不出现对外部域名的请求

## MODIFIED Requirements
无（本变更为新增报告页，不修改现有 Wiki 文档内容本身）。

## REMOVED Requirements
无。

