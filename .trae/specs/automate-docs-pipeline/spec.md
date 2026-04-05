# Agent0 文档预处理自动化 + 契约门控对齐 Spec

## 为什么

### 问题 1：文档预处理自动化
当前 Agent0 的文档处理缺乏自动化预处理（版本过滤、质量检查），文档库需手动构建。

### 问题 2：契约门控与理论框架不对齐（关键发现）
根据《AI-DB-QC 理论框架报告 v2.0》第4-5节，**门控的目的不是拦截测试，而是精确分类缺陷**。但当前实现存在以下问题：

1. **`allowed_dimensions` 经常为空** → L1 门控形同虚设，无法区分 Type-1
2. **L2 门控不完整** → 无法准确识别 Type-2.PF（前置条件失败）
3. **分类决策树未严格实现** → Agent5 的分类可能与四型分类法不一致

**理论框架红线原则**：
```
Type-3 和 Type-4 必须要求：L₁ = ✓ ∧ L₂ = ✓
否则无法区分：
• 真正的语义违规（真正的 bug）
• 因状态不满足而导致的预期失败（非 bug）
```

## 变更内容

### 变更 1：改造 Agent0 文档预处理

- 新增预处理阶段：爬取后自动执行过滤 → 验证 → 缓存
- 新增验证机制：自检清单 + 警告机制
- 新增缓存管理：本地 JSONL 缓存 + 增量更新

### 变更 2：增强契约提取质量（新增）

- 确保 `allowed_dimensions` 等关键字段不为空
- 添加 fallback 规则库（当 LLM 提取失败时使用）
- 添加契约完整性验证器

### 变更 3：完善双层门控实现（新增）

- L1 门控：完整的维度/参数/类型检查
- L2 门控：集合存在性 + 索引加载状态检查
- 门控结果写入 ExecutionResult 用于分类

### 变更 4：对齐四型分类决策树（新增）

- Agent5 分类逻辑严格遵循理论框架决策树
- 使用 L1/L2 门控结果精确分类
- 区分 Type-1、Type-2、Type-2.PF、Type-3、Type-4

## 影响范围

- **修改文件**: `agent0_env_recon.py`, `agent1_contract_analyst.py`, `agent3_executor.py`, `agent5_diagnoser.py`
- **新增**: 契约 fallback 规则库、契约完整性验证器
- **不影响**: agent2/4/6 核心逻辑

## ADDED 需求

### 需求 A：文档预处理自动化

Agent0 SHALL 在爬取后自动执行预处理。（详见原 spec）

### 需求 B：契约提取质量保证

系统 SHALL 确保 L1 契约关键字段不为空。

#### 场景：allowed_dimensions 为空时
- **WHEN** LLM 提取的 `allowed_dimensions` 为空列表
- **THEN** 使用 fallback 规则库填充默认值
- **AND** 记录警告日志

#### 场景：契约完整性验证
- **WHEN** Agent1 输出契约后
- **THEN** 验证关键字段非空
- **AND** 不满足时触发 warning 而非阻断

### 需求 C：双层门控完整实现

系统 SHALL 实现完整的 L1 + L2 门控。

#### 场景：L1 门控
- **WHEN** 测试用例传入 Agent3
- **THEN** 检查维度、metric、top_k 等 L1 参数
- **AND** 返回 `(l1_passed, l1_warning)` 元组
- **AND** 结果写入 `ExecutionResult.l1_warning`

#### 场景：L2 门控
- **WHEN** L1 通过后
- **THEN** 检查集合是否存在、索引是否加载
- **AND** 返回 `(l2_passed, l2_reason)`
- **AND** 结果影响后续分类

### 需求 D：四型分类对齐

Agent5 SHALL 严格遵循理论框架的四型分类决策树。

#### 决策树（必须实现）：
```
                    L₁: 契约有效？
                         │
           ┌─────────────┴─────────────┐
          NO                        YES
           │                          │
    L₂检查（可选）              操作成功？
           │              ┌─────────┴─────────┐
      操作成功？          NO               YES
       │     │           │                 │
     YES    NO    L₂:前置条件通过？    L₂:前置条件通过？
      │      │         │                 │
   Type-1  Type-2  NO         YES    NO         YES
(非法成功)(诊断)  │           │      │           │
                └───┬───────┬──┘      ↓           ↓
                    ↓       ↓      L₂检查失败  L₂:预言机通过？
                Type-2.PF  L₂有效？   (Type-2.PF)  │
                           │              ┌────┴────┐
                          YES             NO       YES
                           │               │        │
                       可忽略           Type-4    Type-3
                                       (语义违规) (运行时失败)
```

## 验收标准

1. Agent0 自动化文档预处理正常工作
2. `allowed_dimensions` 不再为空（或使用合理 fallback）
3. L1 + L2 门控结果正确写入 ExecutionResult
4. Agent5 分类结果与理论框架一致
5. 运行日志显示门控结果被正确使用
