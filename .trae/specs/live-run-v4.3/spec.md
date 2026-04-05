# 实战 v4.3：文档预处理 + 契约门控 + 四型分类 验证 Spec

## 为什么

刚刚完成了 4 项关键改进：
1. **Agent0 文档预处理自动化** - cache-first 策略 + 过滤/验证/缓存
2. **契约 fallback 规则库** - allowed_dimensions 不再为空
3. **双层门控 (L1+L2)** - 完整的参数检查 + 运行时状态检查
4. **四型分类决策树** - 严格对齐理论框架

需要通过实战运行验证这些改进的实际效果。

## 变更内容

### 本次运行特点

- **max_iterations: 6**
- 使用本地 JSONL 文档库
- 重点观察：
  1. Agent0 缓存是否命中
  2. allowed_dimensions 是否被填充
  3. L1/L2 门控日志输出
  4. 四型分类结果分布

## 影响范围

- **运行配置**: `.trae/config.yaml`
- **产出**: GitHub Issues + 运行日志 + telemetry

## ADDED 需求

### 需求：实战验证运行

系统 SHALL 执行一次完整的实战运行以验证所有改进效果。

#### 场景：Agent0 缓存机制
- **WHEN** 启动运行且本地缓存有效
- **THEN** 日志显示 "cache=HIT"
- **AND** 跳过爬取阶段，直接使用缓存

#### 场景：契约填充效果
- **WHEN** Agent1 提取契约后
- **THEN** allowed_dimensions 不为空
- **AND** 如为空则触发 fallback 填充

#### 场景：门控与分类
- **WHEN** 测试执行和缺陷诊断时
- **THEN** L1 Warning 出现于维度不匹配测试
- **AND** L2 Result 记录集合状态
- **AND** 分类结果包含 Type-1/Type-2.PF 等新类型

## 验收标准

1. 运行成功完成，无崩溃
2. Agent0 缓存命中或预处理正常工作
3. allowed_dimensions 有值（LLM 或 fallback）
4. L1/L2 门控结果出现在日志中
5. 四型分类结果符合理论框架
6. 缺陷产出质量良好
