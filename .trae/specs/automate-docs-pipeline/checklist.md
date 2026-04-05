# Agent0 文档预处理自动化 + 契约门控对齐 - 验证清单

## Task 1：配置模型
- [x] DocsConfig 模型存在，包含 cache/filter/validation 字段
- [x] config.yaml 包含 docs 配置项
- [x] 配置加载正确

## Task 2：Agent0 预处理
- [x] `_filter_docs()` 能过滤版本和质量
- [x] `_validate_docs()` 能检测质量问题
- [x] JSONL 缓存读写正常（含 TTL 检查）
- [x] 集成到 Agent0 主流程（cache-first 策略）

## Task 3：契约提取质量（关键）
- [x] fallback 规则库包含 Milvus 默认维度（36 种维度值）
- [x] fallback 规则库包含 supported_metrics（6 种距离度量）
- [x] apply_fallbacks() 能自动填充空字段
- [x] 日志记录哪些字段被 fallback 填充

## Task 4：双层门控实现（关键）
- [x] L1 门控检查 dimension/metric/top_k 三参数
- [x] L2 门控检查 collection/data 状态
- [x] ExecutionResult 包含 l1_warning 和 l2_result
- [x] _execute_single_case() 集成双层门控调用

## Task 5：四型分类对齐（关键）
- [x] classify_defect_v2() 实现完整决策树
- [x] L1=✗ 且 success → Type-1 ✓
- [x] L1=✓ 且 L2=✗ → Type-2.PF ✓
- [x] L1=✓ 且 oracle_fail → Type-4 ✓
- [x] _classify_defect() 委托给 v2 实现

## Task 6：端到端验证
- [x] 6/6 测试全部 PASS (exit_code=0)
- [x] 日志显示 allowed_dimensions 已填充
- [x] L1 Warning 正确输出维度不匹配警告
- [x] L2 Gating 正确返回状态和原因
- [x] 四型分类结果符合理论框架
