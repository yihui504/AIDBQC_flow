# AI-DB-QC

基于 LLM Agent 的向量数据库自动化质量检测系统

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PydanticAI](https://img.shields.io/badge/PydanticAI-Agent-green.svg)](https://ai.pydantic.dev/)
[![DeepSeek V4](https://img.shields.io/badge/DeepSeek-V4_Pro/Flash-orange.svg)](https://api.deepseek.com/)
[![Version](https://img.shields.io/badge/Version-v6.0-brightgreen.svg)](#v60-验证结果)

---

## 项目简介

**AI-DB-QC** (AI-driven Database Quality Control) 是一套基于 PydanticAI Agent 的向量数据库自动化质量检测系统。系统采用 **TestRuntime + PolicyEngine + EventBus** 三层架构，通过自主编排的 Agent 自动完成以下全流程工作：

1. **文档获取与源码分析** -- 搜索目标数据库官方文档，克隆源码仓库进行静态分析
2. **契约提取与验证** -- 从文档和源码中提取三层契约（L1 API / L2 语义 / L3 应用），支持三源交叉验证（文档+源码+行为）
3. **多库适配执行** -- 通过 VectorDBBase 抽象层统一操作 Milvus/Qdrant/Weaviate/Pgvector 四种向量数据库
4. **策略门控** -- PolicyEngine 组合 FocusAdvisor + PermissionEvaluator + SafetyGuard 三层策略，控制工具执行权限
5. **缺陷分类与验证** -- 四型决策树分类 + FP过滤器 + ANN近似白名单 + Docker沙箱MRE复现验证
6. **Issue 生成** -- 输出标准化的 BugIssue，含证据链、MRE代码、验证状态

---

## 架构总览

### 三层架构

```
┌─────────────────────────────────────────────────────┐
│                    TestRuntime                       │
│  主循环: 多轮迭代 + FocusMode 状态机 + 交互式控制     │
│  Agent: PydanticAI Agent + SYSTEM_PROMPT + 27 Tools  │
│  恢复: RecoveryStrategy (6类错误 + 指数退避)          │
└──────────────┬──────────────────┬────────────────────┘
               │                  │
       ┌───────▼───────┐  ┌──────▼────────┐
       │  PolicyEngine  │  │   EventBus    │
       │  FocusAdvisor  │  │  12种事件类型  │
       │  Permission    │  │  发布/订阅     │
       │  SafetyGuard   │  │  去重/缓冲     │
       └───────────────┘  └───────────────┘
```

### Agent 工具调用流

```
用户输入 → TestRuntime.run() → PydanticAI Agent 循环
                                    ↓
                    Agent 自主选择工具调用:
                    ┌─ db/* (9个) ── 数据库 CRUD + 健康检查
                    ├─ doc/* (2个) ── 文档搜索 + 引用验证
                    ├─ source/* (3个) ─ 源码克隆/搜索/分析
                    ├─ code/* (2个) ── Docker沙箱MRE执行
                    ├─ verify/* (4个) ─ 契约验证 + 缺陷验证 + FP过滤
                    └─ flow/* (7个) ── 焦点切换 + 缺陷记录 + 反馈生成
                                    ↓
                    PolicyEngine.check_tool_execution()
                    → FocusAdvisor: 工具是否在当前焦点内?
                    → PermissionEvaluator: 权限是否允许?
                    → SafetyGuard: 参数是否安全?
                                    ↓
                    EventBus.emit() → 事件日志 + Session持久化
```

### FocusMode 状态机

Agent 在五阶段焦点模式间切换，每个工具声明自己适用的焦点模式：

| 焦点模式 | 阶段 | 典型工具 |
|----------|------|----------|
| `understanding` | 理解文档与源码 | doc_search, source_analyze_module, db_list_collections |
| `generation` | 生成测试用例 | (Agent 自主推理) |
| `execution` | 执行数据库操作 | db_create_collection, db_insert_data, db_search |
| `verification` | 验证契约与缺陷 | contract_tri_validate, verify_defect |
| `reporting` | 生成报告 | record_defect, generate_feedback |

---

## 核心特性

### 四型缺陷分类 (Four-Type Classification)

| 类型 | 名称 | 判定条件 | 典型场景 |
|------|------|----------|----------|
| **Type-1** | 非法成功 (Illegal Success) | 契约违规但操作成功 | 非法维度请求绕过校验 |
| **Type-2** | 诊断不足 (Poor Diagnostics) | 操作失败但错误信息模糊 | 返回不充分的错误描述 |
| **Type-2.PF** | 前置条件失败 (Precondition Failure) | 前置条件未满足导致失败 | Collection不存在 |
| **Type-4** | 语义违规 (Semantic Violation) | 操作成功但结果不符合语义预期 | 搜索结果排序不合理 |

### 多库适配器 (Multi-DB Adapters)

VectorDBBase 定义 13 个抽象方法，4 个适配器实现：

| 适配器 | 目标数据库 | SDK |
|--------|-----------|-----|
| MilvusAdapter | Milvus | pymilvus |
| PgvectorAdapter | PostgreSQL + pgvector | asyncpg + pgvector |
| QdrantAdapter | Qdrant | qdrant-client |
| WeaviateAdapter | Weaviate | weaviate-client |

AdapterFactory 根据 `DBInstanceConfig.type` 自动创建对应适配器实例。

### 策略引擎 (PolicyEngine)

组合三层策略对每次工具调用进行门控：

| 层 | 组件 | 职责 |
|----|------|------|
| 焦点层 | FocusAdvisor | 检查工具是否在当前 FocusMode 允许范围内 |
| 权限层 | PermissionEvaluator | 按 safety_level (cautious/aggressive) 评估工具权限 |
| 安全层 | SafetyGuard | 检查参数安全性（路径穿越、注入等） |

### 事件系统 (EventBus)

12 种事件类型覆盖完整生命周期：

`ROUND_STARTED` / `ROUND_COMPLETED` / `FOCUS_CHANGED` / `TOOL_INVOKED` / `TOOL_COMPLETED` / `DEFECT_DISCOVERED` / `DEFECT_VERIFIED` / `ADAPTER_SELECTED` / `COMPACTION_APPLIED` / `RECOVERY_ATTEMPTED` / `SESSION_SAVED` / `SANDBOX_EXECUTED`

### 工具输出压缩 (ToolOutputCompressor)

每个工具通过 `@tool_meta` 装饰器声明压缩策略，8 种压缩策略自动缩减 LLM 上下文占用。

### 恢复策略 (RecoveryStrategy)

6 类错误自动分类与恢复：API超时 / 工具执行失败 / 数据库连接丢失 / 上下文溢出 / 策略阻断 / 速率限制，支持指数退避重试。

---

## 快速开始

### 前置要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.12 | 需要 typing 新特性 |
| Docker | >= 20.10 | 用于运行目标数据库实例 + MRE沙箱 |
| DeepSeek API Key | -- | 必填 |

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd AIDBQC_flow

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 4. 设置 API Key
set DEEPSEEK_API_KEY=sk-xxx          # Windows
# export DEEPSEEK_API_KEY=sk-xxx     # Linux/macOS
```

运行时配置文件为 `config.yaml`，支持环境变量 `AI_DB_QC_` 前缀覆盖。

### 运行

```bash
# 交互模式 (默认)
python -m src.main --target milvus --version 2.6.12

# 非交互模式
python -m src.main --target milvus --non-interactive

# 指定模型
python -m src.main --model deepseek-reasoner
```

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--target` | `milvus` | 目标数据库: milvus/qdrant/weaviate/pgvector |
| `--version` | `2.6.12` | 目标数据库版本 |
| `--max-rounds` | `4` | 最大测试轮次 |
| `--config` | `config.yaml` | 配置文件路径 |
| `--safety-level` | `cautious` | 安全级别: cautious/aggressive |
| `--model` | `deepseek-chat` | 模型: deepseek-chat/deepseek-reasoner |
| `--non-interactive` | `false` | 非交互模式运行 |

### 交互命令

| 命令 | 缩写 | 说明 |
|------|------|------|
| `pause` | `p` | 暂停当前轮次 |
| `resume` | `r` | 恢复执行 |
| `status` | `s` | 查看当前状态 |
| `skip` | -- | 跳过当前轮次 |
| `stop` | -- | 终止运行 |
| `focus <mode>` | -- | 切换焦点模式 |

---

## v6.0 验证结果

### v6.0 最小验收: 通过

v6.0 最小验收目标已通过，真实数据库 E2E 测试发现 **4 个真实缺陷**。

### 测试概况

| 指标 | 值 |
|------|-----|
| 版本 | v6.0 |
| 单元测试 | 94 个 (6 个文件) |
| 集成测试 | 8 个 (E2E Pipeline) |
| 真实数据库 E2E 测试 | 2 套: Milvus 11 个 + Qdrant 11 个 |
| 系统 E2E 测试 | 1 个 |
| 真实缺陷发现 | **4 个** (>=2 要求，验收通过) |
| 项目完成度 | 90% |

### 真实缺陷验证

通过连接真实 Milvus 和 Qdrant 数据库执行完整测试流程，发现 4 个真实缺陷，具备完整证据链(执行日志 + 数据库状态 + MRE 代码)，可生成格式正确的 BugIssue。

### v4.4 历史验证结果 (参考)

| 指标 | 值 |
|------|-----|
| Run ID | `run_0a79d4f2` |
| 版本 | v4.4 |
| 退出码 | 0 (成功) |
| 总耗时 | ~15.5 分钟 |
| 迭代轮次 | 4 轮 |
| 产出 Issue 数 | **12 个** |

v4.4 关键修复: L2 门控状态传播 Bug -- v4.3 中所有缺陷被误判为 Type-2.PF (100% 伪阳性)，根因为 `state.data_inserted` 和 `state.current_collection` 字段未正确写入 WorkflowState，v4.4 修复后出现合理的 Type-2 与 Type-4 分布。

---

## 项目结构

```
src/
├── __init__.py
├── config.py              # AppConfig (Pydantic, YAML+环境变量)
├── main.py                # CLI入口 + 交互式命令循环
├── ann_whitelist.py       # ANN近似白名单检查
│
├── models/                # 数据模型 (6文件)
│   ├── contract.py        # ContractSet (L1/L2/L3 + 置信度)
│   ├── defect.py          # DefectReport + EvidenceChain
│   ├── issue.py           # BugIssue (GitHub Issue格式)
│   ├── probe.py           # ProbeResult
│   ├── state.py           # UnifiedState + FocusMode + tool_meta
│   └── deepseek_provider.py # DeepSeek ModelSettings
│
├── adapters/              # 向量数据库适配器 (6文件)
│   ├── base.py            # VectorDBBase (ABC, 13个抽象方法)
│   ├── factory.py         # AdapterFactory
│   ├── milvus.py          # MilvusAdapter
│   ├── pgvector.py        # PgvectorAdapter
│   ├── qdrant.py          # QdrantAdapter
│   └── weaviate.py        # WeaviateAdapter
│
├── events/                # 事件系统 (3文件)
│   ├── types.py           # TestEventType (12种事件)
│   └── bus.py             # EventBus (发布/订阅/去重/缓冲)
│
├── policy/                # 策略引擎 (5文件)
│   ├── engine.py          # PolicyEngine (组合三层策略)
│   ├── focus.py           # FocusAdvisor
│   ├── permission.py      # PermissionEvaluator
│   └── safety.py          # SafetyGuard
│
├── runtime/               # 运行时 (4文件)
│   ├── agent.py           # create_agent + SYSTEM_PROMPT + ModelFallback
│   ├── loop.py            # TestRuntime (主循环)
│   └── recovery.py        # RecoveryStrategy (6类错误+指数退避)
│
├── session/               # 会话持久化 (2文件)
│   └── store.py           # SessionStore (JSONL+JSON快照+fork)
│
├── tools/                 # 工具函数 (14文件, 27个工具)
│   ├── __init__.py        # collect_all_tools + create_registry
│   ├── registry.py        # ToolRegistry
│   ├── compression.py     # ToolOutputCompressor (8种压缩策略)
│   ├── event_bus_holder.py # 全局EventBus单例
│   ├── db/                # 9个数据库操作工具
│   ├── doc/               # 2个文档工具 (search + validate)
│   ├── source/            # 3个源码分析工具 (clone/search/analyze)
│   ├── code/              # 2个代码沙箱工具 (Docker执行)
│   ├── verify/            # 4个验证工具 (contract_validate + verify_defect + FP过滤)
│   └── flow/              # 7个流程控制工具 (focus/defect/feedback)
│
└── ui/                    # 终端UI (3文件)
    ├── display.py         # AgentDisplay (Rich终端UI)
    └── input_handler.py   # AsyncInputHandler

tests/
├── unit/                  # 6个单元测试文件 (94个测试方法)
│   ├── test_unified_state.py
│   ├── test_tool_registry.py
│   ├── test_session_store.py
│   ├── test_recovery.py
│   ├── test_policy_engine.py
│   └── test_event_bus.py
├── integration/           # 集成测试
│   ├── test_e2e_pipeline.py      # 8个E2E集成测试
│   ├── test_real_milvus.py       # Milvus真实E2E测试 (11个)
│   ├── test_real_qdrant.py       # Qdrant真实E2E测试 (11个)
│   └── test_system_e2e.py        # 系统E2E测试 (1个)
```

---

## 配置参考

### LLM 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | (必填) |
| `llm.provider` | LLM 提供商 | `deepseek` |
| `llm.pro_model` | Pro 模型 | `deepseek-v4-pro` |
| `llm.flash_model` | Flash 模型 (降级用) | `deepseek-v4-flash` |
| `llm.thinking_mode` | 启用 Think 模式 | `true` |
| `llm.reasoning_effort` | 推理强度 | `high` |

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `database.default` | 默认数据库类型 | `milvus` |
| `database.target_version` | 目标版本 | `2.6.12` |
| `database.instances` | 多实例配置列表 | `[]` |

### Harness 配置

| 键路径 | 说明 | 默认值 |
|--------|------|--------|
| `harness.max_rounds` | 最大迭代轮次 | `4` |
| `harness.max_token_budget` | 最大 Token 预算 | `2000000` |
| `harness.max_consecutive_failures` | 连续失败阈值 | `5` |
| `harness.safety_level` | 安全级别 | `cautious` |

---

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **Agent 框架** | PydanticAI | Agent 编排、工具注册、RunContext 依赖注入 |
| **LLM** | DeepSeek V4 Pro/Flash | 语义理解、测试生成、缺陷分类 |
| **向量数据库** | pymilvus / qdrant-client / weaviate-client / asyncpg+pgvector | 目标被测数据库 |
| **数据模型** | Pydantic v2 | 类型安全模型、配置管理 |
| **配置管理** | Pydantic Settings + PyYAML | YAML配置 + 环境变量覆盖 |
| **终端UI** | Rich | AgentDisplay 终端渲染 |
| **容器化** | Docker | 数据库实例 + MRE沙箱 |
| **测试框架** | pytest | 单元测试 + 集成测试 |

---

## 开发进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 核心架构 (Runtime/Policy/EventBus) | 已完成 | TestRuntime + PolicyEngine + EventBus |
| 27个工具函数 | 已完成 | DB 9 + Doc 2 + Source 3 + Code 2 + Verify 4 + Flow 7 |
| 4个数据库适配器 | 已完成 | Milvus/Pgvector/Qdrant/Weaviate |
| 测试框架 | 已完成 | 94个单元测试 + 8个集成测试 + 真实DB E2E + 系统E2E |
| CLI + 交互式UI | 已完成 | argparse + Rich + asyncio |
| v6.0最小验收 | 已通过 | 真实Milvus+Qdrant E2E，发现4个真实缺陷 |
| DeepSeek V4 Think模式验证 | 待完成 | reasoning_effort 参数调优 |
| Docker Compose 3套数据库环境 | 待完成 | Milvus/Qdrant/Pgvector 编排 |

---

## 链接与参考

| 文档 | 说明 |
|------|------|
| [src/config.py](src/config.py) | 配置管理系统 (AppConfig + LLMConfig + MultiDBConfig) |
| [src/models/state.py](src/models/state.py) | UnifiedState + FocusMode 状态模型 |
| [src/runtime/loop.py](src/runtime/loop.py) | TestRuntime 主循环 |
| [src/runtime/agent.py](src/runtime/agent.py) | PydanticAI Agent 创建 + ModelFallback |
| [src/adapters/base.py](src/adapters/base.py) | VectorDBBase 抽象接口 (13个方法) |
| [src/policy/engine.py](src/policy/engine.py) | PolicyEngine 三层策略组合 |
| [src/events/bus.py](src/events/bus.py) | EventBus 发布/订阅系统 |
| [src/tools/__init__.py](src/tools/__init__.py) | 27个工具注册入口 |

---

## 许可证

本项目仅供学习与研究使用。
