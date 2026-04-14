# AI-DB-QC v4.5 项目现况深入介绍 HTML 页面 Spec

## Why
项目历经 v1→v4.5 多轮迭代，已形成完整的多智能体向量数据库质量保证框架，并完成了 Milvus/Qdrant/Weaviate 三库实战验收。需要一份专业的 HTML 介绍页面，向混合受众（技术同行、资助方、开源社区）全面、深入地展示项目架构、理论框架、核心机制与实战成果。

## What Changes
- 创建单文件 HTML 页面 `project_overview.html`，包含项目完整介绍
- 包含 Python 数据提取脚本 `_extract_overview_data.py`，从 `.trae/runs` 提取真实数据写入 HTML
- 使用 Chart.js (CDN) 实现数据图表
- 使用 Prism.js (CDN) 实现代码语法高亮
- 使用 mermaid.js (CDN) 渲染流程图
- 使用 HTML/CSS 手绘决策树和循环示意图

## Impact
- Affected code: 无代码变更，纯新增交付物
- 新增文件: `project_overview.html`, `_extract_overview_data.py`

## ADDED Requirements

### Requirement: 页面整体结构
系统 SHALL 生成一个单文件 HTML 页面，采用单页长滚动 + 侧边二级目录导航布局，仅适配桌面浏览器。

#### Scenario: 页面加载
- **WHEN** 用户在浏览器中打开 `project_overview.html`
- **THEN** 页面完整渲染，侧边导航可点击跳转，所有图表和流程图正常显示

### Requirement: 视觉风格
页面 SHALL 采用简洁学术风：学术蓝配色方案、宋体/Georgia 字体、混合风格内容区块（重要内容用卡片，次要内容扁平）、学术简洁表格样式。

#### Scenario: 视觉一致性
- **WHEN** 页面渲染完成
- **THEN** 所有章节遵循统一的配色、字体和间距规范

### Requirement: 页面头部
页面顶部 SHALL 显示简洁标题栏：项目名称 + v4.5 版本号 + 一句话描述。

### Requirement: 页面底部
页面底部 SHALL 显示简洁页脚：项目名 + 生成日期。

### Requirement: 交互元素
页面 SHALL 提供：侧边二级目录导航（点击锚点跳转）、可折叠章节（代码示例/详细表格/子组件默认折叠）、回到顶部浮动按钮、适度动画（滚动淡入、图表加载动画、悬停效果）。

### Requirement: 章节编排顺序
页面章节 SHALL 按以下顺序编排：
1. 项目概述（完整背景故事：问题定义、动机、与现有工具对比、核心创新点）
2. 核心架构（9 Agent 流水线总览 + 完整协作流程图）
3. 理论框架（四型分类法、双层有效性模型、三层契约、智能预言机）
4. 逐 Agent 详细介绍（统一卡片模板：编号+功能名称、职责、输入输出、核心工具）
5. 关键子系统详解（L2门控、Reranker、Docker日志探测、去重系统、MRE验证流水线、文档预处理、多轮循环、覆盖率监控、熔断自愈、状态管理、适配器层）
6. 实战验收成果（三库汇总表格+分析、4个数据图表）
7. 精选 Top Issue 案例（完整案例卡片）
8. 技术栈（完整技术栈+选型理由）
9. 补充内容（项目目录结构、配置文件说明、运行指南）

### Requirement: 项目概述章节
概述 SHALL 包含：向量数据库测试痛点问题定义、项目动机、与现有测试工具（如 fuzzing、传统单元测试）的对比、核心创新点（契约驱动+LLM语义生成+四型分类）。

### Requirement: 核心架构章节
架构章节 SHALL 包含：
- 9 Agent + Reranker + Reflect 的流水线总览
- mermaid 渲染的完整协作流程图（主循环+旁路验证流+Recovery恢复流）
- Agent 间数据流转说明

### Requirement: 理论框架章节
理论框架 SHALL 完整展开全部理论模块：
1. **四型缺陷分类法**：Type-1/2/2.PF/3/4 完整详解+示例，用 HTML/CSS 手绘决策树
2. **双层有效性模型**：L1 抽象合法性 + L2 运行时就绪性，完整机制详解
3. **三层契约系统**：L1 API/L2 Runtime/L3 Semantic 完整展开（含字段示例），契约回退和热修补简要提及
4. **智能预言机**：传统预言机+LLM语义预言机的分层验证机制

### Requirement: Agent 详细介绍章节
每个 Agent SHALL 使用统一卡片模板展示：
- 编号+功能名称（混合显示，如 "Agent 3 - 执行与前置门控官"）
- 核心职责
- 输入/输出
- LLM核心能力/工具
- 关键代码片段（可折叠）

9 个 Agent：Agent 0(环境侦察) → Agent 1(场景分析) → Agent 2(测试生成) → Agent 3(执行门控) → Reranker(重排序) → Agent 4(预言机) → Agent 5(缺陷诊断) → Agent 6(缺陷验证) → Reflect(反思总结)

### Requirement: 关键子系统详解章节
以下子系统 SHALL 各自独立小节，完整详解：

1. **L2 运行时门控**：门控流程图、状态字段维护、与决策树关联、自适应契约演化
2. **Reranker 重排序**：Cross-Encoder 模型、重排序流程、容错降级策略
3. **Docker 日志探测**：DockerLogsProbe 触发条件、采集参数、数据结构、与决策树集成
4. **智能语义去重**：四维相似度计算（语义0.5+结构0.3+行为0.1+上下文0.1）、ChromaDB混合搜索、阈值判定策略、去重率数据
5. **MRE 验证流水线**：EmbeddingGenerator（7种占位符模式+替换策略+容错机制）、IsolatedCodeRunner（Docker沙箱配置+资源限制+执行流程+容错降级）、ReferenceValidator（验证逻辑+阈值设置+VerifiedReference结构）
6. **文档预处理流水线**：缓存策略、深度爬取、Filter-Validate-Save 管线、URL映射表
7. **多轮自适应测试循环**：HTML/CSS 手绘循环示意图、终止条件、反馈生成策略、Web搜索触发机制
8. **覆盖率监控**：覆盖率模型、计算方法、监控策略、终止条件
9. **智能熔断器与自愈节点**：熔断器阈值、自愈节点逻辑、Recovery 模式流程
10. **状态管理**：WorkflowState 字段、压缩存储、版本管理、增量保存
11. **数据库适配器层**：接口定义+三库差异对比表+扩展方法

### Requirement: 实战验收成果章节
实战成果 SHALL 包含：
- 三库（Milvus/Qdrant/Weaviate）汇总数据表格+关键差异分析文字
- 4 个 Chart.js 图表：
  1. 缺陷类型分布饼图（Type-1/2/2.PF/3/4 各类型数量）
  2. 三库对比柱状图（缺陷数、去重率、MRE验证率）
  3. Token 消耗分布图（Agent0-6 各节点占比）
  4. 去重效果对比图（去重前后缺陷数量变化）
- 数据从 `.trae/runs` 最近运行结果中手动提取写入

### Requirement: 精选 Top Issue 案例章节
每个库选 Top 3-5 个最有价值的 Issue，使用完整案例卡片展示：
- Issue 标题
- 缺陷类型+评分
- MRE 代码片段（可折叠，Prism.js 高亮）
- 关键证据摘要

### Requirement: 技术栈章节
完整技术栈+选型理由，按类别分组：
- 核心框架（LangGraph、LangChain、Pydantic）
- LLM 服务（智谱 GLM-4-Plus/Flash）
- 向量数据库客户端（pymilvus、qdrant-client、weaviate-client）
- 嵌入模型（SentenceTransformer、CrossEncoder）
- 基础设施（Docker、ChromaDB）
- 每项说明选型理由

### Requirement: 补充内容章节
1. **项目目录结构**：核心目录级别树形图
2. **配置文件说明**：完整配置参考（所有配置项+默认值+说明）
3. **运行指南**：完整运行指南（环境准备+配置+启动命令+参数说明）

### Requirement: 代码示例
页面 SHALL 包含以下 4 个代码示例（Prism.js 高亮，默认折叠）：
1. 契约定义示例（L1/L2/L3 契约的 Pydantic 定义）
2. L2 门控检查示例（门控检查的代码逻辑）
3. 决策树分类示例（四型分类的判定逻辑）
4. MRE 生成示例（生成的 MRE 代码样例）

### Requirement: 数据图表
页面 SHALL 使用 Chart.js (CDN) 渲染 4 个交互式图表，数据手动从运行结果提取写入 HTML 内联 JSON。

### Requirement: 流程图
页面 SHALL 使用 mermaid.js (CDN) 渲染多 Agent 协作流程图。决策树和循环示意图使用 HTML/CSS 手绘。

### Requirement: 外部依赖
页面 SHALL 通过 CDN 引入以下外部库：
- Chart.js（数据图表）
- Prism.js（代码语法高亮）
- mermaid.js（流程图渲染）

### Requirement: 语言
页面内容 SHALL 以中文为主，技术术语保留英文。

### Requirement: 单文件输出
最终交付 SHALL 为单个 HTML 文件，所有 CSS 和 JS 内联，仅外部 CDN 依赖允许外部引用。
