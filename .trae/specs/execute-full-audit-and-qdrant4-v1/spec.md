# Qdrant v1.17.1 全量审计与4轮实战 Spec

## Why

项目已完成 Weaviate v1.36.9 的全量审计和 4 轮实战（spec: execute-full-audit-and-weaviate4-v1），修复了 5 个关键 Bug。现需将同等质量保证流程应用于 Qdrant v1.17.1，确保项目对三库（Milvus/Qdrant/Weaviate）均能稳定运行并产出高质量 Issue。

## What Changes

- 将 `target_db_input` 从 `Weaviate 1.36.9` 切换为 `Qdrant v1.17.1`
- 启动 Qdrant v1.17.1 Docker 容器（端口 6333）
- 执行完整 4 轮实战，监控全流程
- 发现异常立即根因修复（非降级、非替代、非模拟）
- 验证产出 Issue 质量符合设计预期

## Impact

- Affected code: `src/agents/agent0_env_recon.py`（Qdrant 文档策略）、`src/adapters/qdrant_adapter.py`（Qdrant 执行器）、`main.py`（入口配置）
- Affected config: `.trae/config.yaml`（target_db_input 切换）
- Affected docs: 不影响核心文档，仅产出新的 Issue 文件

## ADDED Requirements

### Requirement: Qdrant v1.17.1 全量实战
系统 SHALL 在 Qdrant v1.17.1 上执行最大 4 轮迭代的全自动测试流水线。

#### Scenario: 成功完成 4 轮实战
- **WHEN** 用户启动 `main.py` 且 `target_db_input=Qdrant v1.17.1`, `max_iterations=4`
- **THEN** 系统应：
  1. Agent 0 正确识别目标为 Qdrant 并爬取 Qdrant 官方文档
  2. Agent 3 使用 QdrantAdapter 连接 localhost:6333 执行搜索
  3. 流水线完成 4 轮迭代后以 exit code 0 退出
  4. 产出 GitHub_Issue_*.md 文件，Environment 字段显示 "Qdrant version: qdrant 1.17.1"
  5. 每个 Issue 包含完整的 MRE 代码、Evidence & Documentation

#### Scenario: 异常中断与修复
- **WHEN** 运行中出现死循环、泄漏、超时或逻辑错误
- **THEN** 立即中断，定位根因并实施根治性修复后重跑
- **FORBIDDEN**: 不允许降级、替代、模拟路径

### Requirement: Issue 质量标准
产出的 Issue SHALL 满足以下质量标准：

#### Scenario: Issue 证据链完整性
- **WHEN** 检查任意生成的 GitHub_Issue_*.md 文件
- **THEN** 该文件应包含：
  1. Environment 正确显示 `Qdrant version: qdrant 1.17.1`（非 Milvus/Weaviate）
  2. 完整的 MRE Python 代码（使用 qdrant-client SDK）
  3. 清晰的 Steps To Reproduce / Expected / Actual Behavior
  4. Evidence & Documentation 部分（含官方文档引用或逻辑验证说明）
  5. 准确的 Bug 分类（Type-1/2/3/4）

## MODIFIED Requirements

### Requirement: 文档爬取策略适配 Qdrant
Agent 0 的文档策略 SHALL 根据目标数据库动态调整：
- Qdrant 的 `url_path_allow_substrings` 应覆盖 `/docs.qdrant.tech` 相关路径
- Qdrant 的 `min_docs` 和 `min_chars` 应适配 Qdrant 文档规模
- Qdrant 的 DeepCrawler 参数应足够获取充分文档上下文

## REMOVED Requirements

无。
