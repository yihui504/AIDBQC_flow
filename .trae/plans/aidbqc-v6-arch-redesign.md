# Plan: AIDBQC v6.0 Architecture Redesign (v3 - Code Review 修订版)

## Overview
基于16轮深度访谈规格(模糊度4%)、对抗性审查、以及4轮严格Code Review(50个问题修复)，将AIDBQC系统从v5.0重构为6模块原则驱动架构。支持4库深度bug挖掘，焦点引导替代阶段约束，DeepSeek V4(1M上下文)驱动，Docker沙箱隔离执行。

## 修订记录
- v1: 初始计划(11步)
- v2: 根据对抗性审查修订——增加Step 0前置验证、解决循环依赖、拆分God Step、增加配置/提示词/Docker基础设施步骤、量化退出标准
- v3: 根据4轮Code Review(50个问题)修订——补全占位符工具实现、增加单元测试要求、修复架构缺陷(out_of_focus失效/adapter初始化/版本兼容)、增加恢复策略/DeepSeek V4集成/Docker基础设施的细化任务

## v3 修订要点(基于Code Review发现)
1. **Focus Mode策略从"建议"改为"引导+阻止"**: v2计划说"out_of_focus不拒绝"，但Code Review发现这导致策略形同虚设。v3改为out_of_focus阻止执行，通过SkipToolExecution通知Agent
2. **11个占位符工具必须实现**: v2计划只要求"迁移"，但Code Review发现11/26个工具是纯占位符，系统无法执行任何实际测试
3. **单元测试从"建议"升级为"必须"**: v2计划每个Step有测试要求但无量化。v3要求核心模块测试覆盖率>80%
4. **适配器延迟初始化**: Code Review发现4个适配器中3个在构造时立即连接，服务器不可达时应用崩溃
5. **PydanticAI版本兼容**: Code Review发现SkipToolExecution/Hooks可能不存在于当前版本
6. **Docker沙箱超时语义**: Code Review发现container.wait(timeout=)是HTTP超时不是执行超时
7. **create_collection不应隐式删除**: Code Review发现静默删除导致数据丢失
8. **PolicyEngine必须集成到工具调用链**: Code Review发现检查结果从未被使用
9. **agent.run()返回值必须使用**: Code Review发现Agent推理结果全部丢失
10. **恢复策略从"可选"升级为"必须"**: Code Review发现任何错误都导致Agent直接失败

## v4 修订要点(2026-05-07 代码全面扫描更新)
基于对src/目录全部源代码和tests/目录全部测试文件的全面扫描，更新各Step的实际完成状态。**重大发现**：v3计划中标注为"占位符"的9个工具函数已全部实现，恢复策略和用户交互已完成，6个核心模块的单元测试已编写(93个测试方法)，集成测试已编写(8个端到端测试)。

1. **Step 5 工具迁移: 58% → ✅ 100%** — 9个"占位符"工具(doc_search/doc_validate_reference/source_clone_repo/source_search/source_read/source_analyze_module/contract_validate_source/contract_validate_behavior/contract_tri_validate)已全部实现
2. **Step 8c 恢复策略+用户交互: 40% → ✅ 95%** — RecoveryStrategy已完整实现(129行，6类错误分类+指数退避)，用户交互已完整实现(main.py中pause/resume/focus/skip/stop/status)
3. **Step 4a EventBus: 85% → ✅ 95%** — 单元测试已编写(10个测试方法)
4. **Step 4b PolicyEngine: 90% → ✅ 95%** — 单元测试已编写(15个测试方法)
5. **Step 6 SessionStore: 85% → ✅ 95%** — 单元测试已编写(12个测试方法)，fork已实现
6. **Step 10 假阳性过滤: 80% → ✅ 95%** — FalsePositiveFilter完整实现(139行)
7. **Step 11 集成测试+CLI+UI: 50% → ✅ 85%** — CLI完整(--config/--model/--non-interactive)，UI完整(display.py 175行+input_handler.py 96行)，8个端到端集成测试
8. **Step 12 单元测试: 0% → ✅ 75%** — 6个核心模块单元测试已编写(93个测试方法)，但DBAdapter mock测试和DockerSandbox测试仍缺
9. **Step 9 DeepSeek V4: 30% → ⚠️ 50%** — ModelFallback降级逻辑已实现，但Think模式验证和1M上下文配置仍待完成

## v5 修订要点(2026-05-07 Deep Interview决策)
基于4轮Deep Interview(模糊度从100%降至18%)，明确v6.0最小验收版本的范围和优先级：

1. **最小验收目标聚焦**: 仅"真实数据库E2E测试"为必须项，其余7项未完成工作全部推迟
2. **E2E范围**: Milvus + Qdrant（不做Pgvector/Weaviate的真实E2E）
3. **验收标准**: 系统发现≥2个真实缺陷（任意类型，不限制Type-4）
4. **推迟项**: DeepSeek Think模式验证、DBAdapter测试、DockerSandbox测试、工具函数测试、模块配置化、EventBus并发安全、统一Docker Compose
5. **新增Step 13**: 真实数据库E2E测试（Milvus+Qdrant），作为v6.0最小验收的最终门控

## Dependency Graph (v5更新)
```
Step 0: 前置验证 (DeepSeek V4 + PydanticAI + Docker) [⚠️ 60%]
          ↓
Step 1: 项目骨架 + v4.x清理 + AppConfig多库重构 + Bug修复 [✅ 95%]
          ↓
Step 2: 统一状态模型 + FocusMode + @tool_meta [✅ 100%]
          ↓
Step 3: DBAdapter层 + Docker基础设施 [⚠️ 75%]
    ├── base.py + AdapterFactory [✅]
    ├── milvus.py [✅] ──┐
    ├── qdrant.py [✅]   │ 可并行
    ├── weaviate.py [✅] │
    └── pgvector.py [✅] ┘
    └── Docker Compose [❌ 缺3套] ← 推迟
          ↓
Step 4a: EventBus [✅ 95%]
Step 4b: PolicyEngine [✅ 95%]
          ↓
Step 5: ToolRegistry + 工具迁移 [✅ 100%]
          ↓
Step 6: SessionStore [✅ 95%]
          ↓
Step 7: Docker沙箱 [✅ 90%]
          ↓
Step 8a: Runtime骨架 + Agent配置 [✅ 95%]
Step 8b: 模块集成 [✅ 95%]
Step 8c: System Prompt + 恢复策略 + 用户交互 [✅ 95%]
          ↓
Step 9: DeepSeek V4集成 [⚠️ 50%] ← 推迟(Think模式验证)
          ↓
Step 10: 自动假阳性过滤 [✅ 95%]
          ↓
Step 11: 集成测试 + CLI入口 + UI适配 [✅ 85%]
          ↓
Step 12: 单元测试补全 [⚠️ 75%] ← 推迟(DBAdapter/工具测试)
          ↓
Step 13: ⭐ 真实数据库E2E测试 (Milvus+Qdrant) [✅ 100%] ← v6.0最小验收门控 ✅ 通过
          ↓
────── 以下为v6.1+推迟项 ──────
Step 14: [推迟] Docker Compose统一+Weaviate gRPC端口
Step 15: [推迟] DBAdapter mock单元测试
Step 16: [推迟] 工具函数单元测试
Step 17: [推迟] 模块配置化(恢复策略/FP阈值/压缩策略)
Step 18: [推迟] EventBus并发安全+MilvusAdapter Lock审查
Step 19: [推迟] DeepSeek Think模式端到端验证
Step 20: [推迟] Pgvector/Weaviate真实E2E测试
```

---

## Step 0: 前置验证

### Status: ⚠️ 部分(60%)

### 已完成
- [x] PydanticAI基本功能验证(已集成到runtime)
- [x] Docker沙箱基本功能验证(已实现DockerSandbox)

### 未完成
- [ ] DeepSeek V4 Think+工具调用同时使用的验证
- [ ] PydanticAI 1M上下文窗口验证
- [ ] PydanticAI Hooks/SkipToolExecution版本兼容性验证
- [ ] 验证结果记录到`.trae/validation-results.md`

### v3新增任务
- [ ] 验证当前安装的PydanticAI版本是否支持Hooks/SkipToolExecution
- [ ] 如果不支持，确认FallbackHooks降级方案是否工作
- [ ] 验证DeepSeek V4通过OpenAIProvider(base_url=...)方式是否正确传递thinking_mode参数

### Exit Criteria
- DeepSeek V4 Think+工具调用验证通过，或确定fallback(关闭Think模式)
- PydanticAI版本兼容性确认，Hooks降级方案可用
- 验证结果记录到`.trae/validation-results.md`

---

## Step 1: 项目骨架 + v4.x清理 + AppConfig多库重构 + Bug修复

### Status: ✅ 95%

### 已完成
- [x] 6模块目录结构创建
- [x] AppConfig重构为MultiDBConfig + target_version
- [x] pyproject.toml更新
- [x] tools/__init__.py清理旧版导入

### 未完成
- [ ] 删除v4.x遗留: `src/adapters/db_adapter.py`(旧版MilvusAdapter与新版同名冲突)
- [ ] 删除v4.x遗留: `src/tools/compression.py`中的ToolOutputCompressor从未被调用
- [ ] 删除v4.x遗留: `src/models/deepseek_provider.py`中的DeepSeekProvider类未被使用(回退到OpenAIProvider)

### v3新增任务
- [ ] 清理`src/adapters/db_adapter.py`或重命名为`_legacy_db_adapter.py`
- [ ] 确认`ToolOutputCompressor`是否需要集成到ToolRegistry，如不需要则标记为未来工作

---

## Step 2: 统一状态模型 + FocusMode + @tool_meta定义

### Status: ✅ 100%

### 已完成
- [x] UnifiedState模型(替代TestState+CoreState+WorkflowState)
- [x] FocusMode枚举
- [x] @tool_meta装饰器
- [x] computed_field替代__getattr__(Code Review C1修复)
- [x] defect_counter替代len()计数(Code Review NI2修复)
- [x] advance_round不再强制重置focus(Code Review NI5修复)
- [x] 单元测试 — test_unified_state.py(23个测试方法，175行)
- [x] 状态迁移方法 — from_legacy()已实现(3个测试验证)

---

## Step 3: DBAdapter层 + Docker基础设施

### Status: ⚠️ 75%

### 已完成
- [x] VectorDBBase抽象接口(13个方法)
- [x] MilvusAdapter(pymilvus MilvusClient实现)
- [x] QdrantAdapter(qdrant-client实现，延迟初始化)
- [x] WeaviateAdapter(weaviate-client实现，延迟初始化)
- [x] PgvectorAdapter(asyncpg+pgvector实现，SQL注入防护)
- [x] AdapterFactory
- [x] create_collection不再隐式删除(Code Review C5修复)
- [x] 4个适配器统一延迟初始化模式(Code Review NC3修复)
- [x] QdrantAdapter.query使用JSON filter解析(Code Review I7修复)
- [x] QdrantAdapter.delete兼容UUID(Code Review NI8修复)
- [x] WeaviateAdapter.query使用Filter API(Code Review NI7修复)
- [x] WeaviateAdapter.insert不再修改传入data(Code Review I9修复)

### 未完成
- [ ] Docker Compose配置:
  - [ ] docker-compose.qdrant.yml
  - [ ] docker-compose.weaviate.yml
  - [ ] docker-compose.pgvector.yml
  - [ ] docker-compose.all.yml
- [ ] 适配器接口测试(mock)
- [ ] Milvus集成测试(需实例)

### v3新增任务
- [ ] 创建3套缺失的Docker Compose配置
- [ ] 为每个适配器编写mock测试(验证接口一致性)
- [ ] 验证MilvusAdapter在真实Milvus实例上的集成

---

## Step 4a: EventBus

### Status: ✅ 95%

### 已完成
- [x] TestEventType扩展(含FOCUS_CHANGED等)
- [x] EventBus(发射/订阅/去重/缓冲)
- [x] 事件去重(MD5 hash + 时间窗口)
- [x] 单元测试 — test_event_bus.py(10个测试方法，126行)

### 未完成
- [ ] threading.Lock→asyncio.Lock迁移(当前在async环境中可能阻塞事件循环)

---

## Step 4b: PolicyEngine

### Status: ✅ 95%

### 已完成
- [x] FocusAdvisor(焦点建议+out_of_focus判断)
- [x] PermissionEvaluator(权限评估+cautious模式WRITE阻止)
- [x] SafetyGuard(危险操作检测，已移除DROP误杀)
- [x] out_of_focus纳入allowed判断(Code Review QC1修复)
- [x] EXECUTE权限在cautious模式允许(Code Review NI1修复)
- [x] PolicyEngine通过Hooks集成到工具调用链(Code Review RI1修复)
- [x] 单元测试 — test_policy_engine.py(15个测试方法，104行)

### 未完成
- [ ] SafetyGuard嵌套结构检测(当前只检查args顶层值)

---

## Step 5: ToolRegistry + 工具迁移

### Status: ✅ 100%

### 已完成(5a: 核心)
- [x] ToolRegistry(收集/注册/焦点建议)
- [x] _has_run_context基于类型注解+字符串兜底(Code Review RC2修复)
- [x] ToolOutputCompressor定义+集成到ToolRegistry(169行，8种压缩策略)

### 已完成(5b: DB工具)
- [x] 13个DB工具迁移+@tool_meta
- [x] DB工具权限从write改为execute(Code Review RI7修复)
- [x] adapter_holder全局变量模式

### 已完成(5c: 非DB工具) — ✅ 全部实现，无占位符
- [x] code_run_mre(Docker沙箱+延迟初始化+超时修复)
- [x] update_focus(焦点切换)
- [x] record_defect(完整实现，创建DefectReport+BugIssue)
- [x] generate_feedback(完整实现，生成测试策略)
- [x] verify_defect(完整实现，更新已有BugIssue而非创建重复)
- [x] doc_search — ✅ 已实现(tools/doc/__init__.py，125行，JSONL文档加载+关键词搜索评分)
- [x] doc_validate_reference — ✅ 已实现(tools/doc/__init__.py，URL验证)
- [x] source_clone_repo — ✅ 已实现(tools/source/__init__.py，217行，git clone/pull)
- [x] source_search — ✅ 已实现(tools/source/__init__.py，正则搜索)
- [x] source_read — ✅ 已实现(tools/source/__init__.py，文件读取+路径遍历防护)
- [x] source_analyze_module — ✅ 已实现(tools/source/__init__.py，模块导出分析)
- [x] contract_validate_source — ✅ 已实现(tools/verify/__init__.py，L3源码级合约验证)
- [x] contract_validate_behavior — ✅ 已实现(tools/verify/__init__.py，L2行为级合约验证)
- [x] contract_tri_validate — ✅ 已实现(tools/verify/__init__.py，L1+L2+L3三方交叉验证)

### 单元测试
- [x] test_tool_registry.py(13个测试方法，108行)

### Exit Criteria
- [x] 所有27个工具非占位符实现
- [x] PydanticAI工具注册桥接工作
- [x] 工具注册代码<100行

---

## Step 6: SessionStore

### Status: ✅ 95%

### 已完成
- [x] JSONL追加写入+最新快照恢复
- [x] 状态快照(UnifiedState.model_dump_json)
- [x] compact_state后调用_save_snapshot(Code Review NM2修复)
- [x] 会话fork(深拷贝用于分支)
- [x] 单元测试 — test_session_store.py(12个测试方法，127行)

### 未完成
- [ ] 压缩策略可配置化(当前硬编码截断阈值)

---

## Step 7: Docker沙箱

### Status: ✅ 90%

### 已完成
- [x] DockerSandbox类(延迟初始化+优雅降级)
- [x] 超时使用threading.Timer+container.kill()(Code Review C4修复)
- [x] exit_code 137辅助判断超时(Code Review NC2修复)
- [x] 容器执行后自动清理(remove force)
- [x] 模块级初始化改为延迟初始化(Code Review C3修复)
- [x] 镜像构建
- [x] code_run_mre集成

### 未完成
- [ ] Docker Compose配置(3套数据库环境)
- [ ] 沙箱资源限制(CPU/内存)
- [ ] 单元测试

---

## Step 8a: Runtime骨架 + Agent配置

### Status: ✅ 95%

### 已完成
- [x] PydanticAI Agent配置(OpenAIProvider+DeepSeek base_url)
- [x] 基础对话循环
- [x] System Prompt(焦点引导+4库+R1-R7+ANN警告)
- [x] 动态System Prompt注入(焦点/轮次/缺陷/合约)
- [x] _attach_policy_hooks(before/after/error三钩子)
- [x] PolicyEngine集成到Agent Hooks

### 未完成
- [ ] Agent重试策略配置化

---

## Step 8b: 模块集成

### Status: ✅ 95%

### 已完成
- [x] PolicyEngine集成(通过Hooks+SkipToolExecution)
- [x] ToolRegistry集成(所有工具注册到Agent)
- [x] EventBus集成(关键操作发射事件)
- [x] SessionStore集成(每轮结束保存状态)
- [x] DBAdapter集成(AdapterFactory+adapter_holder)
- [x] instances为空时创建默认实例(Code Review QC2修复)
- [x] PydanticAI版本兼容(FallbackHooks降级)(Code Review QC3修复)
- [x] agent.run()返回值记录到execution_log(Code Review QI3修复)
- [x] _build_round_prompt增强上下文(Code Review NI4修复)
- [x] 事件发射到UI
- [x] 适配器重置(recovery触发)

### 未完成
- [ ] 多数据库并行测试模式

---

## Step 8c: System Prompt + 恢复策略 + 用户交互

### Status: ✅ 95%

### 已完成
- [x] SYSTEM_PROMPT(焦点引导+4库+R1-R7+ANN警告)
- [x] 动态System Prompt注入(焦点/轮次/缺陷/合约)
- [x] RecoveryStrategy — 6类错误分类(API_TIMEOUT/DB_CONNECTION_LOST/RATE_LIMITED/CONTEXT_OVERFLOW/POLICY_BLOCKED/TOOL_EXECUTION_FAILURE/UNKNOWN)
- [x] 指数退避重试(1s/2s/4s)
- [x] 适配器重置(DB_CONNECTION_LOST时触发)
- [x] 上下文压缩(CONTEXT_OVERFLOW时触发compact_fn)
- [x] 用户交互 — pause/resume/focus/skip/stop/status命令
- [x] AsyncInputHandler(异步输入处理，96行)
- [x] 单元测试 — test_recovery.py(20个测试方法，164行)

### 未完成
- [ ] 恢复策略可配置化(当前硬编码重试次数和退避时间)
- [ ] 用户命令持久化(跨会话恢复)

---

## Step 9: DeepSeek V4集成

### Status: ⚠️ 50%

### 已完成
- [x] DeepSeekProvider类定义(继承Provider[AsyncOpenAI])
- [x] create_pro_model/create_flash_model工厂函数
- [x] ModelSettings配置(extra_body传递thinking参数)
- [x] ModelFallback降级逻辑(deepseek-chat→deepseek-reasoner→gemini-2.0-flash)
- [x] deepseek_provider.py(ModelSettings构建，含thinking mode配置)
- [x] is_fallback_eligible判断

### 未完成
- [ ] **DeepSeekProvider实际使用**: 当前回退到OpenAIProvider(Code Review RC1修复确认)
- [ ] **Think模式端到端验证**: DeepSeek-R1的thinking输出解析
- [ ] **V4 Flash fallback**: 成本更低速度更快的备选模型
- [ ] **1M上下文窗口配置**: max_tokens设置
- [ ] 多模型并发测试
- [ ] 模型降级策略的A/B测试
- [ ] 单元测试

### v3新增任务
- [ ] 验证OpenAIProvider(base_url=DeepSeek_API_URL)方式是否正确传递thinking_mode
- [ ] 如果OpenAIProvider不支持extra_body，需要自定义Provider子类
- [ ] 实现V4 Pro→V4 Flash自动降级(当Pro超时或限流时)
- [ ] 配置1M上下文窗口(max_input_tokens=1000000)

---

## Step 10: 自动假阳性过滤

### Status: ✅ 95%

### 已完成
- [x] 4层过滤流水线(MRE检查→证据评分→ANN过滤→开发者评审)
- [x] ANN recall从issue文本提取(Code Review I3修复)
- [x] FalsePositiveFilter类(139行，MRE可复现性检查+证据评分+ANN预期行为判定+开发者审查评分)
- [x] ANNWhitelistChecker
- [x] FilterResult(通过/需审查/假阳性三级判定)

### 未完成
- [ ] FP阈值可配置化(当前硬编码)

---

## Step 11: 集成测试 + CLI入口 + UI适配

### Status: ✅ 85%

### 已完成
- [x] CLI入口 — main.py(130行，--config/--model/--non-interactive参数)
- [x] 交互式命令循环 — run_interactive() + _read_commands()
- [x] UI — display.py(175行，AgentDisplay事件驱动显示) + input_handler.py(96行，AsyncInputHandler)
- [x] 集成测试 — test_e2e_pipeline.py(8个端到端测试，185行)
  - [x] full_pipeline_initialization
  - [x] event_bus_propagation
  - [x] policy_blocks_dangerous_tool
  - [x] recovery_on_connection_error
  - [x] flash_fallback_on_rate_limit
  - [x] defect_lifecycle
  - [x] session_persistence
  - [x] compressor_integration

### 未完成
- [ ] 真实数据库端到端测试(当前全部mock)
- [ ] 非交互模式完整流程验证
- [ ] UI焦点模式显示优化

---

## Step 12: 单元测试补全 + 验收标准验证

### Status: ⚠️ 75%

### 已完成
- [x] test_unified_state.py — 23个测试方法，175行
- [x] test_event_bus.py — 10个测试方法，126行
- [x] test_policy_engine.py — 15个测试方法，104行
- [x] test_recovery.py — 20个测试方法，164行
- [x] test_session_store.py — 12个测试方法，127行
- [x] test_tool_registry.py — 13个测试方法，108行
- [x] test_e2e_pipeline.py(集成) — 8个测试方法，185行

### 未完成
- [ ] DBAdapter mock测试(4个适配器的单元测试)
- [ ] DockerSandbox单元测试
- [ ] 工具函数单元测试(doc/source/verify/flow/code)
- [ ] 验收标准自动化验证脚本

---

## 下一步工作优先级(基于当前进度)

### P0: 最小可运行路径(让系统能跑起来)

| 优先级 | 工作项 | 对应Step | 依赖 |
|--------|--------|----------|------|
| P0-1 | 实现`doc_search`工具(非占位符) | Step 5c | 无 |
| P0-2 | 实现`source_clone_repo`+`source_read`工具 | Step 5c | 无 |
| P0-3 | 实现`contract_validate_*`工具 | Step 5c | doc_search |
| P0-4 | 创建3套Docker Compose配置 | Step 3 | 无 |
| P0-5 | 实现恢复策略(RecoveryStrategy) | Step 8c | 无 |
| P0-6 | 构建Docker沙箱镜像(Dockerfile) | Step 7 | 无 |

### P1: 让系统跑得稳

| 优先级 | 工作项 | 对应Step | 依赖 |
|--------|--------|----------|------|
| P1-1 | 核心模块单元测试 | Step 12 | 无 | ✅ 已完成(93个测试方法) |
| P1-2 | DeepSeek V4集成(Think模式+Flash fallback) | Step 9 | Step 0验证 | ⚠️ 50% → 推迟至v6.1 |
| P1-3 | 用户交互(pause/resume/focus/skip/stop/status) | Step 8c | 无 | ✅ 已完成 |
| P1-4 | UI适配v6.0 | Step 11 | 无 | ✅ 已完成 |

### P2: 让系统跑出质量

| 优先级 | 工作项 | 对应Step | 依赖 | 状态 |
|--------|--------|----------|------|------|
| P2-1 | 端到端集成测试 | Step 11 | P0全部 | ✅ 8个E2E测试已完成(mock) |
| P2-2 | 验收标准验证 | Step 12 | P0+P1 | ⚠️ 75% → 推迟至v6.1 |
| P2-3 | EventBus threading.Lock→asyncio.Lock | Step 4a | 无 | 推迟至v6.1 |
| P2-4 | ToolOutputCompressor集成到ToolRegistry | Step 5a | 无 | ✅ 已完成 |

### P3: ⭐ v6.0最小验收 (Deep Interview决策)

| 优先级 | 工作项 | 对应Step | 依赖 | 状态 |
|--------|--------|----------|------|------|
| **P3-1** | **真实数据库E2E测试 (Milvus+Qdrant)** | **Step 13** | **Step 0-11** | **✅ 100% — 发现4个真实缺陷，v6.0最小验收通过** |

### P4: v6.1+ 推迟项 (Deep Interview决策)

| 优先级 | 工作项 | 对应Step | 说明 |
|--------|--------|----------|------|
| P4-1 | Docker Compose统一+Weaviate gRPC端口 | Step 14 | 4个单独compose已够用 |
| P4-2 | DBAdapter mock单元测试 | Step 15 | ✅ 38个测试(Milvus 19+Qdrant 14+Factory 4+Base 1) |
| P4-3 | 工具函数单元测试 | Step 16 | ✅ 22个测试(Compressor 11+Config 9+CompressionConfig 2) |
| P4-4 | 模块配置化 | Step 17 | 恢复策略/FP阈值/压缩策略等7处硬编码 |
| P4-5 | EventBus并发安全+MilvusAdapter Lock审查 | Step 18 | EventBus无Lock，Milvus用threading.Lock合理 |
| P4-6 | DeepSeek Think模式端到端验证 | Step 19 | ✅ 通过！发现3个缺陷，改用ModelSettings(thinking=)原生API |
| P4-7 | Pgvector/Weaviate真实E2E测试 | Step 20 | 适配器有多个"Not supported"方法 |

---

## Step 13: ⭐ 真实数据库E2E测试 (Milvus+Qdrant) — v6.0最小验收门控

### Status: ✅ 100% — 通过

### 目标
在真实Milvus和Qdrant数据库上运行完整测试流程，发现≥2个真实缺陷（任意类型），证明系统的核心价值。

### 验收标准
- [x] 系统能连接真实Milvus数据库并执行完整测试流程（create→insert→search→delete）
- [x] 系统能连接真实Qdrant数据库并执行基本CRUD操作
- [x] 系统在真实数据库上运行多轮Fuzzing后，发现≥2个真实缺陷
- [x] 真实缺陷有完整的证据链（执行日志+数据库状态+MRE代码）
- [x] 真实缺陷能生成格式正确的BugIssue

### 实现结果

#### 13a: pytest基础设施 ✅
- [x] 添加 `@pytest.mark.integration` 和 `@pytest.mark.db_milvus` / `@pytest.mark.db_qdrant` 标记
- [x] 添加数据库可用性检测fixture（连接失败则skip）
- [x] 添加测试数据隔离fixture（唯一前缀collection名 + 测试后清理）
- [x] 在conftest.py中配置markers和默认跳过integration标记

#### 13b: Milvus真实E2E ✅
- [x] test_real_milvus.py: 11个Milvus E2E测试（CRUD全流程+错误注入+边界测试）
- [x] Milvus 2.6.11 Docker容器运行正常
- [x] 适配器E2E测试全部通过（23/23）

#### 13c: Qdrant真实E2E ✅
- [x] test_real_qdrant.py: 12个Qdrant E2E测试（CRUD全流程+错误注入+边界测试）
- [x] Qdrant Docker容器运行正常

#### 13d: 缺陷验证 ✅
- [x] 系统级E2E测试通过（test_system_e2e.py）
- [x] 发现4个真实缺陷（要求≥2）
- [x] 缺陷类型包含Type-3（Traditional Oracle）等
- [x] 缺陷有MRE代码和证据链

### 修复的Bug（E2E测试过程中发现并修复）
1. **MilvusAdapter死锁**: `threading.Lock`→`threading.RLock`（嵌套调用导致死锁）
2. **QdrantAdapter兼容性**: `info.vectors_count`→兼容不同版本客户端
3. **PydanticAI Hooks API**: `ToolDefinition`导入路径修正
4. **工具注册RunContext检测**: 字符串类型注解检测修复
5. **verify_defect issue_id bug**: `DefectReport`无`issue_id`属性→从`defect_id`派生
6. **record_defect severity/defect_type兼容性**: 添加模糊匹配和默认值
7. **DefectType枚举引用错误**: `TYPE1_ILLEGAL_SUCCESS`→`ILLEGAL_SUCCESS`
8. **TestEventType.ERROR_OCCURRED不存在**: 改为`RECOVERY_ATTEMPTED`

### Exit Criteria
- [x] Milvus适配器E2E测试全部通过
- [x] Qdrant适配器E2E测试全部通过
- [x] 发现4个真实缺陷（≥2要求）
- [x] 真实缺陷有MRE代码和证据链

---

## Step 14-20: v6.1+ 推迟项

> 以下工作项已通过Deep Interview确认为非v6.0最小验收必须项，推迟至v6.1+版本。

### Step 14: [推迟] Docker Compose统一+Weaviate gRPC端口
- 统一docker-compose.yml（一次性启动所有数据库）
- Weaviate添加gRPC端口50051映射
- config.yaml MultiDBConfig多库实例配置
- 统一启动/停止脚本

### Step 15: [推迟] DBAdapter mock单元测试
- 4个适配器各14个方法的mock测试
- AdapterFactory类型分发测试
- PgvectorAdapter._validate_table_name SQL注入测试
- MilvusAdapter threading.Lock vs 其他 asyncio.Lock 差异测试

### Step 16: [推迟] 工具函数单元测试
- doc/ 工具测试（doc_search评分逻辑、doc_validate_reference URL验证）
- source/ 工具测试（clone/pull、正则搜索、路径遍历防护、模块分析）
- verify/ 工具测试（三级合约验证、verify_defect、FalsePositiveFilter）
- flow/ 工具测试（焦点切换、缺陷记录、反馈生成）
- code/ 工具测试（DockerSandbox容器执行、超时控制）

### Step 17: [推迟] 模块配置化
- RecoveryStrategy: 7类错误的max_retries/base_delay/reset_adapter → AppConfig.recovery
- FalsePositiveFilter: fp_risk阈值/evidence阈值/4个权重 → AppConfig.fp_filter
- ANNWhitelistChecker: 6个recall_threshold → AppConfig.ann_thresholds
- CompressionConfig: max_chars/lines/line_chars → 接入AppConfig
- ModelFallback: max_consecutive/cooldown_threshold → AppConfig.llm.fallback_*
- EventBus: buffer_maxlen/dedup_window → AppConfig.events.*
- SafetyGuard: dangerous_patterns → AppConfig.safety.dangerous_patterns

### Step 18: [推迟] EventBus并发安全+MilvusAdapter Lock审查
- EventBus: emit()与on()/subscribe_global()的并发安全问题
- MilvusAdapter: threading.Lock在asyncio.to_thread场景下是正确选择，不需迁移
- 如需加锁，EventBus应使用asyncio.Lock，但需将emit()改为async，影响面大

### Step 19: [推迟] DeepSeek Think模式端到端验证
- flash fallback时传递thinking配置（loop.py:124-127应使用build_model_settings）
- 端到端验证：调用DeepSeek V4 API验证thinking输出
- reasoning_effort参数效果差异验证
- pydantic-ai OpenAIChatModel extra_body透传确认

### Step 20: [推迟] Pgvector/Weaviate真实E2E测试
- Pgvector: asyncpg连接池测试，SQL注入防护验证
- Weaviate: gRPC连接测试，多个"Not supported"方法验证
- 跨数据库差分测试（同一数据集在不同DB中的搜索结果差异）

### Code Review遗留项(非阻塞，可后续处理)

| 项目 | 来源 | 说明 |
|------|------|------|
| computed_field冗余字段 | R1-M1 | model_dump()输出中current_focus和current_stage同时存在 |
| EventBus threading.Lock | R1-M3 | 在async环境中可能阻塞事件循环 → 推迟至Step 18 |
| 11/26工具占位符 | R3-RM3 | ✅ 已全部实现 |
| dedup_window清理逻辑 | R4-QM3 | 2秒清理窗口可能过于激进 → 推迟至Step 17配置化 |
