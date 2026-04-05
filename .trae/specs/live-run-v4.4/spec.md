# Live Run v4.4 - L2 门控修复验证

## Why

v4.3 实战审查发现 **关键 Bug**：`state.current_collection` 和 `state.data_inserted` 在 Agent3 execute() 中从未赋值，导致 L2 门控 100% 失败 → DecisionTree 全部落入 Type-2.PF 分支，四型分类退化为单点。现已修复两处代码（state.py 新增字段 + agent3_executor.py 赋值），需实战验证修复效果。

## What Changes

- **配置变更**：`config.yaml` 中 `max_iterations` 从 6 改为 **4**（用户要求）
- **代码变更（已应用）**：
  - [state.py](src/state.py)：WorkflowState 新增 `current_collection: Optional[str]` 和 `data_inserted: bool` 字段
  - [agent3_executor.py](src/agents/agent3_executor.py)：数据注入后设置 `state.current_collection = real_collection_name` 和 `state.data_inserted = True`
- **预期行为变化**：
  - L2 门控正常通过 → 测试用例真正执行 Milvus search
  - DecisionTree 四个分支均有机会触发
  - 缺陷类型分布应呈现多样性（Type-1/2/2.PF/3/4）

## Impact

- Affected code: `src/state.py`, `src/agents/agent3_executor.py`
- Affected config: `.trae/config.yaml` (max_iterations)
- 验证目标：L2 门控状态传递链路 + 四型分类决策树完整性

## ADDED Requirements

### Requirement: L2 Gating State Propagation

系统 SHALL 在 Agent3 数据注入完成后正确设置 WorkflowState 的运行时状态字段：

#### Scenario: L2 门控正常通过
- **WHEN** Agent3.execute() 成功调用 adapter.insert_data() 完成数据注入
- **THEN** state.current_collection 被设置为实际集合名
- **AND** state.data_inserted 被设置为 True
- **AND** 后续 _l2_gating() 调用时返回 (True, None)

### Requirement: Four-Type Classification Distribution

系统 SHALL 在修复后产生多样化的缺陷分类结果：

#### Scenario: 决策树多分支触发
- **WHEN** 运行完成且产生缺陷报告
- **THEN** 缺陷类型分布包含至少 2 种不同类型（Type-1/2/2.PF/3/4）
- **AND** 不再出现 100% 单一类型的情况

## MODIFIED Requirements

### Requirement: Max Iterations Configuration

最大迭代次数 SHALL 为 4（从 6 降低）：
- **原因**：用户要求缩短验证周期
- **影响**：总运行时间减少约 33%

## REMOVED Requirements

无
