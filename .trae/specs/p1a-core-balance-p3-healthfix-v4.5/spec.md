# P1-a 核心能力均衡化 + P3 代码健康度修复 实施规格

## Why

基于代码深度审查，项目存在两个亟待解决的问题：

**P1-a（核心短板）**: v4.5 验证数据显示缺陷分布严重失衡 — Type-4 占 91.7%，Type-1/Type-3 检出率为 0%。根因已定位：
1. Agent3 的 L1 门控在检测到违规时返回 warning 但仍允许执行，而非法维度请求通常执行失败（变为 Type-2 而非 Type-1）
2. Agent4 传统预言机仅检查距离排序单调性，缺少结果数量、向量维度、metric 范围等校验，导致 Type-3 无法触发
3. Agent2 测试生成 prompt 缺少定向的 Type-1/Type-3 用例生成策略

**P3（技术债务）**: 3 个代码级问题影响系统可维护性和跨数据库兼容性：
1. Agent5 硬编码容器名 `milvus-standalone`（切换 Qdrant/Weaviate 必失败）
2. Dashboard 导入不存在的 `src.roadmap` 模块（无法启动）
3. AGENTS.md 版本号标注不一致（v4.4 vs 实际 v4.5）

## What Changes

### P1-a 改动范围（核心能力增强）

- **Agent3 (`agent3_executor.py`)**: 增强 `_l1_gating()` 返回结构，新增 `l1_violation_details` 字段记录违规详情（违规类型+参数值+期望范围），使下游 Agent5 能区分"轻微警告"和"严重违规"
- **Agent5 (`agent5_diagnoser.py`)**:
  - 修改 `classify_defect_v2()` 的 L1 合规判定逻辑：引入 `violation_severity` 概念，对极端参数值（dim=1, dim>10000, 非法 metric）提升为"硬违规"
  - 修复硬编码容器名：`DockerLogsProbe(container_name=...)` 改为从 `state.db_config` 或配置读取
  - 新增 Type-3 判定路径：当传统预言机检测到异常但 LLM 语义预言机通过时，应分类为 Type-3（当前代码缺失此路径！）
- **Agent4 (`agent4_oracle.py`)**: 增强 `_traditional_oracle_check()` 为 `_traditional_oracle_check_enhanced()`，新增 4 项检查：
  1. 结果数量与 top_k 一致性
  2. 向量维度一致性
  3. metric_type 与距离值范围对应关系（L2≥0, COSINE/IP∈[-1,1]）
  4. distance 值合法性（非 NaN/Inf）
- **Agent2 (`agent2_test_generator.py`)**: 在 system prompt 中新增 Type-1/Type-3 定向策略：
  - Strategy 9: **Type-1 Hunting** — 构造"应该被拒绝但可能被接受"的边界用例（如刚好超出允许列表的维度）
  - Strategy 10: **Type-3 Hunting** — 构造满足契约但可能违反传统属性的用例（如重复查询一致性、空结果集边界）
- **state.py**: `ExecutionResult` 新增 `l1_violation_details: Optional[Dict]` 字段

### P3 改动范围（代码健康度修复）

- **`agent5_diagnoser.py:24`**: `container_name="milvus-standalone"` → 从 config 或 state 动态获取
- **`dashboard/app.py:35`**: 删除 `from src.roadmap import Roadmap`，替换为直接数据读取逻辑
- **`AGENTS.md:3`**: 版本号 `v4.4` → `v4.5`

## Impact

- Affected specs: 核心缺陷检测能力（P1-a 影响决策树全链路）、系统可维护性（P3）
- Affected code: `agent3_executor.py`, `agent5_diagnoser.py`, `agent4_oracle.py`, `agent2_test_generator.py`, `state.py`, `dashboard/app.py`, `AGENTS.md`

## ADDED Requirements

### Requirement: P1-a-1 L1 违规详情增强

Agent3 的 `_l1_gating()` SHALL 返回增强的违规信息：

#### Scenario: L1 违规详情记录
- **WHEN** Agent3 检测到 dimension / metric_type / top_k 违规
- **THEN** ExecutionResult SHALL 包含 `l1_violation_details` 字典，包含 `violation_type`, `actual_value`, `expected_range`, `severity`(soft/hard)

### Requirement: P1-a-2 决策树 Type-1/Type-3 路径修复

Agent5 的 `classify_defect_v2()` SHALL 正确分类 Type-1 和 Type-3 缺陷：

#### Scenario: Type-1 分类（非法成功）
- **WHEN** L1 有 hard-severity 违规 AND 执行成功
- **THEN** 分类为 Type-1

#### Scenario: Type-3 分类（传统预言机违规）
- **WHEN** L1 通过 AND 执行成功 AND 传统预言机检测到异常（即使 LLM 语义预言机通过）
- **THEN** 分类为 Type-3（**当前此路径缺失，需新增**）

### Requirement: P1-a-3 传统预言机增强

Agent4 的传统预言机 SHALL 执行多属性校验：

#### Scenario: 增强型传统预言机
- **WHEN** 执行成功且有 raw_response
- **THEN** 传统预言机 SHALL 检查：距离单调性 + 结果数一致性 + 向量维度一致性 + metric 范围合法性

### Requirement: P1-a-4 定向测试生成

Agent2 的 prompt SHALL 包含 Type-1/Type-3 定向策略：

#### Scenario: 平衡化测试覆盖
- **WHEN** Agent2 生成测试用例
- **THEN** 生成的用例集 SHALL 包含专门针对 Type-1（契约绕过）和 Type-3（属性违反）的用例模板

### Requirement: P3-1 硬编码消除

Agent5 的 DockerLogsProbe 容器名 SHALL 从配置动态获取：

#### Scenario: 跨数据库兼容
- **WHEN** 系统目标为 Qdrant 或 Weaviate（非 Milvus）
- **THEN** DockerLogsProbe 使用对应数据库的容器名，而非硬编码 `milvus-standalone`

### Requirement: P3-2 Dashboard 导入修复

Dashboard 应用 SHALL 能正常启动：

#### Scenario: Dashboard 启动
- **WHEN** 用户运行 `streamlit run dashboard/app.py`
- **THEN** 应用无 ImportError，能正常加载并展示数据

### Requirement: P3-3 文档版本一致

AGENTS.md 版本号 SHALL 与实际代码版本一致。

## MODIFIED Requirements

### Requirement: ExecutionResult Schema

`ExecutionResult` 数据模型 SHALL 新增 `l1_violation_details: Optional[Dict[str, Any]]` 字段，默认值为 None。该字段包含结构化的 L1 违规信息。

### Requirement: Agent4 Traditional Oracle Check

`_traditional_oracle_check()` 方法 SHALL 重命名为 `_traditional_oracle_check_enhanced()` 或在其内部扩展检查项，保持向后兼容。
