# 放宽 L1 门控 + 增强测试多样性 Spec

## 为什么

分析发现 L1 门控拦截了大量测试（1612 次 L1 Gating Failed），导致潜在缺陷未被发现。用户指出：**四类 bug 都在目标范围内**，维度不匹配本就应该被测试并记录为缺陷。

同时，测试生成多样性不足导致两次运行缺陷完全不重叠。需要评估论文搜索功能的可行性，并增强 prompt 多样性。

## 变更内容

### 变更 1：放宽 L1 门控限制

- **文件**: `src/agents/agent3_executor.py`
- **当前行为**: `dimension not in allowed_dimensions` → 直接返回 False，测试被拦截
- **改进行为**: 允许执行，记录为 Type-1 缺陷（Illegal Request Executed）
- **理由**: Type-1 (L1 Crash/Error) 是目标缺陷类型之一，维度不匹配正是这类缺陷

### 变更 2：增强测试生成多样性

- **文件**: `src/agents/agent2_test_generator.py`
- **改进 A**: 在 prompt 中增加多样性约束
- **改进 B**: 评估论文搜索功能可行性

## 影响范围

- **影响代码**: `agent3_executor.py`（L1 门控逻辑）、`agent2_test_generator.py`（prompt 增强）
- **不影响**: agent0/1/4/5/6、state 格式

## ADDED 需求

### 需求：L1 门控放宽

系统 SHALL 允许维度不匹配的测试执行，并记录为 Type-1 缺陷。

#### 场景：维度不匹配测试
- **WHEN** 测试用例的 dimension 不在 allowed_dimensions 列表中
- **THEN** 测试仍然执行
- **AND** 如果执行成功（本应失败），记录为 Type-1 (Illegal Success)
- **AND** 如果执行失败，记录错误信息

### 需求：测试多样性增强

系统 SHALL 生成更多样化的测试用例。

#### 场景：Prompt 多样性约束
- **WHEN** Agent2 生成测试用例
- **THEN** prompt 包含多样性约束指令
- **AND** 覆盖更多边界场景

### 需求：论文搜索可行性评估

系统 SHALL 评估论文搜索功能的真实可行性。

#### 场景：可行性评估
- **WHEN** 评估 `agent_web_search.py` 的论文搜索能力
- **THEN** 输出可行性报告
- **AND** 如果可行性低，仅修改 prompt

## 验收标准

1. L1 门控放宽后，维度不匹配测试能执行并生成缺陷
2. Agent2 prompt 包含多样性约束
3. 论文搜索可行性评估完成，给出明确结论
