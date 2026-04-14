# Weaviate 实战运行 Spec (max_iterations=3)

## Why

项目已具备 WeaviateAdapter 完整实现（[db_adapter.py](src/adapters/db_adapter.py)），Agent3 执行器也已支持 Weaviate 分支（[agent3_executor.py](src/agents/agent3_executor.py) L284-285），但 main.py 当前目标数据库仍指向 Qdrant，且 config.yaml 最大迭代数为 4。需要在真实 Weaviate 环境上执行最大轮数 3 的实战运行，观察行为和最终产出，过程中遇到问题即时修复（不回退、不模拟、不替代），修完即重跑。同时确保对 Milvus/Qdrant 的兼容性不受破坏。

## What Changes

- **配置变更**：
  - [main.py](main.py)：target_db_input 从 "请帮我深度测试一下 Qdrant latest" 改为 Weaviate
  - [.trae/config.yaml](.trae/config.yaml)：max_iterations 从 4 改为 3
- **环境准备**：
  - 使用 [docker-compose.weaviate.yml](docker-compose.weaviate.yml) 启动 Weaviate 容器（localhost:8081）
  - 验证容器连接正常
- **运行与修复**：
  - 执行完整流水线，实时监控日志
  - 遇到错误即时定位根因并修复代码
  - 修复后重新运行直到成功完成 3 轮迭代

## Impact

- Affected code: `main.py`（仅改输入参数）
- Affected config: `.trae/config.yaml`（仅改迭代次数）
- **不影响其他数据库适配器代码**：MilvusAdapter / QdrantAdapter / WeaviateAdapter 均保持原样
- 验证目标：完整多 Agent 流水线在 Weaviate 上端到端跑通，观察各 Agent 行为和最终缺陷报告产出

## ADDED Requirements

### Requirement: Weaviate 实战运行验证

系统 SHALL 在 Weaviate 上完成至少 3 轮 Fuzzing 循环：

#### Scenario: 端到端流水线执行
- **WHEN** 启动 main.py 且 target_db_input 指向 Weaviate
- **THEN** Agent0→Agent1→Agent2→Agent3→...→Agent6 全链路正常执行
- **AND** Agent3 成功连接 Weaviate 并执行实际 search 操作
- **AND** 最终产出缺陷报告

#### Scenario: 运行中问题修复
- **WHEN** 运行过程中遇到任何错误或异常行为
- **THEN** 立即定位根因并修复对应代码（不回退、不模拟、不替代）
- **AND** 修复完成后重新运行完整流水线

#### Scenario: 多数据库兼容性保障
- **WHEN** 本次修改仅涉及 main.py 输入参数和 config.yaml 配置
- **THEN** MilvusAdapter 和 QdrantAdapter 代码完全不受影响
- **AND** 切换回其他数据库时无需额外修改

## MODIFIED Requirements

### Requirement: 最大迭代次数配置

最大迭代次数 SHALL 为 3：
- **原因**：用户要求缩短实战验证周期
- **影响**：总运行时间减少

### Requirement: 目标数据库输入

target_db_input SHALL 指向 Weaviate：
- **原因**：本次实战目标为 Weaviate
