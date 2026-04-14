# Qdrant v1.17.1 + Weaviate v1.36.9：暴露问题修复 + 5 轮 Bug Mining（从零开始）Spec

## Why

当前项目已具备 Qdrant/Weaviate 适配器与端到端多 Agent 流水线，但在真实版本升级（Qdrant v1.17.1、Weaviate v1.36.9）与更长迭代（5 轮）下，仍可能暴露：
- 适配器行为差异导致的执行失败（连接、schema、batch、filter、metric 等）
- L1/L2 门控边界条件导致的误判、误报或漏报
- 缺陷验证、去重、Issue 产出链路的格式/证据/引用缺失
- 运行稳定性问题（崩溃、挂死、重试风暴、资源泄漏）

本 Spec 的目标是：在全新环境中完成两库各 5 轮 Bug Mining，修复被运行暴露的“测试台问题”（非数据库本身缺陷），并产出可贡献的高质量 Issue 工件。

## Scope

- 目标数据库：
  - Qdrant: **v1.17.1**
  - Weaviate: **v1.36.9**
- 执行方式：使用项目现有多 Agent 流水线（Agent0→Agent6），在真实 Docker 环境上运行（不模拟、不替代）。
- Bug Mining 迭代数：每个数据库 **5 轮**（共 10 轮）。
- 修复范围：仅修复“暴露问题”中属于本项目测试台/适配器/门控/验证器/配置/脚本的问题；不修改数据库源码。

## Non-Goals

- 不做性能基准对比与容量压测（除非运行被迫触发）。
- 不引入新的数据库类型或新的重大架构重写。
- 不承诺一定发现数据库真实缺陷；但必须产出可复现的运行报告与证据链。

## Definition: 暴露问题（Exposed Issues）

运行过程中被暴露、且可归因于本项目自身的任一问题，包括但不限于：
- 运行崩溃/异常退出/死循环/无上限重试
- 适配器与目标版本不兼容（API 变更、参数差异、返回结构变化）
- L1/L2 门控误判（例如：应 PASS 却 FAIL，或应 FAIL 却 PASS）
- 缺陷分类与证据输出不完整（缺少环境、步骤、期望/实际、日志片段、官方文档引用）
- Issue 模板不合规或敏感信息泄露风险（keys、tokens、内部路径等）

## From Scratch（从零开始）要求

系统 SHALL 在干净环境下运行本次 Bug Mining：
- **每个数据库使用全新容器与全新数据卷**（避免历史数据/collection 干扰）
- **每次 run 生成独立 run_id 与独立工件目录**（.trae/runs 下可追溯）
- **不复用旧的 run 产物做结论**（允许复用文档缓存以节省时间，但必须记录 cache_hit 状态）

## ADDED Requirements

### Requirement: 版本固定与可追溯

系统 SHALL 将目标数据库版本写入运行态配置与 Issue 环境信息中：

#### Scenario: Qdrant 版本固定
- **WHEN** 用户输入包含 “Qdrant 1.17.1”
- **THEN** Agent0 拉起镜像 `qdrant/qdrant:1.17.1`
- **AND** Issue 环境信息中包含 Qdrant version=1.17.1

#### Scenario: Weaviate 版本固定
- **WHEN** 用户输入包含 “Weaviate 1.36.9”
- **THEN** Agent0 拉起镜像 `cr.weaviate.io/semitechnologies/weaviate:1.36.9`
- **AND** Issue 环境信息中包含 Weaviate version=1.36.9

### Requirement: 两库各 5 轮完整运行

系统 SHALL 分别在 Qdrant 与 Weaviate 上完成 5 轮迭代：

#### Scenario: Qdrant 5 轮
- **WHEN** 运行目标为 Qdrant 且 max_iterations=5
- **THEN** 运行正常结束（exit_code=0）
- **AND** 产出完整工件（日志、缺陷、Issue markdown）

#### Scenario: Weaviate 5 轮
- **WHEN** 运行目标为 Weaviate 且 max_iterations=5
- **THEN** 运行正常结束（exit_code=0）
- **AND** 产出完整工件（日志、缺陷、Issue markdown）

### Requirement: 暴露问题修复闭环

系统 SHALL 对暴露问题形成“定位→修复→最小回归→重跑”的闭环：

#### Scenario: 归因到测试台
- **WHEN** 某故障被判定为测试台问题（非数据库缺陷）
- **THEN** 在主分支代码中修复（不做临时手工补丁）
- **AND** 通过最小回归验证（单库 1 轮或脚本级 smoke）
- **AND** 继续执行后续迭代（必要时从当前库重新开始计数）

### Requirement: Issue 工件质量门槛

系统 SHALL 仅输出社区可用的 Issue 工件：

#### Scenario: Issue 模板合规
- **WHEN** 生成 Issue markdown
- **THEN** 包含 Environment / Steps To Reproduce / Expected / Actual / Evidence
- **AND** 包含官方文档引用（可验证的引用片段或链接）
- **AND** 不包含 secrets（API keys、tokens、私密 endpoint）

## MODIFIED Requirements

### Requirement: 最大迭代次数配置

max_iterations SHALL 为 5：
- **原因**：本次为 5 轮 Bug Mining
- **影响**：单库运行时间增加，需更严格的稳定性与资源监控

### Requirement: 目标数据库输入

target_db_input SHALL 明确包含数据库名与版本：
- Qdrant: “深度测试 Qdrant 1.17.1”
- Weaviate: “深度测试 Weaviate 1.36.9”

## REMOVED Requirements

无
