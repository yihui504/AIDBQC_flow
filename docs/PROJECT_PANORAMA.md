# AI-DB-QC 项目全景图

## 1. 文档目的与范围

本文档基于现有产出进行结构化归纳，信息来源包括：

- `README.md`（系统能力与模块结构）
- `AGENTS.md`（多智能体协作与数据接口）
- `docs/TECHNICAL_REPORT.md`（双层门控、缺陷分类与运行结果）
- `.trae/runs/run_0a79d4f2/GitHub_Issue_*.md`（已输出漏洞样本）

目标是形成可审计的“项目全景图”，为漏洞审计与修复优先级提供统一上下文。

## 2. 业务目标与系统定位

AI-DB-QC 是一个面向向量数据库（Milvus/Qdrant/Weaviate）的自动化质量检测系统，核心目标：

1. 自动获取文档与运行环境，构建契约约束。
2. 自动生成边界/语义/对抗测试用例并执行。
3. 使用双层门控与预言机发现缺陷。
4. 进行缺陷验证、去重并产出标准化 Issue。

## 3. 架构总览

### 3.1 核心流水线（主链路）

`Agent0 环境与情报获取`  
-> `Agent1 契约分析`  
-> `Agent2 测试生成`  
-> `Agent3 执行与 L1/L2 门控`  
-> `Reranker 语义重排序`  
-> `Agent4 预言机校验`  
-> `Agent5 缺陷分类`  
-> `Agent6 验证去重与 Issue 生成`

### 3.2 关键机制

- 双层有效性模型：
  - L1 抽象合法性（默认硬阻断 dimension/top_k，支持配置开关切换为 Warning）
  - L2 运行时就绪性（硬阻断，用于区分 Type-2 与 Type-2.PF）
- 四型缺陷分类决策树：
  - Type-1 / Type-2 / Type-2.PF / Type-3 / Type-4
- 自适应闭环：
  - Agent5 反馈薄弱点 -> Agent2 定向增强下一轮用例。

## 4. 代码与模块边界

### 4.1 核心目录

- `src/agents/`：智能体实现（Agent0~Agent6 + recovery/reflection/reranker）
- `src/adapters/`：多数据库统一适配层
- `src/oracles/`：语义预言机与评估校准
- `src/defects/`：缺陷去重与相似度计算
- `src/validators/`：证据/参考验证
- `src/state.py`：全局状态模型（WorkflowState）
- `src/graph.py`：LangGraph 流程编排与路由

### 4.2 运行资产

- `.trae/config.yaml`：运行配置与门限
- `.trae/cache/`：文档缓存
- `.trae/runs/run_xxx/`：状态快照、遥测日志、Issue 产物

## 5. 依赖拓扑（外部系统）

### 5.1 基础依赖

- Python + pytest
- LangGraph（工作流编排）
- SentenceTransformer / Cross-Encoder（语义向量与重排序）
- ChromaDB（缺陷知识库）
- Crawl4AI（文档抓取）

### 5.2 基础设施依赖

- Docker + Docker Compose（Milvus/Qdrant/Weaviate 测试环境）
- LLM Provider（Anthropic/DeepSeek/智谱）

## 6. 关键数据流

1. 用户输入数据库目标 -> 初始化 `WorkflowState`。
2. Agent0 抓取/加载文档并部署 DB 环境。
3. Agent1 从文档抽取契约，必要时由 `contract_fallbacks` 补全。
4. Agent2 生成测试集（标准/边界/对抗）。
5. Agent3 执行并记录 L1/L2 结果与底层日志。
6. Reranker + Agent4 完成语义与传统预言机验证。
7. Agent5 分类并形成缺陷报告。
8. Agent6 重放验证、去重，生成 `GitHub_Issue_*.md`。

## 7. 质量与风险热区

结合已输出问题，当前高风险集中在以下链路：

- 契约边界约束：`dimension`、`top_k` 等上限可能被绕过。
- 运行时状态约束：`collection_exists`、`index_loaded` 场景存在语义违约样本。
- 语义检索质量：拼写扰动、过滤条件、混合检索重排序中出现相关性漂移与噪声上浮。
- 诊断可用性：参数错误可能被误报为“数据库未就绪”，影响排障效率。

## 8. 全景结论

项目已形成“可运行 + 可观测 + 可生成缺陷证据”的完整链路，但在“约束强制执行”和“语义结果稳定性”两条主线上仍有明显改进空间。建议将修复优先级聚焦在：

1. 高危约束绕过（维度/Top-K/状态约束）。
2. 语义检索与重排序一致性。
3. 诊断信息准确性与可定位性。

对应漏洞条目、修复建议与测试映射见 `docs/VULNERABILITY_AUDIT.md`。
