# AI-DB-QC

基于 LLM Multi-Agent 的向量数据库自动化质量检测系统

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Pipeline-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Milvus](https://img.shields.io/badge/Milvus-v2.6.12-green.svg)](https://milvus.io/)
[![Version](https://img.shields.io/badge/Version-v4.5-brightgreen.svg)](#v45-验证结果)

---

## 项目简介

**AI-DB-QC** (AI-driven Database Quality Control) 是一套基于 LLM 多智能体 (Multi-Agent) 流水线的向量数据库自动化质量检测系统。系统以 **Milvus / Qdrant / Weaviate** 等向量数据库为检测目标，通过自主编排的 Agent 管道自动完成以下全流程工作：

1. **环境拉起与文档获取** -- 自动搜索、爬取目标数据库版本的官方文档，并通过 Docker Compose 部署测试实例
2. **契约分析与测试生成** -- 从文档和业务场景中提取三层契约（L1 API / L2 语义 / L3 应用），并据此生成多维测试用例（含对抗样本）
3. **双层门控执行拦截** -- 在测试执行前进行 L1 抽象合法性检查 + L2 运行时就绪性检查，拦截非法或未就绪请求
4. **语义预言机验证** -- 结合传统预言机（单调性/一致性）与 LLM 语义预言机对执行结果进行分层校验
5. **缺陷分类与诊断** -- 使用四型决策树将发现的缺陷归入 Type-1 / Type-2 / Type-2.PF / Type-3 / Type-4 五类体系
6. **验证去重与 Issue 生成** -- 对潜在 Bug 进行可复现性重放、MRE 提取、多维度相似度去重，最终输出标准化的 GitHub Issue

整个流水线支持**多轮自适应闭环迭代**：每轮测试结束后，缺陷诊断器会将薄弱点特征反馈给测试生成器，驱动下一轮用例的定向进化。

---

## 架构总览

### Agent 流水线

```
Agent0 (Recon)                                                    用户输入: "深度测试 Milvus/Qdrant/Weaviate"
    |                                                              |
    |  文档预处理 (缓存优先) + Docker 环境拉起                      |
    v                                                              v
Agent1 (Contract Analyst)                                         三层契约 (L1/L2/L3)
    |                                                              |
    |  契约回退填充 (MilvusContractDefaults)                       |
    v                                                              v
Agent2 (Test Generator)                                           测试用例集 (含对抗样本)
    |                                                              |
    |  基于上轮反馈的 Fuzzing 变异                                  |
    v                                                              v
Agent3 (Executor + Gate)                                          执行结果 + L1/L2 门控状态
    |                                                              |
    |  L1 抽象合法性 (Warning 模式)                                |
    |  L2 运行时就绪性 (Collection / Data)                         |
    v                                                              v
Reranker (Cross-Encoder)                                          重排序结果 (rerank_score)
    |                                                              |
    |  ms-marco-MiniLM-L-6-v2 语义重排序                           |
    v                                                              v
Agent4 (Oracle)                                                   预言机验证结果
    |                                                              |
    |  传统预言机 + LLM 语义预言机                                 |
    v                                                              v
Agent5 (Diagnoser + Classifier)                                   缺陷报告 (四型分类)
    |                                                              |
    |  Type-1/Type-2/Type-2.PF/Type-3/Type-4 决策树               |
    +-----> Agent6 (Verifier + Issue Generator)                   GitHub Issue 文件
    |          |                                                  |
    |          |  可复现性重放 / MRE 提取 / 相似度去重             |
    |          v                                                  |
    |      Reflection Loop                                        反思总结 -> 输出 Issue
    |                                                             |
    +--- Feedback --> Agent2 (下一轮迭代) -------------------------+
```

### 核心数据流

```
用户输入 → WorkflowState 初始化 → LangGraph StateGraph 编排
                                    ↓
                    条件路由 (conditional_edges):
                    - agent0_env_recon     (文档爬取 + 环境部署)
                    - agent1_contract_analyst (契约提取 + 回退填充)
                    - agent2_test_generator   (混合测试生成)
                    - agent3_executor         (L1/L2 双层门控执行)
                    - agent_reranker          (Cross-Encoder 重排序)
                    - agent4_oracle           (语义预言机校验)
                    - agent5_reflection       (四型分类 + 反馈生成)
                    - agent6_verifier         (验证去重 + Issue 生成)
                                    ↓
                        StateManager 持久化 (.trae/runs/run_xxx/)
```

---

## 核心特性

### 双层有效性模型 (L1 + L2 Dual-Layer Validity)

Agent3 (`agent3_executor.py`) 实现了严格的双层门控机制，在测试执行前对每个请求进行两次合法性检查：

| 层级 | 名称 | 检查内容 | 行为模式 |
|------|------|----------|----------|
| **L1** | 抽象合法性 (Abstract Legality) | `dimension` 范围、`metric_type` 合法性、`top_k` 上限 | **Warning 模式** -- 记录违规但不阻断，允许捕获 Type-1 缺陷 |
| **L2** | 运行时就绪性 (Runtime Readiness) | Collection 是否存在、数据是否已注入、Index 是否加载 | **硬阻断** -- 未就绪直接标记为 Type-2.PF |

L2 门控通过维护 `state.current_collection` 和 `state.data_inserted` 两个 WorkflowState 字段实现状态传播，这是区分 **Type-2** (Poor Diagnostics) 与 **Type-2.PF** (Precondition Failure) 的关键依据。

### 四型缺陷分类决策树 (Four-Type Decision Tree)

Agent5 (`agent5_diagnoser.py`) 的 `classify_defect_v2()` 方法实现了五类缺陷分类体系：

```
                    L1: 契约合法?
                         |
           ┌─────────────┴─────────────┐
          NO (有Warning)               YES (无Warning)
           |                            |
         执行成功?                    执行成功?
       ┌──┴──┐                      ┌───┴───┐
      YES   NO                     NO     YES
       |     |                      |       |
    Type-1 Type-2              L2通过?  L2通过?
                                      |       |
                                    NO       YES
                                     |        |
                                  Type-2.PF  Oracle通过?
                                             |
                                           NO     YES
                                            |       |
                                         Type-4  无缺陷(Type-3保留)
```

| 类型 | 名称 | 判定条件 | 证据级别 | 典型场景 |
|------|------|----------|----------|----------|
| **Type-1** | 非法成功 (Illegal Success) | `L1=FAIL \| Exec=SUCCESS` | L1 | 非法维度请求绕过校验并被数据库接受 |
| **Type-2** | 诊断不足 (Poor Diagnostics) | `L1=FAIL\|PASS \| Exec=FAIL \| L2=PASS` | L2 | 请求失败但错误信息模糊不充分 |
| **Type-2.PF** | 前置条件失败 (Precondition Failure) | `L1=PASS \| Exec=FAIL \| L2=FAIL` | L2 | Collection 不存在或无数据导致失败 |
| **Type-3** | 传统预言机违规 (Traditional Oracle) | `L1=PASS \| Exec=SUCCESS \| 传统Oracle=FAIL` | L2/L3 | 单调性/一致性异常 |
| **Type-4** | 语义违规 (Semantic Violation) | `L1=PASS \| Exec=SUCCESS \| 语义Oracle=FAIL` | L3 | 搜索结果排序不合理、相关性不足 |

### 文档预处理流水线 (Document Preprocessing Pipeline)

Agent0 采用 **缓存优先 (Cache-First)** 策略处理数据库官方文档：

```
DocsConfig.source 选择
    ├── "auto"      → 优先加载本地 JSONL 缓存 → 未命中则 Crawl4AI 爬取
    ├── "local_jsonl" → 仅从本地 JSONL 加载
    └── "crawl"     → 强制重新爬取并覆盖缓存

处理管线: Filter (版本过滤/长度过滤) → Validate (数量/关键词校验) → Save (JSONL 本地存储)
```

配置参数见 [`.trae/config.yaml`](.trae/config.yaml) 中 `docs.` 节点。

### 契约回退系统 (Contract Fallback System)

当 Agent1 通过 LLM 提取契约时出现字段缺失，[`contract_fallbacks.py`](src/contract_fallbacks.py) 中的 `MilvusContractDefaults` 会自动填充空值，确保下游测试生成永不阻塞。回退规则涵盖：
- **L1 API 约束**: 30 种允许维度、6 种度量类型、12 种索引类型、Top-K 上限等
- **L2 语义约束**: 5 种标准操作序列

### Reranker 重排序管线

位于 Agent3 与 Agent4 之间的 [`agent_reranker.py`](src/agents/agent_reranker.py)，使用 `cross-encoder/ms-marco-MiniLM-L-6-v2` Cross-Encoder 模型对 Top-K 搜索结果进行精确语义重排序。模型加载失败时自动降级为词重叠评分策略。

### 其他关键能力

- **多轮自适应测试**: Agent2 接收 Agent5 的薄弱点反馈后进行定向用例变异
- **语义预言机**: Agent4 结合传统检查与 LLM 语义相关性打分
- **Token 预算熔断**: 全局 Token 消耗达到阈值时优雅终止
- **Recovery 机制**: 连续失败触发自动恢复流程
- **Docker 日志抓取**: 缺陷发现时自动采集容器深度日志作为补充证据
- **增强版去重 (EnhancedDeduplicator)**: 多维度相似度计算，避免重复 Issue 生成
- **MRE 隔离执行器 (IsolatedCodeRunner)**: Docker 容器隔离执行最小复现代码，确保安全性与可复现性
- **真实向量注入 (EmbeddingGenerator)**: 替换占位符向量，使用真实嵌入向量进行测试
- **文档参考验证器 (ReferenceValidator)**: 验证测试结果是否符合文档参考数据
- **Docker 容器连接池 (DockerContainerPool)**: 高效管理与复用 Docker 容器实例
- **状态压缩存储 (CompressionUtils)**: gzip/zlib 压缩算法优化大体积 WorkflowState 持久化

---

## 快速开始

### 前置要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.8 | 推荐 3.11 |
| Docker | >= 20.10 | 用于运行向量数据库测试实例 (Milvus/Qdrant/Weaviate) |
| Docker Compose | >= 2.0 | 用于编排测试集群 |
| GPU (可选) | CUDA 支持 | 加速 SentenceTransformer / Cross-Encoder 推理 |

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd ralph

# 2. 创建虚拟环境 (推荐)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 4. 复制环境变量模板
cp .env.example .env

# 5. 编辑 .env，设置 LLM API Key (三选一)
#    DEEPSEEK_API_KEY=sk-xxx
#    ANTHROPIC_API_KEY=sk-ant-xxx
#    ZHIPUAI_API_KEY=xxx
```

运行时配置文件位于 [`.trae/config.yaml`](.trae/config.yaml)，可通过环境变量以 `AI_DB_QC_` 前缀覆盖任意配置项（如 `AI_DB_QC_HARNESS_MAX_ITERATIONS=8`）。

### 运行

```bash
# 6. 启动检测流水线
python main.py
```

程序将自动完成以下流程：文档爬取/加载 -> 向量数据库 Docker 环境拉起 -> 多轮 Agent 协作测试 -> 缺陷发现与分类 -> GitHub Issue 生成。

### 输出位置

每次运行会在 `.trae/runs/` 下创建以 `run_` 前缀的唯一目录，包含：

```
.trae/runs/run_xxxxxxxxx/
├── state.json              # 完整 WorkflowState 快照 (每轮保存)
├── telemetry.jsonl         # 全链路遥测日志
├── emergency_dump.json     # 异常时的紧急转储 (仅出错时)
└── GitHub_Issue_*.md       # 生成的 GitHub Issue 文件
```

---

## v4.5 验证结果

### 测试概况

| 指标 | 值 |
|------|-----|
| Run ID | `run_0a79d4f2` |
| 版本 | v4.5 |
| 退出码 | 0 (成功) |
| 总耗时 | ~15.5 分钟 |
| 迭代轮次 | 4 轮 |
| 产出 Issue 数 | **12 个** |

### 缺陷类型分布

| 缺陷类型 | 数量 | 占比 | 说明 |
|----------|------|------|------|
| **Type-4** (语义违规/Semantic Violation) | ~11 | ~91.7% | LLM 语义预言机判定搜索结果不符合预期 |
| **Type-2** (诊断不足/Poor Diagnostics) | ~1 | ~8.3% | 错误信息模糊或不充分 |
| **Type-2.PF** (前置条件失败) | 0 | 0% | v4.4 已修复 |
| **Type-1** (非法成功) | 0 | 0% | -- |
| **Type-3** (传统预言机违规) | 0 | 0% | -- |

### v4.5 关键更新: 多数据库支持与能力增强

**v4.5 版本在 v4.4 基础上进行了以下重要更新：**

- **多数据库支持**: 系统现支持 Milvus、Qdrant、Weaviate 三种主流向量数据库
- **增强版去重**: 新增 EnhancedDeduplicator，支持多维度相似度计算
- **MRE 隔离执行器**: 新增 IsolatedCodeRunner，支持 Docker 容器隔离执行
- **真实向量注入**: 新增 EmbeddingGenerator，支持真实嵌入向量测试
- **文档参考验证器**: 新增 ReferenceValidator，验证测试结果符合参考数据
- **容器连接池优化**: 新增 DockerContainerPool，提升容器管理效率
- **状态压缩存储**: 新增 CompressionUtils，支持 gzip/zlib 压缩

### v4.4 关键修复: L2 门控状态传播 Bug

**问题**: v4.3 版本中所有缺陷被误判为 **Type-2.PF** (100% 伪阳性)，原因是 Agent3 的 L2 Runtime Gating 结果未正确传播至 Agent5 的决策树节点。

**根因**: `state.data_inserted` 和 `state.current_collection` 字段在 Agent3 执行过程中未正确写入 WorkflowState，导致 Agent5 在判断 `L2=PASS vs L2=FAIL` 时始终得到 `FAIL`，从而将本应归类为 Type-2 或 Type-4 的缺陷全部归入 Type-2.PF。

**修复方案**: 在 [`agent3_executor.py`](src/agents/agent3_executor.py) 中确保每次 Collection 创建和数据注入操作完成后同步更新 `state.current_collection` 与 `state.data_inserted`；在 StateGraph 的边传递中使用 Pydantic model_dump() 保证字段完整性。

**验证结论**: v4.4 的 12 个 Issue 中出现了合理的 Type-2 与 Type-4 分布，确认 L2 门控状态传播链路已正常工作。

---

## 项目结构

```
ralph/
├── main.py                          # 入口点: 初始化 State -> 构建 Graph -> 执行流水线
│
├── src/
│   ├── graph.py                     # LangGraph StateGraph 流水线编排 (条件路由定义)
│   ├── state.py                     # WorkflowState (Pydantic): 全局状态模型定义 + 工具类 (CompressionUtils / DockerContainerPool / StateManager)
│   ├── config.py                    # 配置管理: AppConfig / ConfigLoader (YAML + Env)
│   ├── contract_fallbacks.py        # 契约回退系统: MilvusContractDefaults
│   ├── telemetry.py                 # 遥测系统: TelemetryEvent / telemetry_sink
│   ├── performance.py               # 性能监控: memory / cpu / elapsed 采集
│   ├── rate_limiter.py              # API 速率限制器
│   ├── coverage_monitor.py          # 覆盖率监控: 评估缺陷趋势与终止条件
│   ├── knowledge_base.py            # 缺陷知识库: ChromaDB 向量存储
│   │
│   ├── agents/                      # Multi-Agent 实现 (Agent0 ~ Agent6 + 辅助 Agent)
│   │   ├── agent0_env_recon.py      # 环境与情报获取: 文档爬取 + Docker 部署
│   │   ├── agent1_contract_analyst.py # 场景与契约分析师: L1/L2/L3 契约提取
│   │   ├── agent2_test_generator.py  # 混合测试生成器: 规则 + LLM 语义用例
│   │   ├── agent3_executor.py        # 执行与前置门控官: L1/L2 双层门控 (核心)
│   │   ├── agent_reranker.py         # Reranker: Cross-Encoder 语义重排序
│   │   ├── agent4_oracle.py          # 预言机协调官: 传统 + LLM 语义验证
│   │   ├── agent5_diagnoser.py       # 缺陷诊断器: 四型决策树分类 (核心)
│   │   ├── agent6_verifier.py        # 缺陷验证与去重: MRE + 相似度去重 + Issue 生成
│   │   ├── agent_recovery.py         # Recovery: 连续失败恢复机制
│   │   ├── agent_reflection.py       # Reflection: 反思总结与 Issue 输出
│   │   ├── agent_web_search.py       # Web 搜索: 外部知识获取
│   │   ├── enhanced_test_generator.py # 增强版测试生成器
│   │   └── agent_factory.py          # Agent 工厂: 统一创建与管理
│   │
│   ├── adapters/                    # 数据库适配器层
│   │   └── db_adapter.py            # 统一 DB 接口: MilvusAdapter / QdrantAdapter / WeaviateAdapter
│   │
│   ├── oracles/                     # 语义预言机模块
│   │   ├── enhanced_semantic_oracle.py  # LLM 语义预言机实现
│   │   ├── grading_criteria.py          # 评分标准定义
│   │   └── evaluator_calibration.py     # 评估器校准
│   │
│   ├── docs/                        # 文档处理模块
│   │   └── local_docs_library.py    # 本地 JSONL 文档库管理
│   │
│   ├── defects/                     # 缺陷处理模块
│   │   └── enhanced_deduplicator.py # 增强版去重器 (多维度相似度)
│   │
│   ├── parsers/                     # 文档解析器
│   │   └── doc_parser.py            # 文档内容解析
│   │
│   ├── pools/                       # 资源池管理
│   │   └── collection_pool.py       # Collection 连接池管理
│   │
│   ├── validators/                  # 验证器
│   │   └── reference_validator.py   # 参考数据验证
│   │
│   ├── context/                     # 上下文管理
│   │   ├── handoff.py              # Agent 间交接协议
│   │   └── reset_manager.py        # 状态重置管理
│   │
│   ├── alerting/                    # 告警系统
│   │   ├── alert_manager.py        # 告警管理器
│   │   └── handlers.py             # 告警处理器
│   │
│   ├── dashboard/                   # 可视化面板
│   │   └── app.py                  # Web Dashboard
│   │
│   ├── experiments/                 # 实验模块
│   │   ├── baseline_comparison.py   # 基线对比实验
│   │   ├── cross_database_validation.py # 跨库验证
│   │   └── stability_testing.py     # 稳定性测试
│   │
├── configs/                         # 数据库连接配置文件
├── scripts/                         # 工具脚本 (test_qdrant_adapter.py, test_weaviate_adapter.py, monitor_progress.py, realtime_monitor.py)
├── tests/                           # 单元测试
│
├── .trae/                           # 运行时目录 (gitignored)
│   ├── config.yaml                  # 运行时配置 (YAML)
│   ├── cache/                       # 文档缓存 (JSONL)
│   ├── specs/                       # 开发规格文档
│   │   └── SPECS_INDEX.md           # 开发历史索引
│   └── runs/                        # 运行输出
│       └── run_xxxxxxxxx/           # 每次运行的独立目录
│           ├── state.json
│           ├── telemetry.jsonl
│           └── GitHub_Issue_*.md
│
├── AGENTS.md                        # 详细 Agent 架构设计文档 (v4.5)
├── docker-compose.milvus.yml        # Milvus Docker 编排文件 (etcd + minio + standalone)
├── docker-compose.qdrant.yml        # Qdrant Docker 编排文件
├── docker-compose.weaviate.yml      # Weaviate Docker 编排文件
├── requirements.txt                 # Python 依赖清单
└── .env                             # 环境变量 (API Keys 等, 不入库)
```

---

## 配置参考

运行时配置文件为 [`.trae/config.yaml`](.trae/config.yaml)，支持 YAML 文件 + 环境变量 (`AI_DB_QC_` 前缀) 双层覆盖。主要配置节如下：

### LLM 配置 (通过 `.env` 或环境变量)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | (必填, 三选一) |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API 密钥 | (必填, 三选一) |
| `ZHIPUAI_API_KEY` | 智谱 AI API 密钥 | (必填, 三选一) |
| `LLM_PROVIDER` | LLM 提供商 | `anthropic` |
| `LLM_MODEL` | 模型名称 | `claude-opus-4-6` |
| `LLM_MAX_TOKENS` | 单次请求最大 Token | `4096` |
| `LLM_TEMPERATURE` | 生成温度 | `0.7` |

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_TYPE` | 数据库类型: `milvus` / `qdrant` / `weaviate` | `milvus` |
| `DB_HOST` | 数据库地址 | `localhost` |
| `DB_PORT` | 数据库端口 (Milvus: 19530, Qdrant: 6333, Weaviate: 8081) | `19530` |
| `DB_USERNAME` | 用户名 | (可选) |
| `DB_PASSWORD` | 密码 | (可选) |

**支持的向量数据库：**

| 数据库 | 默认端口 | 适配器类 | Docker 编排文件 |
|--------|----------|----------|----------------|
| **Milvus** | 19530 | MilvusAdapter | [docker-compose.milvus.yml](docker-compose.milvus.yml) |
| **Qdrant** | 6333 | QdrantAdapter | [docker-compose.qdrant.yml](docker-compose.qdrant.yml) |
| **Weaviate** | 8081 | WeaviateAdapter | [docker-compose.weaviate.yml](docker-compose.weaviate.yml) |

### Harness (流水线) 配置

| 键路径 | 说明 | 默认值 |
|--------|------|--------|
| `harness.max_token_budget` | 最大 Token 预算 | `1000000` |
| `harness.max_iterations` | 最大迭代轮次 | `4` |
| `harness.target_db_input` | 本轮目标数据库输入 | `Weaviate 1.36.9` |
| `harness.max_consecutive_failures` | 连续失败阈值 (触发 Recovery) | `3` |
| `harness.similarity_threshold` | 语义相似度阈值 (防退化) | `0.9` |

### Run Guard（禁止降级/模拟路径）

| 键路径 | 说明 | 默认值 |
|--------|------|--------|
| `run_guard.enabled` | 启用运行守卫 | `true` |
| `run_guard.enforce_weaviate_1369` | 强制目标为 Weaviate 1.36.9 | `true` |
| `run_guard.enforce_max_iterations_4` | 强制最大轮次为 4 | `true` |
| `run_guard.forbidden_terms` | 禁止出现的降级/模拟关键词 | `["degraded","fallback","simulate","simulation","mock","fake","降级","替代","模拟"]` |

### 实时监控脚本（CPU/内存/网络/日志/异常栈）

```bash
python scripts/realtime_monitor.py --interval 5 --cpu-threshold 85 --mem-threshold 85 --net-threshold 100 --warmup-seconds 30 --consecutive-breach-threshold 3
```

- 指标时间序列输出：`.trae/runs/monitoring/realtime_metrics_*.jsonl`
- 告警快照输出：`.trae/runs/monitor_alerts/alert_snapshot_*.json`（仅连续超阈触发中断告警时落盘）
- `warmup_seconds`：预热窗口，忽略启动/文档抓取峰值导致的瞬时超阈
- `consecutive_breach_threshold`：连续超阈阈值，达到次数才触发中断告警

### 文档配置

| 键路径 | 说明 | 默认值 |
|--------|------|--------|
| `docs.source` | 文档来源: `auto` / `local_jsonl` / `crawl` | `local_jsonl` |
| `docs.local_jsonl_path` | 本地 JSONL 缓存路径 | `.trae/cache/milvus_io_docs_depth3.jsonl` |
| `docs.cache_enabled` | 是否启用缓存 | `true` |
| `docs.allowed_versions` | 允许的文档版本 | `["2.6"]` |
| `docs.min_docs` | 最少文档数量 | `50` |

完整配置类定义见 [`src/config.py`](src/config.py) 中的 `AppConfig` / `ConfigLoader`。

---

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **编排框架** | LangGraph (StateGraph) | Multi-Agent 流水线编排、条件路由、Checkpoint |
| **LLM** | Anthropic Claude / DeepSeek / 智谱 AI | 语义理解、测试生成、预言机验证、缺陷分类 |
| **向量嵌入** | SentenceTransformers (all-MiniLM-L6-v2) | 查询向量化、缺陷去重相似度计算 |
| **重排序** | Cross-Encoder (ms-marco-MiniLM-L-6-v2) | Top-K 搜索结果语义重排序 |
| **向量数据库** | pymilvus 2.3.6 / qdrant-client 1.8.0 / weaviate-client 3.x | 目标被测数据库 (Milvus/Qdrant/Weaviate) |
| **知识库** | ChromaDB | 缺陷知识存储、混合搜索 |
| **爬虫引擎** | Crawl4AI | 官方文档深度爬取 (BFS 最多 3 层) |
| **容器化** | Docker + docker-compose | Milvus 测试环境隔离部署 |
| **配置管理** | Pydantic Settings + PyYAML | 类型安全配置、环境变量覆盖 |
| **测试框架** | pytest 8.1 + pytest-cov | 单元测试与覆盖率 |

---

## 链接与参考

| 文档 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | 详细 Agent 架构设计文档 (含 Mermaid 时序图、决策树、数据接口定义) |
| [.trae/specs/SPECS_INDEX.md](.trae/specs/SPECS_INDEX.md) | 开发规格索引与版本演进历史 |
| [docker-compose.milvus.yml](docker-compose.milvus.yml) | Milvus v2.6.12 测试环境 Docker 编排文件 |
| [docker-compose.qdrant.yml](docker-compose.qdrant.yml) | Qdrant 测试环境 Docker 编排文件 |
| [docker-compose.weaviate.yml](docker-compose.weaviate.yml) | Weaviate 测试环境 Docker 编排文件 |
| [src/graph.py](src/graph.py) | LangGraph 流水线图定义 (节点与边的声明) |
| [src/state.py](src/state.py) | WorkflowState Pydantic 模型 (全局状态 Schema + 工具类) |
| [src/config.py](src/config.py) | 配置管理系统 (AppConfig + ConfigLoader) |
| [src/agents/agent3_executor.py](src/agents/agent3_executor.py) | L1/L2 双层门控执行器 (核心安全机制) |
| [src/agents/agent5_diagnoser.py](src/agents/agent5_diagnoser.py) | 四型缺陷分类决策树实现 |
| [src/contract_fallbacks.py](src/contract_fallbacks.py) | 契约回退系统 (MilvusContractDefaults) |
| [src/adapters/db_adapter.py](src/adapters/db_adapter.py) | 数据库适配器层 (Milvus/Qdrant/Weaviate 统一接口) |
| [src/defects/enhanced_deduplicator.py](src/defects/enhanced_deduplicator.py) | 增强版去重器 (多维度相似度计算) |
| [src/pools/collection_pool.py](src/pools/collection_pool.py) | Collection 连接池管理 |
| [src/validators/reference_validator.py](src/validators/reference_validator.py) | 参考数据验证器 |
| [src/context/handoff.py](src/context/handoff.py) | Agent 间交接协议 |
| [src/alerting/alert_manager.py](src/alerting/alert_manager.py) | 告警管理器 |

---

## 许可证

本项目仅供学习与研究使用。
