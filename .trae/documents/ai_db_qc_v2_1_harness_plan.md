# AI-DB-QC v2.1: Harness 强化与底层可观测性重构计划

## 0. 前言：关于 "Harness" 的概念澄清

在软件工程和自动化测试领域，**Test Harness (测试线束/测试脚手架)** 是一个标准术语。它指的是一套能够**自动化执行测试、提供受控环境、并收集执行结果**的软件框架。其核心职责包括：环境准备 (`Setup`)、测试数据注入 (`Data Seeding`)、状态监控 (`Monitoring`) 以及环境清理 (`Teardown`)。

> **注：关于 Anthropic 的 Harness**
> Anthropic 在发布 Claude 系列模型（或进行相关对齐、安全评测）时，也开源或提及过他们自己的 "Evaluation Harness"（例如用于大模型跑分的框架）。
> 但在本篇文档中，我们所指的 Harness **并非特指 Anthropic 的某个特定开源库**，而是借用这个经典的软件工程概念，来**重构我们当前工作流中负责与数据库交互的底层执行层 (即 `Agent 3` 和 `DB Adapter`)**。
> 我们的目标是让这个底层模块变得像一个专业的企业级数据库测试线束，而不是目前这样随意的“打草稿”。

---

## 1. 现状痛点 (为什么需要 v2.1)

尽管我们在 v2.0 中加入了智能化的自学习和反思，但底层的执行层 (`Agent 3`) 仍然像个“玩具”，存在以下致命问题：

1. **状态污染 (State Pollution)**：测试结束后不清理临时生成的 `Collection`，导致下一次 Fuzzing 可能被之前残留的脏数据干扰。
2. **假数据无法验证语义 (Fake Embeddings)**：目前为了省事，文本转向量使用的是 `_mock_embed` (生成随机浮点数)。这意味着无论查什么词，底层的距离计算都是随机的，导致 `Agent 4 (语义预言机)` 的验证结果根本站不住脚。
3. **黑盒观测 (Black-box Observability)**：当发生 `ECOM_002` 这种底层 C++ 崩溃时，我们的 Agent 只能拿到外层的 API 报错。如果发生了更隐蔽的 OOM 或死锁，Agent 只能得到一个冰冷的 `Timeout`。

---

## 2. 改进方向与架构升级 (双轨制 Harness)

v2.1 的核心目标是将系统升级为一个**双轨制 (Dual-Track) 的测试线束**：
1. **Software Test Harness (传统工程向)**：将底层的执行层重构为一个确定性强、高保真、白盒可观测的受控环境。
2. **AI Evaluation Harness (智能体评测向)**：借鉴 Anthropic Inspect 理念，将大模型判定机制规范化，并建立对抗能力的评测基准。

### 2.1 引入高保真 Embedding 模型 (Real Embeddings)
* **抛弃随机数**：集成 `sentence-transformers` 或调用大模型的 Embedding API，将 `Agent 3` 中的查询文本和底库文本转化为真实的向量表示。
* **收益**：这是保证 `Agent 4 (语义预言机)` 能够正确评估“召回准确率”和“语义相关性”的绝对前提。

### 2.2 Harness 生命周期与状态重置 (Lifecycle Management)
* **受控的数据注入 (Controlled Data Injection)**：不再只插入 50 条 dummy data。引入数据分布模板（如：20% 密集数据，80% 稀疏噪音）。
* **严格的清理钩子 (Teardown Hooks)**：在 `MilvusAdapter` 中强制实现 `setup_harness()` 和 `teardown_harness()`，确保每一轮测试开始前数据库是干净的。

### 2.3 深度探针与白盒诊断 (Deep Observability)
* **Docker 日志旁路采集**：在 `Agent 3` 执行时，若捕获到异常或超时，通过 Docker SDK 主动去拉取目标容器的最后 100 行 `stderr/stdout` 日志。
* **日志喂入诊断器**：将采集到的底层 C++ 堆栈直接附在 `ExecutionResult` 中，交给 `Agent 5 (缺陷诊断)`。这会让大模型的 Bug Root Cause 分析变得极其精准（从“瞎猜”变成“源码级分析”）。

### 2.4 AI Evaluation Harness: 预言机重构与基准抽取 (Anthropic 理念)
* **规范化 Scorer 机制**：将 `Agent 4 (预言机)` 升级为类似于 Inspect 的标准化 Scorer。除了现有的“通过/失败”，要求 LLM 输出详细的推理轨迹 (Reasoning Traces) 并打分 (0.0-1.0 置信度)。
* **变异能力基准化 (Benchmark Extraction)**：把 `Agent 5` 诊断出的历史真实 Bug（如维度越界）沉淀为固定的**测试数据集 (Dataset)**。这套数据集可用于反向评估不同大模型（GPT-4o vs GLM-4 vs Claude 3.5）在数据库 QA 场景下的“攻击/诊断能力”。

---

## 3. WBS 任务拆解 (v2.1 双轨制)

### 阶段一：高保真数据与生命周期 (Week 1)
* **WBS 1.1: 真实 Embedding 接入**：在 `Agent 3` 中集成 `HuggingFaceEmbeddings` (如 `all-MiniLM-L6-v2`)，替换掉 `_mock_embed`。
* **WBS 1.2: Adapter 生命周期重构**：在 `VectorDBAdapter` 接口中增加 `setup_harness` 和 `teardown_harness` 方法。
* **WBS 1.3: 受控数据生成器**：开发一个小型模块，专门负责根据配置（如规模、维度、噪音比例）向测试 Collection 中注入具有真实语义的文本和向量底库。

### 阶段二：白盒观测与诊断联动 (Week 2)
* **WBS 2.1: Docker 探针开发**：开发 `DockerLogsProbe` 类，负责在执行出错时抓取容器内部的底层日志。
* **WBS 2.2: 状态机结构更新**：修改 `ExecutionResult` 模型，增加 `underlying_logs` 字段。
* **WBS 2.3: 诊断提示词升级**：修改 `Agent 5` 的 Prompt，使其能够解析 C++ 或 Go 的底层堆栈，输出更专业的 `Root Cause Analysis`。

### 阶段三：AI Evaluation Harness 机制 (Week 3)
* **WBS 3.1: 预言机打分器重构**：引入置信度评分和强制 `Chain-of-Thought` (CoT) 推理轨迹记录。
* **WBS 3.2: 评测基准抽取器**：开发脚本，从 `chroma_db` 的缺陷库中提取真实 Bug 场景，生成符合行业标准的 JSONL Dataset。