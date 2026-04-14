# Agent6 Verifier 多数据库适配 Spec

## Why

Weaviate 实战运行产出的 16 个 GitHub Issues 全部包含 Milvus 硬编码内容（pymilvus SDK、MilvusClient、localhost:19530），根因是 [agent6_verifier.py](src/agents/agent6_verifier.py) L291-L347 的 system prompt 模板将 **"for the Milvus vector database"**、**"SDK/Client**: pymilvus**、**"using the pymilvus SDK"** 等字样硬编码。需要将模板改为根据 `state.db_config.db_name` 动态生成，确保切换目标数据库时 Issue 内容自动适配。

## What Changes

- **代码变更**：
  - [agent6_verifier.py](src/agents/agent6_verifier.py)：system prompt 从硬编码 Milvus 改为**数据库无关模板** + 动态注入数据库特定片段
  - 新增 `_get_db_template_fragments(db_name)` 方法，返回对应数据库的 SDK 名称、连接示例、MRE 模板
- **支持的目标数据库**：milvus（pymilvus）、qdrant（qdrant-client）、weaviate（weaviate-client）
- **不破坏现有功能**：默认回退到 milvus 模板（向后兼容）

## Impact

- Affected code: `src/agents/agent6_verifier.py`（仅修改 prompt 模板构建逻辑）
- Affected output: 所有后续运行的 GitHub Issue 将使用正确的目标数据库 SDK 和连接信息
- 不影响 Agent 0-5、Reflection Agent 或任何 Adapter 代码

## ADDED Requirements

### Requirement: Verifier 多数据库模板适配

Agent6 Verifier 的 GitHub Issue 生成模板 SHALL 根据 `state.db_config.db_name` 动态选择正确的数据库 SDK 信息：

#### Scenario: Weaviate 目标数据库
- **WHEN** `state.db_config.db_name == "weaviate"`
- **THEN** Issue 模板中使用 `weaviate-client` 作为 SDK/Client，MRE 使用 weaviate Python client API，Environment 显示 `Weaviate version`

#### Scenario: Qdrant 目标数据库
- **WHEN** `state.db_config.db_name == "qdrant"`
- **THEN** Issue 模板中使用 `qdrant-client` 作为 SDK/Client，MRE 使用 QdrantClient Python API

#### Scenario: Milvus 目标数据库（默认/向后兼容）
- **WHEN** `state.db_config.db_name == "milvus"` 或 db_name 为空
- **THEN** 保持原有 pymilvus 模板不变

#### Scenario: 动态注入机制
- **WHEN** Verifier 执行 `generate_issue()` 时
- **THEN** 从 state 中读取 db_config.db_name，调用 `_get_db_template_fragments()` 获取对应数据库的模板片段，拼接到 system prompt 中

## MODIFIED Requirements

### Requirement: Verifier System Prompt

Verifier 的 system prompt SHALL 不再包含任何硬编码的数据库名称或 SDK 名称。所有数据库相关信息通过 `{db_template}` 占位符在运行时动态替换。
