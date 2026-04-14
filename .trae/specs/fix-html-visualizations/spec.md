# Tasks - 项目现况深入介绍 HTML 页面

* [x] Task 1: 数据提取脚本 - 编写 `_extract_overview_data.py` 从 `.trae/runs` 提取真实数据

  * [x] SubTask 1.1: 提取三库实战验收数据（缺陷数、类型分布、去重率、MRE验证率）

  * [x] SubTask 1.2: 提取 Token 消耗分布数据（各 Agent 节点占比）

  * [x] SubTask 1.3: 提取精选 Top Issue 案例数据（每库 Top 3-5）

  * [x] SubTask 1.4: 输出为 JSON 文件供 HTML 内联使用

* [x] Task 2: HTML 页面骨架 - 创建 `project_overview.html` 基础结构

  * [x] SubTask 2.1: HTML 文档结构（head、meta、CDN 引入、CSS 变量定义）

  * [x] SubTask 2.2: 侧边导航栏（二级目录、锚点跳转、滚动高亮）

  * [x] SubTask 2.3: 页面头部（项目名+v4.5+一句话描述）

  * [x] SubTask 2.4: 页面底部（项目名+生成日期）

  * [x] SubTask 2.5: 回到顶部浮动按钮

  * [x] SubTask 2.6: 可折叠章节组件（CSS+JS）

  * [x] SubTask 2.7: 滚动淡入动画（IntersectionObserver）

* [x] Task 3: 项目概述章节 - 完整背景故事

  * [x] SubTask 3.1: 向量数据库测试痛点问题定义

  * [x] SubTask 3.2: 项目动机与目标

  * [x] SubTask 3.3: 与现有测试工具对比

  * [x] SubTask 3.4: 核心创新点

* [x] Task 4: 核心架构章节 - 9 Agent 流水线

  * [x] SubTask 4.1: Agent 流水线总览文字说明

  * [x] SubTask 4.2: mermaid 完整协作流程图（主循环+旁路+Recovery）

  * [x] SubTask 4.3: Agent 间数据流转说明

* [x] Task 5: 理论框架章节 - 全部理论模块

  * [x] SubTask 5.1: 四型缺陷分类法（完整详解+示例+HTML/CSS手绘决策树）

  * [x] SubTask 5.2: 双层有效性模型（L1+L2 完整机制详解）

  * [x] SubTask 5.3: 三层契约系统（L1/L2/L3 完整展开+字段示例，回退和热修补简要提及）

  * [x] SubTask 5.4: 智能预言机（传统+LLM语义分层验证）

* [x] Task 6: Agent 详细介绍章节 - 统一卡片模板

  * [x] SubTask 6.1: Agent 0 - 环境与情报获取者卡片

  * [x] SubTask 6.2: Agent 1 - 场景与契约分析师卡片

  * [x] SubTask 6.3: Agent 2 - 混合测试生成器卡片

  * [x] SubTask 6.4: Agent 3 - 执行与前置门控官卡片

  * [x] SubTask 6.5: Reranker - 结果重排序智能体卡片

  * [x] SubTask 6.6: Agent 4 - 预言机协调官卡片

  * [x] SubTask 6.7: Agent 5 - 缺陷诊断收集器卡片

  * [x] SubTask 6.8: Agent 6 - 缺陷验证与去重专家卡片

  * [x] SubTask 6.9: Reflect - 反思总结卡片

* [x] Task 7: 关键子系统详解章节 - 11 个子系统

  * [x] SubTask 7.1: L2 运行时门控（流程图+状态字段+决策树关联+自适应演化）

  * [x] SubTask 7.2: Reranker 重排序（Cross-Encoder+流程+容错降级）

  * [x] SubTask 7.3: Docker 日志探测（触发条件+采集参数+数据结构+决策树集成）

  * [x] SubTask 7.4: 智能语义去重（四维相似度+ChromaDB+阈值策略+去重率数据）

  * [x] SubTask 7.5: MRE 验证流水线（EmbeddingGenerator 7种占位符+IsolatedCodeRunner Docker沙箱+ReferenceValidator）

  * [x] SubTask 7.6: 文档预处理流水线（缓存策略+深度爬取+Filter-Validate-Save+URL映射）

  * [x] SubTask 7.7: 多轮自适应测试循环（HTML/CSS手绘循环图+终止条件+反馈策略+Web搜索）

  * [x] SubTask 7.8: 覆盖率监控（模型+计算方法+监控策略+终止条件）

  * [x] SubTask 7.9: 智能熔断器与自愈节点（阈值+自愈逻辑+Recovery流程）

  * [x] SubTask 7.10: 状态管理（WorkflowState字段+压缩存储+版本管理+增量保存）

  * [x] SubTask 7.11: 数据库适配器层（接口定义+三库差异对比表+扩展方法）

* [x] Task 8: 实战验收成果章节 - 三库数据+4图表

  * [x] SubTask 8.1: 三库汇总数据表格+关键差异分析文字

  * [x] SubTask 8.2: Chart.js 缺陷类型分布饼图

  * [x] SubTask 8.3: Chart.js 三库对比柱状图

  * [x] SubTask 8.4: Chart.js Token 消耗分布图

  * [x] SubTask 8.5: Chart.js 去重效果对比图

* [x] Task 9: 精选 Top Issue 案例章节

  * [x] SubTask 9.1: Milvus Top 3-5 Issue 完整案例卡片

  * [x] SubTask 9.2: Qdrant Top 3-5 Issue 完整案例卡片

  * [x] SubTask 9.3: Weaviate Top 3-5 Issue 完整案例卡片

* [x] Task 10: 技术栈章节

  * [x] SubTask 10.1: 按类别分组列出完整技术栈

  * [x] SubTask 10.2: 每项技术附选型理由

* [x] Task 11: 补充内容章节

  * [x] SubTask 11.1: 项目目录结构（核心目录级别树形图）

  * [x] SubTask 11.2: 配置文件说明（完整配置参考）

  * [x] SubTask 11.3: 运行指南（环境准备+配置+启动命令+参数说明）

* [x] Task 12: 代码示例集成

  * [x] SubTask 12.1: 契约定义示例（Pydantic 定义，Prism.js 高亮，默认折叠）

  * [x] SubTask 12.2: L2 门控检查示例

  * [x] SubTask 12.3: 决策树分类示例

  * [x] SubTask 12.4: MRE 生成示例

* [x] Task 13: 最终验证与数据注入

  * [x] SubTask 13.1: 运行数据提取脚本，将真实数据注入 HTML

  * [x] SubTask 13.2: 浏览器打开验证所有图表、流程图、代码高亮正常渲染

  * [x] SubTask 13.3: 验证侧边导航、折叠、回顶按钮等交互功能

# Task Dependencies

* \[Task 1] → \[Task 8], \[Task 9] (数据提取先于成果展示)

* \[Task 2] → \[Task 3-12] (骨架先于内容填充)

* \[Task 5.1] → \[Task 7.1] (决策树先于L2门控关联说明)

* \[Task 6] → \[Task 7] (Agent卡片先于子系统详解)

* \[Task 3-12] → \[Task 13] (所有内容完成后最终验证)

