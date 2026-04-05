# Agent0 文档预处理自动化 + 契约门控对齐 - 任务列表

## [x] Task 1：扩展配置模型
- **优先级**：P0
- **子任务**：
  - [x] 1.1：修改 `src/config.py` - 添加 DocsConfig 模型（cache/filter/validation）
  - [x] 1.2：修改 `.trae/config.yaml` - 添加 docs 配置项
  - [x] 1.3：添加契约 fallback 规则库配置

## [x] Task 2：实现 Agent0 预处理方法
- **优先级**：P0
- **依赖**：Task 1
- **子任务**：
  - [x] 2.1：实现 `_filter_docs()` - 版本匹配 + 质量过滤
  - [x] 2.2：实现 `_validate_docs()` - 文档数量 + 关键文档检查
  - [x] 2.3：实现 `_save_docs_cache()` / `_load_docs_cache()` - JSONL 读写 + TTL
  - [x] 2.4：集成到 Agent0 主流程（cache-first 策略）

## [x] Task 3：增强契约提取质量
- **优先级**：P0（关键）
- **依赖**：Task 1
- **子任务**：
  - [x] 3.1：创建 `src/contract_fallbacks.py` - Milvus 契约 fallback 规则库
  - [x] 3.2：`apply_fallbacks()` 函数 - 自动填充空字段
  - [x] 3.3：MilvusContractDefaults 包含完整默认值

## [x] Task 4：完善双层门控实现
- **优先级**：P0（关键）
- **依赖**：Task 3
- **子任务**：
  - [x] 4.1：增强 `_l1_gating()` - dimension/metric/top_k 三重检查
  - [x] 4.2：实现 `_l2_gating()` - 集合存在性 + 数据插入检查
  - [x] 4.3：ExecutionResult 新增 l2_result 字段
  - [x] 4.4：_execute_single_case() 集成双层门控

## [x] Task 5：对齐四型分类决策树
- **优先级**：P0（关键）
- **依赖**：Task 4
- **子任务**：
  - [x] 5.1：实现 `classify_defect_v2()` - 完整决策树
  - [x] 5.2：使用 L1/L2 门控结果进行分类
  - [x] 5.3：区分 Type-1/Type-2/Type-2.PF/Type-3/Type-4
  - [x] 5.4：重构 _classify_defect() 委托给 v2

## [x] Task 6：端到端验证
- **优先级**：P0
- **依赖**：Task 5
- **子任务**：
  - [x] 6.1：运行验证脚本 → 全部 6 项测试 PASS
  - [x] 6.2：确认 allowed_dimensions 有 fallback 默认值
  - [x] 6.3：确认 L1/L2 门控正常工作
  - [x] 6.4：确认四型分类符合理论框架

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 5]

# 关键路径：Task 1 → Task 3 → Task 4 → Task 5 → Task 6 ✅
