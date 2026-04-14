# Qdrant/Weaviate 实战验证与完善 Spec

## Why

QdrantAdapter 和 WeaviateAdapter 已实现，但尚未在真实 Docker 环境中进行端到端测试。需要在实战中验证适配器的正确性，发现并修复潜在问题，确保跨数据库支持真正可用。

## What Changes

### 1. Docker 环境验证
- 启动 Qdrant Docker 容器
- 启动 Weaviate Docker 容器
- 验证容器健康状态

### 2. 适配器实战测试
- 连接测试
- Collection 创建测试
- 数据插入测试
- 向量搜索测试
- 错误处理测试

### 3. 问题修复与完善
- 根据测试结果修复发现的问题
- 完善错误处理和日志
- 更新文档

## Impact

- Affected code: `src/adapters/db_adapter.py`, `src/contract_fallbacks.py`
- Affected configs: `docker-compose.qdrant.yml`, `docker-compose.weaviate.yml`
- Affected docs: `README.md`, `ROADMAP.md`

## ADDED Requirements

### Requirement: Qdrant 实战验证
系统 SHALL 在真实 Qdrant Docker 环境中完成以下测试：
- 连接建立与断开
- Collection 创建与删除
- 向量数据插入
- 向量相似度搜索
- 错误场景处理

#### Scenario: Qdrant 端到端测试
- **WHEN** 启动 Qdrant Docker 容器并运行测试
- **THEN** 所有基本操作成功完成，无未捕获异常

### Requirement: Weaviate 实战验证
系统 SHALL 在真实 Weaviate Docker 环境中完成以下测试：
- 连接建立与断开
- Collection 创建与删除
- 向量数据插入
- 向量相似度搜索
- 错误场景处理

#### Scenario: Weaviate 端到端测试
- **WHEN** 启动 Weaviate Docker 容器并运行测试
- **THEN** 所有基本操作成功完成，无未捕获异常

## MODIFIED Requirements

无

## REMOVED Requirements

无
