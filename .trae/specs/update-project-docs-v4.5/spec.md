# 项目文档更新 Spec

## Why

项目自 v4.4 以来经历了大量代码演进（Qdrant/Weaviate 全支持、增强去重、隔离执行器、真实向量注入等），但 README.md、AGENTS.md、ROADMAP.md 等核心文档仍停留在 v4.4 阶段，存在以下问题：

- **README.md**: 缺少 Qdrant/Weaviate 支持说明、缺少新增模块（alerting/dashboard/experiments）描述、项目结构树过时、版本号未更新
- **AGENTS.md**: 缺少 Agent 细节更新（如 Agent6 的 IsolatedCodeRunner/EmbeddingGenerator/ReferenceValidator）、缺少完整数据流变更说明
- **ROADMAP.md**: 多个方向已实现（Qdrant/Weaviate 支持）但未标记完成状态，优先级需调整
- **项目结构**: `src/generators/mre_generator.py` 在 README 中列出但实际不存在；缺少 `src/alerting/`、`src/experiments/`、`src/context/` 等模块说明

## What Changes

- 更新 **README.md**：反映当前代码实际状态（v4.4→v4.5），补充新模块、新数据库支持、修正过时信息
- 更新 **AGENTS.md**：补充 Agent 新增能力细节（隔离执行器、真实向量注入、参考验证器等）
- 更新 **ROADMAP.md**：标记已完成项，调整进行中方向
- 修正 **项目结构树**：与实际文件系统对齐

## Impact

- Affected specs: 项目级文档完整性
- Affected code: 不修改代码，仅更新 `.md` 文档

## ADDED Requirements

### Requirement: 文档与代码同步

系统 SHALL 提供准确反映当前代码库状态的文档，包括：

#### Scenario: README.md 完整性
- **WHEN** 开发者或用户阅读 README.md
- **THEN** 文档应准确描述：所有支持的数据库（Milvus/Qdrant/Weaviate）、实际存在的模块结构、当前的配置参数、正确的版本信息

#### Scenario: AGENTS.md 完整性
- **WHEN** 开发者阅读 AGENTS.md 了解 Agent 架构
- **THEN** 文档应包含每个 Agent 的全部子组件（如 Agent6 的 EmbeddingGenerator/IsolatedCodeRunner/EnhancedDeduplicator/ReferenceValidator）

#### Scenario: ROADMAP.md 准确性
- **WHEN** 项目管理者查看 ROADMAP.md
- **THEN** 已完成的功能应标记为 ✅，进行中的功能反映真实开发状态

## MODIFIED Requirements

### Requirement: 核心文档准确性

所有 Markdown 文档文件（README.md、AGENTS.md、ROADMAP.md） SHALL 与当前 `src/` 目录下的实际代码实现保持一致，包括但不限于：

1. Agent 列表与 `src/agents/` 下实际文件对应
2. 数据库适配器列表与 `src/adapters/db_adapter.py` 中实际类对应
3. 配置参数与 `src/config.py` 中实际定义对应
4. 项目目录树与文件系统 `ls` 结果对应
5. 版本号和验证数据反映最新运行结果
