# 对抗性与压力攻击升级规范 (v3.5)

## 为什么
当前 AI-DB-QC 流水线在工程稳健性上表现优异，但在“漏洞挖掘攻击性”上存在显著瓶颈：
1. **测试用例过于守规矩**：Agent 2 仅生成合法用例，导致无法挖掘 Type-1（非法成功）和 Type-2（诊断不足）缺陷。
2. **执行层过度拦截**：Agent 3 作为“防火墙”拦截了非法请求，阻止了对数据库边界处理能力的实测。
3. **缺乏压力与时序攻击**：数据规模较小且调用序列单一，无法诱发 Type-3（运行时崩溃/段错误）。

本升级旨在将系统从“防御性验收”转向“攻击性挖掘”，实现对四型缺陷的全量覆盖。

## 变更内容
- **引入攻击性变异算子 (Agent 2)**：新增“契约违约算子”（故意越界、非法类型）和“时序混沌算子”（乱序 API 调用）。
- **执行层“放行模式” (Agent 3)**：**BREAKING** 移除强制拦截逻辑，改为“透传+观测”模式。明知请求非法也要打向数据库，并详细记录数据库的容错表现。
- **四型缺陷判定逻辑重构 (Agent 5)**：
    - 增加 **Type-1 判定**：当预期非法但数据库成功执行时触发。
    - 增加 **Type-2 判定**：当数据库报错信息为 `Unknown` 或 `Internal Error` 时触发。
- **极端压力注入 (Software Harness)**：支持生成万级维度的超大向量和百万级的 Top-K 请求，探索数据库内存管理极限。
- **语义精排重排序 (Reranker Node)**：在 Oracle 判定前引入 Cross-Encoder，减少由于向量检索原始偏差导致的 Type-4 假阳性。

## 影响
- 受影响 specs: `upgrade-harness-v3.3`, `refactor-harness-v3.4`.
- 受影响代码: `src/agents/agent2_test_generator.py`, `src/agents/agent3_executor.py`, `src/agents/agent5_diagnoser.py`, `src/graph.py`.

## ADDED Requirements
### 需求：非法输入渗透测试
Agent 2 必须生成至少 20% 的违反 L1 契约的“攻击性用例”。

#### 场景：Type-1 挖掘成功
- **WHEN** Agent 2 生成了一个维度为 -1 的向量插入请求
- **AND** Agent 3 将其发送至 Milvus
- **AND** Milvus 返回 `Success`
- **THEN** Agent 5 必须将其标记为 **Type-1 (Illegal Operation Succeeded)**。

### 需求：语义重排序网关
系统 SHALL 在 Agent 4 判定前，对 Top-K 结果进行基于 Cross-Encoder 的重评分。

## MODIFIED Requirements
### 需求：执行器角色转变
Agent 3 不再担任“过滤器”角色，而是转变为“攻击记录员”，必须允许非法 payload 渗透至数据库。

## REMOVED Requirements
### 需求：执行前 L1 强制拦截
**原因**：拦截行为掩盖了数据库本身的漏洞。
**迁移**：拦截逻辑迁移至诊断层（Agent 5）作为判定依据。
