# AI-DB-QC v2.0 迭代与改进开发计划

**文档状态**：Draft
**目标**：基于 v1.0 成功跑通的基座，针对现有瓶颈进行架构优化、性能提升及能力扩展，打造企业级可用的测试流水线。

***

## 1. 现状分析与痛点 (v1.0 Bottlenecks)

虽然 v1.0 成功实现了从环境拉起到 Bug Issue 生成的闭环，但在实战中暴露出以下局限性：

### 1.1 性能与并发瓶颈

* **单线程执行**：目前 `Agent 3 (执行门控)` 和 `Agent 4 (预言机)` 都是串行处理测试用例。如果一次生成 100 个用例，LLM 预言机校验会非常耗时。

* **冷启动慢**：`Agent 0` 每次都重新拉起 Docker 容器，对于短轮次的 Fuzzing 来说，环境准备时间占比较高。

### 1.2 智能化程度不足

* **假阳性 (False Positives) 偏高**：`Agent 4 (语义预言机)` 仅靠一次 LLM 调用判断结果，缺乏对数据库内部状态（如索引是否构建完成、数据是否落盘）的感知，容易误报。

* **Fuzzing 变异策略单一**：`Agent 2` 目前主要依赖 LLM 的随机生成（Temperature=0.7），缺乏基于代码覆盖率或真实请求分布的导向性变异 (Coverage-guided or Distribution-guided Fuzzing)。

### 1.3 生态与工具链局限

* **去重策略过于简单**：`Agent 6` 目前仅使用字符串前缀匹配进行 Bug 去重，无法识别表象不同但根因相同的缺陷。

* **支持的数据库单一**：虽然设计了 Adapter 接口，但目前只实现了 Milvus，缺乏 Qdrant、Pinecone 等横向对比能力。

***

## 2. 改进方向与架构升级 (v2.0 Improvements)

针对上述痛点，v2.0 计划从以下四个维度进行升级：

### 2.1 架构并发与异步化 (Concurrency)

* **LangGraph 并行执行**：利用 LangGraph 的 `Send` API (Map-Reduce 模式) 或 `asyncio`，重构 `Agent 3` 和 `Agent 4`，使测试用例的执行和 LLM 校验能够并行处理。

* **连接池与会话保持**：在 Adapter 层引入长连接池，避免频繁建联。

### 2.2 预言机与诊断升级 (Smart Oracle & Diagnostics)

* **引入自我反思机制 (Self-Reflection)**：`Agent 4` 在判定为“失败”时，自动触发二次确认（即 `Critic` 模式），结合数据库日志再次推理，降低假阳性。

* **多模态向量支持**：除了纯文本，扩展 `Agent 2` 生成图像/多模态向量的能力，测试更复杂的 Embedding 场景。

### 2.3 自我进化与闭环增强 (Self-Evolution Loop)

* **主动联网学习 (Web-Augmented Learning)**：打破固有的变异规则，赋予 Agent 主动调用 `Tavily API` 或其他搜索引擎的能力。当当前 Fuzzing 策略陷入瓶颈（连续多轮未发现新 Bug）时，Agent 自动上网检索目标数据库的最新 CVE 漏洞库、GitHub Issues 以及前沿学术论文（如关于 HNSW 算法的对抗攻击研究），从中提取新的测试策略 (Testing Strategies)。

* **反思与策略沉淀 (Strategy Reflection)**：在每一轮测试结束或诊断出新 Bug 后，增加一个专门的 `Reflection Node`，对“为什么这种变异有效”进行总结反思，并将经验固化为 Prompt 规则库或向量化存储。

* **反馈向量化**：将 `Agent 5` 提取的缺陷特征进行 Embedding 存储，构建“缺陷知识库”。`Agent 2` 生成用例时，优先利用 RAG 检索历史缺陷特征进行定向变异。

* **变异算子分离**：将 Rule-based 变异（如随机翻转、越界注入）与 LLM-based 语义变异分离，由传统代码处理高频的基础越界，LLM 专注于语义逻辑盲区，节省 Token。

### 2.4 生态扩展与 CI/CD 集成 (Ecosystem & CI/CD)

* **向量化去重**：`Agent 6` 引入 `Chroma` 或本地 `FAISS`，将收集到的 Bug Root Cause 转化为向量进行相似度检索 (Cosine Similarity > 0.85 则认为是重复 Bug)。

* **GitHub Actions 集成**：提供标准的 `.github/workflows/ai-db-qc.yml` 模板，支持作为 PR 的自动化门禁（回归测试）。

* **Qdrant 适配器**：实现 `QdrantAdapter` 并完成双库比对测试 (Differential Testing)。

***

## 3. WBS 任务拆解 (v2.0)

预计周期：4-6 周。

### 阶段一：性能优化与并发重构 (Week 1)

* **WBS 1.1**: 重构 `Agent 3`，引入 `asyncio` 和 `aiohttp/grpc-async` 实现高并发打流。

* **WBS 1.2**: 重构 `Agent 4`，使用 LangChain 的异步批处理 (`abatch`) 并发调用 LLM 预言机。

* **WBS 1.3**: 环境层优化，引入“热备沙箱池”机制，减少 Docker 启停等待时间。

### 阶段二：算法增强、主动学习与知识库构建 (Week 2-3)

* **WBS 2.1**: 开发 `Defect Knowledge Base`，在 `Agent 5` 诊断后将 Bug 向量化落盘。

* **WBS 2.2**: 升级 `Agent 2` 为 RAG-based Fuzzer，检索历史弱点进行定向生成。

* **WBS 2.3**: 引入 **Web Search Agent**，配置 `Tavily` 或 `Google Search API`。设计策略瓶颈检测机制，触发主动检索学术文献与 CVE 库。

* **WBS 2.4**: 增加 `Reflection Node`，在 LangGraph 的闭环末端对测试收益进行总结反思，提取新的变异算子存入规则库。

### 阶段三：生态扩展与去重重构 (Week 4)

* **WBS 3.1**: 重构 `Agent 6`，基于向量相似度重写 Deduplication 逻辑。

* **WBS 3.2**: 开发并联调 `QdrantAdapter`。

* **WBS 3.3**: 引入 Differential Testing (差异测试) 逻辑：同一个用例同时打入 Milvus 和 Qdrant，对比两者结果集。

### 阶段四：打包发布与 CI/CD (Week 5)

* **WBS 4.1**: 编写 GitHub Actions Action 插件封装。

* **WBS 4.2**: 完善用户控制台（CLI 或简易 Streamlit WebUI），实时展示 Agent 运行状态和 Token 消耗。

***

## 4. 关键指标 (KPIs for v2.0)

1. **执行效率**：单轮 100 个用例的执行+预言机校验耗时从 5 分钟缩短至 1 分钟内。
2. **去重准确率**：同一 Bug 变体的拦截率提升至 95% 以上。
3. **假阳性率**：语义预言机误报率降低至 2% 以下。
4. **覆盖率**：支持至少 2 种主流开源向量数据库（Milvus, Qdrant）。

