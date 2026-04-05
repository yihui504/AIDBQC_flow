# Execution Run with Local Docs v1 Spec

## Why

用户希望在最近完成的“深度提取与来源标注”基础上，进行一轮真实的生产级回归测试。
核心目标是：

1. **真实性验证**：仅使用 `milvus_io_docs_depth3.jsonl` 作为文档源。
2. **主动修复**：监控运行过程中的任何报错（如速率限制、死锁、异步异常），并即时修复。
3. **零糊弄**：禁止使用任何模拟（Mock）或硬编码的契约/缺陷。

## What Changes

* **Configuration**: 确保 `.trae/config.yaml` 中 `docs.source` 为 `local_jsonl`。

* **Monitoring**: 开启 `telemetry` 实时监控。

* **Error Handling**: 如果 Agent 运行失败，直接拦截并修复底层代码。

## Impact

* Affected specs: `tag-contract-sources`, `use-local-docs-library-v2.6`

* Affected code: 全量 Agent 及核心框架

## ADDED Requirements

### Requirement: 实时观测与诊断

系统在运行过程中必须能够暴露详细的内部状态，以便于开发者（Agent）及时介入。

#### Scenario: 遇到 Rate Limit

* **WHEN** LLM 调用触发 429 报错

* **THEN** 系统应能被即时暂停，开发者通过调整速率限制策略或增加重试逻辑后恢复。

### Requirement: 文档源唯一性校验

Agent 0 必须在启动时声明加载的文档来源。

#### Scenario: 加载本地文档库

* **WHEN** Agent 0 启动

* **THEN** 日志必须显示 "Loading local documentation library from: .trae/cache/milvus\_io\_docs\_depth3.jsonl" 且禁用所有网络爬取逻辑。

## MODIFIED Requirements

### Requirement: 错误处理策略

* **OLD**: 部分非关键报错可能通过降级或重试跳过。

* **NEW**: 所有阻塞性报错（Blocking Errors）必须在本次执行周期内被彻底修复，禁止绕过。

