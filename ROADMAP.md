# AI-DB-QC 项目发展规划 (Roadmap)

> **文档版本**: v1.3 | **基准版本**: v4.5 | **更新日期**: 2026-04-06

---

## 一、项目现状总结

### 1.1 版本演进

| 版本 | 核心能力 | 状态 |
|------|----------|------|
| v3.2 | Multi-Agent Pipeline 基础架构 | ✅ 完成 |
| v3.5 | 三层契约系统、语义去重、MRE 生成 | ✅ 完成 |
| v4.0 | L1 门控、文档预处理管道 | ✅ 完成 |
| v4.4 | L2 Runtime Gating、四型决策树、Reranker、Contract Fallback | ✅ 已验证 |

### 1.2 当前核心能力 (v4.5)

| 能力 | 实现状态 | 验证结果 |
|------|----------|----------|
| **Multi-Agent Pipeline** | ✅ 完整实现 | 9-Agent 协同流，LangGraph 编排 |
| **L1 抽象合法性门控** | ✅ Warning 模式 | 允许捕获 Type-1 缺陷 |
| **L2 运行时就绪性门控** | ✅ 硬阻断 | 区分 Type-2 vs Type-2.PF |
| **四型缺陷分类决策树** | ✅ 完整实现 | Type-1/2/2.PF/3/4 五类分类 |
| **文档预处理管道** | ✅ Cache-First | JSONL 缓存 + Filter/Validate/Save |
| **契约回退系统** | ✅ MilvusContractDefaults | 自动填充空字段 |
| **Cross-Encoder Reranker** | ✅ ms-marco-MiniLM-L-6-v2 | 语义重排序 |
| **语义预言机** | ✅ LLM + 传统预言机 | 相关性打分 |
| **ChromaDB 知识库** | ✅ 缺陷去重 | 多维度相似度 |
| **MRE 生成与验证** | ✅ 自动生成 | 可复现性验证 |
| **Qdrant 支持** | ✅ 已验证 | 向量数据库测试扩展 | 实战测试通过 |
| **Weaviate 支持** | ✅ 已验证 | 向量数据库测试扩展 | 实战测试通过 |
| **GitHub Issue 生成** | ✅ 标准化输出 | 12 Issues / run |
| **EnhancedDeduplicator** | ✅ 已实现 | 多维度相似度去重（语义+结构+行为+上下文） |
| **IsolatedCodeRunner** | ✅ 已实现 | Docker 隔离 MRE 执行 |
| **EmbeddingGenerator** | ✅ 已实现 | 真实语义向量注入 |
| **ReferenceValidator** | ✅ 已实现 | 文档参考验证 |
| **DocumentCache** | ✅ 已实现 | TTL 文档缓存系统 |
| **DockerContainerPool** | ✅ 已实现 | 容器连接池复用 |
| **CompressionUtils** | ✅ 已实现 | 状态压缩存储（gzip/zlib） |

### 1.3 v4.4 验证数据

| 指标 | 值 |
|------|-----|
| Run ID | `run_0a79d4f2` |
| 退出码 | 0 (成功) |
| 总耗时 | ~15.5 分钟 |
| 迭代轮次 | 4 轮 |
| 产出 Issue 数 | 12 个 |
| 缺陷分布 | Type-4: ~91.7%, Type-2: ~8.3% |

---

## 二、开题报告目标 vs 当前实现对照

### 2.1 核心研究内容对照

| 开题报告目标 | 当前实现 | 完成度 | 说明 |
|--------------|----------|--------|------|
| **0. 调研AI数据库技术体系，梳理质量保障核心挑战** | ✅ 已完成 | 100% | 已形成完整的技术框架报告，识别了向量计算偏差、语义匹配失真等核心缺陷类型 |
| **1. 设计基于大模型的AI数据库质量测试用例生成方法** | ✅ 已完成 | 95% | Agent2 实现了混合测试生成（规则+LLM语义），支持对抗样本、语义边界测试 |
| **2. 构建AI数据库测试用例正确性判断技术** | ✅ 已完成 | 95% | Agent4 预言机系统实现了传统预言机 + LLM 语义预言机双层验证，ReferenceValidator 新增文档参考验证 |
| **3. 跨数据库质量检测框架** | ✅ 已完成 | 100% | 统一 Adapter 抽象 + 三种数据库（Milvus/Qdrant/Weaviate）全适配 |

### 2.2 三阶段规划对照

| 阶段 | 开题报告目标 | 当前状态 | 完成度 |
|------|--------------|----------|--------|
| **阶段一 (1-2月)** | 完成AI数据库调研分析，梳理主流技术及案例，明确质量保障瓶颈，提炼缺陷关键特点 | ✅ 已完成 | 100% |
| **阶段二 (3-4月)** | 设计并初步实现大模型驱动的测试用例生成方法，搭建实验环境，选取典型场景验证 | ✅ 已完成 | 100% |
| **阶段三 (5-6月)** | 设计测试用例正确性判断方法，构建多维度验证模型，形成完整方案 | ✅ 已完成 | 95% |

### 2.3 预期成果对照

| 预期成果 | 当前状态 | 完成度 |
|----------|----------|--------|
| 适配AI数据库的质量保障工具 | ✅ AI-DB-QC v4.4 已发布 | 100% |
| 缺陷分析、自动化测试方法技术报告 | ✅ docs/TECHNICAL_REPORT.md | 100% |
| 学术论文1篇 | ❌ 未完成 | 0% |

---

## 三、差距分析与优先级

### 3.1 已识别差距

| 差距 | 优先级 | 影响范围 | 解决难度 |
|------|--------|----------|----------|
| **学术论文未产出** | P0 | 项目结题 | 中等 |
| **Type-1/Type-3 缺陷检测率不足** | P1 | 核心能力 | 高 |
| **技术报告需整理** | ✅ 已解决 | 文档完整性 | docs/TECHNICAL_REPORT.md 已创建 |
| **跨数据库支持不足** | ✅ 已解决 | 功能扩展 | Milvus/Qdrant/Weaviate 全支持 |
| **可视化报告缺失** | P2 | 用户体验 | 低 |
| **CI/CD 集成缺失** | P3 | 工程化 | 低 |
| **代码健康度问题** | P3 | 系统稳定性 | 低 |

### 3.2 核心差距详情

#### 差距 1：学术论文未产出 (P0)

**现状**: 项目已完成核心功能开发与验证，但尚未形成学术论文。

**影响**: 影响项目结题，无法满足开题报告的预期成果要求。

**解决方向**:
1. 整理 v4.4 验证数据，形成实验报告
2. 提炼核心创新点（双层门控、四型决策树、契约回退）
3. 对比实验：与传统测试方法的缺陷检测率对比

#### 差距 2：技术报告需整理 (P1)

**现状**: 项目有完整的 README.md 和 AGENTS.md，但缺少系统性的技术报告。

**影响**: 文档完整性不足，不利于后续维护和学术产出。

**解决方向**:
1. 整理缺陷分析方法论
2. 总结自动化测试流程
3. 形成完整的技术报告文档

#### 差距 3：Type-1/Type-3 缺陷检测率不足 (P1)

**现状**: 当前主要产出为 Type-4 缺陷（占比 ~91.7%），Type-1 和 Type-3 缺陷检测率接近 0%。

**影响**: 核心能力存在短板，无法全面覆盖缺陷类型，影响测试完整性和工具价值。

**解决方向**:
1. 放宽 L1 门控策略，允许更多抽象合法性检查进入验证流程
2. 增强传统预言机（单调性、一致性、幂等性等属性检测）
3. 引入更多对抗性测试用例生成策略
4. 优化四型决策树中 Type-1/Type-3 的判定路径

#### 差距 4：代码健康度问题 (P3)

**现状**: 项目代码存在多处硬编码依赖、导入错误和版本不一致问题，影响系统可维护性和跨平台适配能力。

**具体问题**:

1. **Agent5 硬编码容器名** — [agent5_diagnoser.py:24](src/agents/agent5_diagnoser.py#L24) 中 `container_name="milvus-standalone"` 为硬编码值，切换至 Qdrant 或 Weaviate 时会导致 Docker 日志探针失败。

2. **Dashboard 导入不存在的模块** — [dashboard/app.py:36](src/dashboard/app.py#L36) 中 `from src.roadmap import Roadmap` 引用了不存在的 `Roadmap` 类，导致 Streamlit 应用无法启动（ImportError）。

3. **AGENTS.md 版本号标注不一致** — 文档头部标注为 v4.4，但实际反映的架构已更新至 v4.5，文档与代码版本脱节。

4. **main.py 默认测试目标与文档描述不一致** — 默认配置指向的数据库与 README 主要描述的场景可能存在偏差（需结合 config.yaml 确认）。

**影响**: 降低代码可维护性，增加新开发者上手成本，可能导致跨数据库测试时出现运行时错误。

**解决方向**:
1. 消除硬编码：将容器名等配置项抽取至 `.trae/config.yaml` 或环境变量
2. 修复 Dashboard 导入错误：删除无效引用，改为直接读取 `.trae/runs/` 和 telemetry 数据
3. 统一版本号标注：将 AGENTS.md 更新为 v4.5
4. 配置中心化：建立统一的配置管理机制

---

## 四、后续开发方向与可行性分析

### 4.1 技术深化方向

#### 方向 1：跨数据库支持扩展

**目标**: 支持更多向量数据库（Qdrant、Weaviate、Pinecone）

**当前状态**: ✅ Qdrant / Weaviate 已完成，Milvus 原生支持 | ⏳ Pinecone / Chroma 待扩展

**技术可行性**: ⭐⭐⭐⭐ (高)
- 已有统一的 `db_adapter.py` 接口
- Milvus/Qdrant/Weaviate Adapter 已实现并验证
- 只需实现新数据库的 Adapter（Pinecone/Chroma）
- 契约回退系统已支持扩展

**资源需求**:
- 开发时间: 2-3 周/数据库
- 测试环境: 各数据库 Docker 部署
- API 文档: 官方文档爬取

**风险评估**:
- 不同数据库 API 差异较大，契约系统需适配
- 部分数据库（如 Pinecone）需云服务账号

**优先级**: P3（核心数据库已完成，剩余为扩展性工作）

---

#### 方向 2：缺陷检测精度提升

**目标**: 提高 Type-1/Type-3 缺陷的检测率

**技术可行性**: ⭐⭐⭐ (中)
- Type-1 需要更激进的 L1 门控放宽策略
- Type-3 需要增强传统预言机（单调性、一致性检查）

**资源需求**:
- 开发时间: 2-4 周
- LLM 调用成本: 可能增加 20-30%

**风险评估**:
- Type-1 检测可能导致更多误报
- 需要平衡检测精度与误报率

**优先级**: P1

---

#### 方向 3：性能优化

**目标**: 降低单次运行耗时（当前 ~15 分钟 → 目标 <10 分钟）

**技术可行性**: ⭐⭐⭐⭐ (高)
- 并行化 Agent 执行（部分 Agent 可并行）
- 缓存优化（文档、向量嵌入）
- Token 消耗优化

**资源需求**:
- 开发时间: 1-2 周
- 性能测试: 多轮基准测试

**风险评估**:
- 并行化可能影响状态一致性
- 需要仔细设计同步点

**优先级**: P2

---

### 4.2 功能扩展方向

#### 方向 4：可视化报告系统

**目标**: 提供 Web Dashboard 展示测试结果、缺陷分布、趋势分析

**当前状态**: ⏳ `src/dashboard/app.py` 框架已存在，基础结构就绪，但功能未完善

**技术可行性**: ⭐⭐⭐⭐⭐ (极高)
- 已有 `src/dashboard/app.py` 框架
- Streamlit 快速开发
- 数据源: telemetry.jsonl + state.json

**资源需求**:
- 开发时间: 1-2 周
- 依赖: requirements-dashboard.txt 已就绪

**风险评估**:
- 低风险，技术栈成熟

**优先级**: P1

---

#### 方向 5：CI/CD 集成

**目标**: 提供 GitHub Action / Jenkins 集成，支持自动化回归测试

**技术可行性**: ⭐⭐⭐⭐ (高)
- 输出已是标准化 GitHub Issue
- 可配置为定时任务或触发式

**资源需求**:
- 开发时间: 1 周
- CI 环境配置: Docker-in-Docker 或外部 Milvus

**风险评估**:
- CI 环境资源需求较高
- 需要处理 LLM API 密钥安全

**优先级**: P3

---

#### 方向 6：自动化回归测试

**目标**: 对已发现的缺陷进行自动化回归验证

**技术可行性**: ⭐⭐⭐⭐ (高)
- 已有 MRE 生成能力
- 可存储历史缺陷到知识库
- 定期重放验证

**资源需求**:
- 开发时间: 1-2 周
- 存储: ChromaDB 已就绪

**风险评估**:
- 数据库版本更新可能导致误报
- 需要版本感知机制

**优先级**: P2

---

### 4.3 方向优先级排序

| 优先级 | 方向 | 类型 | 预计周期 | 推荐理由 |
|--------|------|------|----------|----------|
| **P0** | 学术论文产出 | 文档 | 3-4 周 | 建议增加对比实验（vs 基线方法），核心创新点：双层门控+四型决策树+契约回退+多DB适配 |
| **P1** | Type-1/Type-3 缺陷检测率提升 | 核心 | 2-4 周 | **细化**: Type-1需放宽L1+定向用例; Type-3需增强传统预言机(单调性+一致性+幂等性+维度校验); 目标 Type-1≥15%, Type-3≥10% |
| **P1** | 可视化报告系统 | 功能 | 1-2 周 | **细化**: 需先修复 dashboard/app.py 导入错误(删除 src.roadmap 引用), 再实现缺陷分布图/趋势图/实时监控 |
| **P2** | 性能优化 | 技术 | 1-2 周 | **细化**: 文档爬取缓存命中率优化 + LLM调用Token预算精细化 + Docker容器预热复用 |
| **P2** | 自动化回归测试 | 功能 | 1-2 周 | 基于MRE知识库的定期重放验证框架 |
| **P3** | 跨数据库支持扩展 (Pinecone/Chroma) | 功能 | 2-3 周/库 | Milvus/Qdrant/Weaviate 已完成，扩展性工作 |
| **P3** | 代码健康度修复 | 工程 | 3 天 | 消除硬编码(容器名→配置化)、修复Dashboard导入、统一版本号标注 |
| **P3** | CI/CD 集成 | 工程 | 1 周 | GitHub Actions 工作流，Docker-in-Docker 支持 |

### 4.4 代码级改进建议详细方案

> 本节基于深度代码审查报告 ([IMPROVEMENT_SUGGESTIONS.md](.trae/specs/next-dev-improvement-suggestions-v4.5/IMPROVEMENT_SUGGESTIONS.md)) 整理的 7 个改进方向的具体实施方案。

#### 4.4.1 方向 A: 核心能力均衡化 — Type-1/Type-3 检测率提升

**问题**: 当前缺陷分布严重失衡：Type-4 占 ~91.7%，Type-2 占 ~8.3%，而 **Type-1 和 Type-3 的检出率为 0%**。四型决策树实际上只覆盖了两类缺陷，核心检测能力存在明显盲区。

**证据**:
- v4.5 验证数据（[ROADMAP.md §1.3](#13-v44-验证数据)）
- [agent5_diagnoser.py:76-79](src/agents/agent5_diagnoser.py#L76-L79) — L1 门控采用 Warning 模式导致 `l1_passed=True`，无法进入 Type-1 分支
- [agent4_oracle.py:61-80](src/agents/agent4_oracle.py#L61-L80) — 传统预言机仅检查距离排序单调性，缺少维度一致性、结果数量、metric 范围等校验
- [agent2_test_generator.py:55-80](src/agents/agent2_test_generator.py#L55-L80) — Prompt 策略偏向语义对抗样本（触发 Type-4），缺少 Type-1/Type-3 定向用例

**方案**:

| 子方案 | 目标 | 具体措施 | 涉及文件 |
|--------|------|----------|----------|
| **A.1** | L1 门控策略微调 | 对极端维度值(如 dim=1, dim=99999)采用更严格的 Warning→Soft-Block 策略；增加 `l1_violation_details` 字段记录违规详情 | [agent3_executor.py](src/agents/agent3_executor.py), [agent5_diagnoser.py](src/agents/agent5_diagnoser.py) |
| **A.2** | 传统预言机增强 | 新增性能属性检查：结果数量合理性(top_k 一致性)、向量维度一致性、距离范围合法性(L2≥0, COSINE∈[-1,1])、幂等性校验 | [agent4_oracle.py](src/agents/agent4_oracle.py) |
| **A.3** | 定向测试生成 | Agent2 新增 Type-1/Type-3 专用 prompt 模板和用例变异策略；要求 ≥20% 用例靶向 Type-1，≥15% 靶向 Type-3 | [agent2_test_generator.py](src/agents/agent2_test_generator.py) |

**预期收益**: 缺陷类型覆盖率从 40%（2/5 类） → ≥80%（4/5 类）；Type-1 检出率 0% → ≥15%；Type-3 检出率 0% → ≥10%

---

#### 4.4.2 方向 B: Dashboard 可视化完善

**问题**: `dashboard/app.py` 存在 ImportError 导致无法启动，且缺乏与主流水线的集成机制。

**证据**: [dashboard/app.py:36](src/dashboard/app.py#L36) 中 `from src.roadmap import Roadmap` 引用了不存在的 `Roadmap` 类

**方案**:

| 子方案 | 目标 | 具体措施 |
|--------|------|----------|
| **B.1** | 修复导入错误 | 删除无效的 `from src.roadmap import Roadmap`，替换为直接读取 `.trae/runs/` 目录和 telemetry 数据 |
| **B.2** | 实现核心面板 | 缺陷类型分布饼图(Type-1/2/2.PF/3/4)、迭代趋势折线图、Agent 耗时热力图 |
| **B.3** | 多 run 对比视图 | 支持选择不同 run 进行缺陷分布和性能指标对比 |

**技术栈**: Streamlit + Plotly；新建 `src/dashboard/data_service.py`(数据服务层) + `src/dashboard/components.py`(可视化组件)

**预期收益**: 用户体验显著提升，调试效率提高，为学术论文提供可视化实验结果支撑

---

#### 4.4.3 方向 C: 学术论文路径规划

**核心创新点提炼** (可用于论文 Contribution 声明):

1. **双层门控机制 (Dual-Layer Validity Model)** — L1 抽象合法性 + L2 运行时就绪性的分层拦截
2. **四型决策树分类法 (Four-Type Defect Taxonomy)** — 基于 Contract Theory 的缺陷归因框架
3. **契约回退系统 (Contract Fallback Mechanism)** — LLM 提取失败时自动填充领域知识
4. **多数据库适配框架** — 统一抽象层支持 Milvus/Qdrant/Weaviate
5. **RAG-guided Mutation Testing** — 利用历史缺陷知识库引导用例变异

**对比实验设计建议**:
- **基线方法**: Random Testing / Rule-based Fuzzing / Property-based Testing (Hypothesis)
- **评估指标**: defect_detection_rate, type_coverage, time_to_first_defect, cost_per_defect, false_positive_rate
- **投稿目标首选**: IEEE TSE / ISSTA；备选: ASE / ICST

---

#### 4.4.4 方向 D: 性能优化（<10 分钟目标）

**当前瓶颈分析**:

| 瓶颈环节 | 占比预估 | 根因 |
|----------|----------|------|
| 文档爬取 (Crawl4AI BFS 3层) | 30-40% | 每次运行重新爬取，HTML 解析耗时 |
| LLM 调用累积 | 40-50% | 4 轮迭代 x 3 次 LLM 调用 = 12 次，Token 数随上下文增长 |
| Docker 容器冷启动 | 10-15% | IsolatedCodeRunner 每次创建新容器 |

**优化方案**:

| 子方案 | 措施 | 预期效果 |
|--------|------|----------|
| D.1 文档缓存持久化 | TTL 7 天 + 增量更新 + 版本哈希校验 | 爬取时间 ~5min → <1min(命中缓存) |
| D.2 LLM 调用并行化 | Agent4 批量评估并行化(ThreadPoolExecutor) | LLM 耗时 ~7min → ~5min(-29%) |
| D.3 Docker 容器预热池 | 维护最小空闲容器数(2个)，后台预热循环 | 冷启动 ~2min → <30s(-75%) |

**综合目标**: 单轮运行时间 ~15 min → <10 min (-33%)

---

#### 4.4.5 方向 E: 自动化回归测试框架

**现状**: `tests/unit/` 已覆盖状态管理、去重算法、异常处理等单元测试，但缺少系统级回归测试。

**缺失的关键回归测试**:
- Agent 流水线端到端测试
- 四型决策树分类正确性验证（各分支路径）
- 多数据库适配器兼容性测试
- 配置变更影响测试
- 性能回归检测（超过基线 20% 告警）

**实施方案**:
- 新建 `tests/regression/` 目录结构（conftest.py + 6 个核心测试模块）
- 核心用例: 决策树参数化路径测试（覆盖 Type-1/2/2.PF/3/4/无缺陷 全部场景）
- 新建 `tests/benchmarks/test_runtime_regression.py` 性能基线追踪
- 配置 `pytest.ini` 支持 `--cov` + `--junitxml` 输出

**预期收益**: 代码变更后自动验证核心逻辑正确性；可作为 PR 合并前置条件

---

#### 4.4.6 方向 F: 代码健康度修复（3 个具体 Bug）

| Bug 编号 | 位置 | 问题 | 修复方案 |
|----------|------|------|----------|
| **F-1** | [agent5_diagnoser.py:24](src/agents/agent5_diagnoser.py#L24) | 容器名硬编码 `"milvus-standalone"` | 改为从 config/env 读取: `os.getenv("TARGET_DB_CONTAINER", "milvus-standalone")` |
| **F-2** | [dashboard/app.py:36](src/dashboard/app.py#L36) | 导入不存在的 `Roadmap` 类 | 删除该行，改为 `from src.dashboard.data_service import DashboardDataService` |
| **F-3** | [AGENTS.md:3](AGENTS.md#L3) | 版本号标注 v4.4（实际应为 v4.5） | 更新头部版本声明为 v4.5 |

**附加改进**: 建立 `.trae/config.yaml` 配置中心化机制，统一管理 target_database.name、container_name、version 等参数

**预计工期**: 3 天

---

#### 4.4.7 方向 G: CI/CD 集成

**GitHub Actions 工作流设计** (`.github/workflows/ci.yml`):

```yaml
Jobs:
  lint-and-format:    # flake8 + black + isort 检查
  unit-tests:          # pytest tests/unit/ --cov
  regression-tests:    # pytest tests/regression/ (PR 触发)
  build-verification:  # 导入验证 + 配置有效性检查 (main 分支)
```

**Release 自动化** (`.github/workflows/release.yml`):
- 触发条件: push tag `v*`
- 自动生成 Changelog + 创建 GitHub Release

**依赖**: GitHub Secrets 管理 `DEEPSEEK_API_KEY`；Docker-in-Docker 支持数据库集成测试

**预计工期**: 3 天（基础 CI）+ 1 天（Release 流程）

---

## 五、里程碑规划

### 5.1 短期目标 (1-2 月)

| 里程碑 | 目标 | 交付物 |
|--------|------|--------|
| **M1** | 学术论文初稿 | 论文草稿、实验数据整理 |
| **M2** | 可视化报告系统 v1.0 | Web Dashboard |
| **M3** | 技术报告整理 | 完整技术报告文档 |

### 5.2 中期目标 (3-4 月)

| 里程碑 | 目标 | 交付物 |
|--------|------|--------|
| **M4** | 缺陷检测精度提升 | Type-1/Type-3 检测率提升 |
| **M5** | Qdrant 数据库支持 | QdrantAdapter 实现 |
| **M6** | 性能优化 | 单次运行 <10 分钟 |

### 5.3 长期目标 (5-6 月)

| 里程碑 | 目标 | 交付物 |
|--------|------|--------|
| **M7** | 学术论文投稿 | 论文投稿 |
| **M8** | 自动化回归测试 | 回归测试框架 |
| **M9** | CI/CD 集成 | GitHub Action 工作流 |

---

## 六、资源需求

### 6.1 人力资源

| 角色 | 需求 | 职责 |
|------|------|------|
| 核心开发者 | 1 人 | 功能开发、性能优化 |
| 测试工程师 | 0.5 人 | 验证测试、回归测试 |
| 文档工程师 | 0.5 人 | 技术报告、论文撰写 |

### 6.2 计算资源

| 资源 | 需求 | 用途 |
|------|------|------|
| LLM API | DeepSeek/Anthropic/智谱 | Agent 推理 |
| Docker 环境 | Milvus + etcd + minio | 测试环境 |
| GPU (可选) | CUDA 支持 | SentenceTransformer 加速 |

### 6.3 预算估算

| 项目 | 月度成本 | 说明 |
|------|----------|------|
| LLM API | ¥200-500 | 按调用量计费 |
| 云服务器 (可选) | ¥100-300 | CI/CD 环境 |
| **合计** | ¥300-800/月 | |

---

## 七、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM API 成本超支 | 中 | 高 | 设置 Token 预算熔断 |
| 数据库版本兼容性 | 中 | 中 | 版本感知 + 契约适配 |
| 学术论文投稿失败 | 低 | 高 | 多期刊备选 |
| 跨数据库适配困难 | 中 | 中 | 优先适配 API 相近的数据库 |

---

## 八、附录

### A. 参考文档

- [README.md](README.md) - 项目入口文档
- [AGENTS.md](AGENTS.md) - Agent 架构设计文档
- [SPECS_INDEX.md](.trae/specs/SPECS_INDEX.md) - 开发规格索引

### B. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.2 | 2026-04-06 | 升级至 v4.5 基准；补充 7 项核心能力（EnhancedDeduplicator/IsolatedCodeRunner/EmbeddingGenerator/ReferenceValidator/DocumentCache/DockerContainerPool/CompressionUtils）；开题目标 #2 完成度 90%→95%，新增跨数据库框架目标；新增 Type-1/Type-3 缺陷检测率差距(P1)；方向1 标记 Qdrant/Weaviate 完成，优先级降为 P3；P1 新增缺陷检测率提升项 |
| v1.3 | 2026-04-06 | 基于代码深度审查补充改进建议；新增 §4.4 代码级改进详细方案(7个方向：A核心能力均衡化/B Dashboard可视化/C学术论文/D性能优化/E回归测试/F代码健康度/G CI-CD)；差距表新增代码健康度项(P3)；优先级表补充细化的实施路径和量化目标；§3.2 新增差距4详细说明(硬编码/导入错误/版本不一致) |
| v1.0 | 2026-04-05 | 初始版本，基于 v4.4 状态 |
