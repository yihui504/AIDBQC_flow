# AI-DB-QC 实战评估 v3.7.0 Spec

## 为什么
在完成 `fix-critical-issues-v3.6.1` 的所有修复（去重器初始化、遥测文件生成、性能监控、缺陷验证一致性）后，需要执行一轮完整的实战运行，以验证所有修复的实际效果，并基于客观事实产出冷静、不谄媚的评估报告。

**关键背景**：
- 上轮评估 (v3.6.0) 已完成，但 Task 5（内容质量审查）和 Task 6（性能评估）部分未完成
- v3.6.1 修复规范中 Task 6.6（重新跑一轮并评估产出）仍待执行
- 用户已自行做了多轮代码更新（删除了 mre_generator.py、generators 包等）
- 系统配置了网络代理，LLM 调用和 web_search 需按需使用

## 文档来源策略（重要）

**本次评估不使用 Crawl4AI 实时爬取功能。**

文档来源固定为本地官方文档库：
- 文件路径：`.trae/cache/milvus_io_docs_depth3.jsonl`
- 配置方式：`config.yaml` 中 `docs.source: "local_jsonl"`
- 加载方式：agent0 通过 `LocalDocsLibrary.load_docs_context()` 加载
- 内容范围：Milvus v2.6.x 官方文档（从 milvus.io/docs 爬取的深度为 3 的 JSONL 文件）

评估重点不在爬取功能本身，而在：
1. 本地文档库能否被正确加载和使用
2. 基于这些文档生成的缺陷报告质量如何
3. Issue 中的证据引用是否来自该文档库且真实可信

## 变更内容
- 执行一次完整的项目实战运行（max_iterations=3）
- 全程监视每个智能体的行为和输出
- 对所有产出文件进行严格审查
- 基于实际数据生成客观评估报告
- 提供具体可操作的进一步改进建议

## 影响
- 受影响范围：整个 AI-DB-QC 系统
- 评估对象：v3.7.0（包含 v3.5.4 + v3.6.0 + v3.6.1 所有修复）
- 关键关注点：
  - **本地文档库加载与使用**：milvus_io_docs_depth3.jsonl 是否正确加载，docs_context 是否正确传递给下游 agent
  - **缺陷验证与报告一致性**：误报率是否下降、expected_rejection 是否正确归类
  - **verified_defects 落盘**：是否正确聚合写入 state
  - **MRE 代码质量**：是否使用真实语义向量、代码是否可运行
  - **GitHub Issue 质量**：格式、证据引用真实性、MRE 可复现性
  - **遥测数据完整性**：telemetry.jsonl 是否有完整事件序列
  - **系统稳定性**：是否有崩溃、内存泄漏、资源未释放

## ADDED Requirements

### Requirement: 完整实战执行
系统 SHALL 能够从启动到结束完整执行 AI-DB-QC 流水线，所有智能体按预定顺序执行无崩溃。

#### 场景：成功运行
- **WHEN** 执行 `python main.py`
- **THEN** 系统按以下顺序执行：agent0 → agent1 → agent2 → agent3 → reranker → agent4 → agent5 → coverage_monitor → (fuzz 循环 max_iterations=3) → agent6 → reflection → END
- **AND** 每个节点完成后有明确的日志输出
- **AND** 最终生成缺陷报告和/或 GitHub Issue 文件
- **验证**：检查控制台日志和 .trae/runs/run_xxxx/ 目录

### Requirement: 本地文档库正确使用
系统 SHALL 使用 `.trae/cache/milvus_io_docs_depth3.jsonl` 作为唯一文档来源，正确加载并传递给下游智能体。

#### 场景：文档加载成功
- **WHEN** agent0 执行时
- **THEN** LocalDocsLibrary 成功读取 milvus_io_docs_depth3.jsonl
- **AND** 日志显示加载了多少条文档、过滤了多少条
- **AND** docs_context 正确写入 state.db_config
- **AND** raw_docs.json 在运行目录中保存了完整文档快照

### Requirement: 过程行为监视
系统 SHALL 在运行过程中提供充分的可观测性，便于事后分析每个智能体的行为质量。

#### 场景：行为记录
- **WHEN** 每个智能体执行时
- **THEN** 控制台输出包含：输入摘要、处理过程、输出摘要、耗时
- **AND** telemetry.jsonl 记录每次执行的 token 消耗和状态变更
- **AND** 异常情况有清晰的错误堆栈

### Requirement: 产出严格审查
对所有产出文件进行逐项严格审查，不放过任何问题。

#### 审查维度：
1. **运行日志**：是否有未处理的异常、是否有静默失败
2. **State 文件**：state.json.gz 是否正确压缩和解压、字段完整性
3. **Defect Reports**：defect_reports 列表数量、每条报告的字段完整性
4. **GitHub Issues**：格式是否符合模板、MRE 代码是否可运行、证据引用是否真实（来自 milvus_io_docs_depth3.jsonl）
5. **Verified Defects**：verified_defects 数量是否合理、verifier_verdict 分布
6. **Telemetry 数据**：telemetry.jsonl 是否有完整的事件序列
7. **Reflection 输出**：总结是否基于实际发现的缺陷

### Requirement: 缺陷验证一致性深度审查
这是本次评估的核心关注点之一，直接检验 v3.6.1 修复效果。

#### 审查指标：
- reproduced_bug / expected_rejection / invalid_mre / inconclusive 的分布
- expected_rejection 的判定是否准确（"预期拒绝"不应标记为 bug）
- false_positive 标记仅用于确实不是缺陷的情况
- verified_defects 与 defect_reports 中 reproduced_bug=True 的数量一致
- verification_log 与 verdict 无矛盾

### Requirement: 客观评估报告
生成一份完全基于事实的评估报告，拒绝谄媚。

#### 报告要求：
- **客观性**：所有结论必须有具体的数据或日志证据支持
- **批判性**：不回避问题，明确指出不足之处
- **具体性**：不说空话，每个问题都有具体的位置和现象描述
- **可操作性**：改进建议必须可直接执行

#### 报告结构：
1. 运行概况（时间、Token 消耗、各阶段耗时、迭代次数）
2. 文档库使用情况（加载条数、过滤情况、总字符数）
3. 流程完整性评估（哪些节点成功/失败/异常）
4. 产出质量评估（逐项打分，附具体证据）
5. 缺陷验证一致性专项分析（verdict 分布、误报率、典型案例）
6. 核心问题清单（P0/P1/P2 排序，每条有具体证据）
7. 改进建议（短期 < 1天 / 中期 < 1周 / 长期 > 1周）

## MODIFIED Requirements

### Requirement: 评估焦点调整
**修改前**：关注 Crawl4AI 爬取功能
**修改后**：关注本地文档库 (milvus_io_docs_depth3.jsonl) 的使用效果和基于此文档的产出质量

## REMOVED Requirements
无

## 评估方法

1. **执行运行**：`python main.py`，全程捕获输出
2. **实时监视**：观察控制台输出，记录异常
3. **产出审查**：运行结束后逐一检查产出文件
4. **数据分析**：解析 telemetry.jsonl 和 state.json.gz
5. **证据交叉验证**：Issue 中的引用与 milvus_io_docs_depth3.jsonl 原文对照
6. **报告撰写**：基于以上所有信息撰写评估报告

## 验收标准

1. 项目成功运行到 completion 或可控终止
2. 本地文档库被正确加载和使用
3. 所有产出文件经过逐项审查
4. 缺陷验证一致性得到量化评估
5. 评估报告基于事实，不含主观美化
6. 问题识别覆盖所有关键方面
7. 改进建议具体可操作
