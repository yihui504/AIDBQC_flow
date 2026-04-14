# Qdrant 实战运行 Spec (max_iterations=3)

## Why

项目已具备 QdrantAdapter 完整实现（[db_adapter.py](src/adapters/db_adapter.py)），但 Agent3 执行器硬编码仅支持 Milvus，且 main.py 目标数据库写死为 Milvus。需要修复这些阻塞问题，在真实 Qdrant 环境上执行最大轮数 3 的实战运行，观察行为和产出，过程中遇到问题即时修复。

## What Changes

- **代码变更**：
  - [agent3_executor.py](src/agents/agent3_executor.py)：execute() 方法增加 Qdrant 和 Weaviate adapter 分支支持（当前仅支持 milvus）
  - [main.py](main.py)：target_db_input 从 Milvus 改为 Qdrant
- **配置变更**：
  - [.trae/config.yaml](.trae/config.yaml)：max_iterations 从 4 改为 3
- **环境准备**：
  - 确保 Qdrant Docker 容器在 localhost:6333 运行
  - 使用 docker-compose.qdrant.yml 启动

## Impact

- Affected code: `src/agents/agent3_executor.py`, `main.py`
- Affected config: `.trae/config.yaml`
- 验证目标：完整多 Agent 流水线在 Qdrant 上端到端跑通，观察各 Agent 行为和最终缺陷报告产出

## ADDED Requirements

### Requirement: Agent3 多数据库 Adapter 支持

Agent3 ExecutionGatingAgent.execute() SHALL 根据 db_config.db_name 选择正确的适配器：

#### Scenario: Qdrant 适配器选择
- **WHEN** db_config.db_name 为 "qdrant"
- **THEN** 使用 QdrantAdapter 初始化并执行测试

#### Scenario: Weaviate 适配器选择
- **WHEN** db_config.db_name 为 "weaviate"
- **THEN** 使用 WeaviateAdapter 初始化并执行测试

### Requirement: Qdrant 实战运行验证

系统 SHALL 在 Qdrant 上完成至少 3 轮 Fuzzing 循环：

#### Scenario: 端到端流水线执行
- **WHEN** 启动 main.py 且 target_db_input 指向 Qdrant
- **THEN** Agent0→Agent1→Agent2→Agent3→...→Agent6 全链路正常执行
- **AND** Agent3 成功连接 Qdrant 并执行实际 search 操作
- **AND** 最终产出缺陷报告

## MODIFIED Requirements

### Requirement: 最大迭代次数配置

最大迭代次数 SHALL 为 3：
- **原因**：用户要求缩短实战验证周期
- **影响**：总运行时间减少

### Requirement: 目标数据库输入

target_db_input SHALL 指向 Qdrant：
- **原因**：本次实战目标为 Qdrant 而非 Milvus
