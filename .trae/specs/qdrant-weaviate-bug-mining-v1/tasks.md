# Qdrant v1.17.1 + Weaviate v1.36.9（两库各 5 轮，从零开始）- 任务列表

## [x] Task 1：修复运行前暴露问题（配置化/版本固定/从零开始）
- **优先级**：P0
- **目标**：消除“必现阻塞”，确保两库长跑不被入口/配置/环境复用机制打断
- **子任务**：
  - [x] 1.1：入口配置化：main 入口从 `.trae/config.yaml` 读取 `harness.target_db_input` 与 `harness.max_iterations`
  - [x] 1.2：版本固定：更新 [docker-compose.qdrant.yml](file:///c:/Users/11428/Desktop/ralph/docker-compose.qdrant.yml) 为 Qdrant v1.17.1、[docker-compose.weaviate.yml](file:///c:/Users/11428/Desktop/ralph/docker-compose.weaviate.yml) 为 Weaviate v1.36.9
  - [x] 1.3：Agent0 版本归一化：Qdrant 支持 `v1.17.1`/`1.17.1`，Weaviate 支持 `v1.36.9`/`1.36.9` 且最终镜像标签为 `1.36.9`
  - [x] 1.4：Agent0 Weaviate fallback 默认版本更新为 1.36.9（当解析为 latest/缺省时）
  - [x] 1.5：从零开始：为 Agent0 增加可配置开关以禁用 “hot sandbox” 端口复用（from_scratch 模式下必须新起容器/新卷）
  - [x] 1.6：文档配置一致性：Agent0 的 docs cache 读取/写入路径与 TTL 使用 `.trae/config.yaml` 的 `docs.*`（而非 AppConfig 默认 milvus 路径），并确保 Qdrant/Weaviate 不会误用 Milvus 文档缓存

## [x] Task 2：基线与环境就绪
- **优先级**：P0
- **依赖**：Task 1
- **目标**：确保测试台可运行、依赖齐全、不会因环境问题中断
- **子任务**：
  - [x] 2.1：确认 Python 虚拟环境可用（venv312/Scripts/python.exe）
  - [x] 2.2：补齐 .env（LLM 所需配置），避免运行期缺参
  - [x] 2.3：确认 Docker 与 docker compose 可用
  - [x] 2.4：运行单元测试（pytest）作为基线

## [x] Task 3：Qdrant v1.17.1 从零拉起 + 适配器冒烟
- **优先级**：P0
- **依赖**：Task 2
- **子任务**：
  - [x] 3.1：以全新容器与全新数据卷启动 Qdrant v1.17.1
  - [x] 3.2：验证端口连通与健康检查（localhost:6333/6334）
  - [x] 3.3：运行 scripts/test_qdrant_adapter.py 冒烟
  - [x] 3.4：记录版本与 endpoint，作为 Issue 环境信息来源

## [x] Task 4：Weaviate v1.36.9 从零拉起 + 适配器冒烟
- **优先级**：P0
- **依赖**：Task 2
- **子任务**：
  - [x] 4.1：以全新容器与全新数据卷启动 Weaviate v1.36.9
  - [x] 4.2：验证端口连通与健康检查（localhost:8081/50051）
  - [x] 4.3：运行 scripts/test_weaviate_adapter.py 冒烟
  - [x] 4.4：确认容器环境变量满足“无向量化器模块”的测试假设

## [x] Task 5：运行前短跑与暴露问题闭环（每库 1 轮）
- **优先级**：P0
- **依赖**：Task 3, Task 4
- **目标**：先消除“必现阻塞”，避免 5 轮长跑被早期失败浪费
- **子任务**：
  - [x] 5.1：Qdrant 短跑：max_iterations=1
  - [x] 5.2：Weaviate 短跑：max_iterations=1
  - [x] 5.3：对失败进行归因：数据库缺陷 vs 测试台缺陷
  - [x] 5.4：对测试台缺陷进行修复（适配器/门控/验证器/脚本/配置）并执行最小回归

## [x] Task 6：Qdrant 5 轮 Bug Mining（从零开始）
- **优先级**：P0
- **依赖**：Task 5
- **子任务**：
  - [x] 6.1：配置 `harness.target_db_input="深度测试 Qdrant v1.17.1"`，`harness.max_iterations=5`
  - [x] 6.2：运行端到端流水线并实时监控（崩溃/挂死/重试风暴立即止损）
  - [x] 6.3：运行结束后收集工件（run 目录、缺陷列表、Issue markdown）

## [ ] Task 7：Weaviate 5 轮 Bug Mining（从零开始）
- **优先级**：P0
- **依赖**：Task 5
- **子任务**：
  - [ ] 7.1：配置 `harness.target_db_input="深度测试 Weaviate v1.36.9"`，`harness.max_iterations=5`
  - [ ] 7.2：运行端到端流水线并实时监控（崩溃/挂死/重试风暴立即止损）
  - [ ] 7.3：运行结束后收集工件（run 目录、缺陷列表、Issue markdown）

## [ ] Task 8：复盘、去重、交付与回归保障
- **优先级**：P1
- **依赖**：Task 6, Task 7
- **子任务**：
  - [ ] 8.1：跨 run 去重与聚类（按缺陷语义与行为证据）
  - [ ] 8.2：筛除测试台误报，保留可复现且证据完整的候选
  - [ ] 8.3：生成每库摘要（缺陷类型分布、Top issue、失败原因）
  - [ ] 8.4：回归：pytest +（如有）lint/typecheck，确保修复不破坏 Milvus

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
- [Task 5] depends on [Task 3], [Task 4]
- [Task 6] depends on [Task 5]
- [Task 7] depends on [Task 5]
- [Task 8] depends on [Task 6], [Task 7]
