# Spec 版本索引

> AI-DB-QC 项目规格（Spec）目录总览，共 28 个 spec 目录。
> 当前活跃版本：**v4.x** | 归档历史：**v3.2 ~ v3.7**

---

## v4.x 活跃规格 (Active)

| Spec 目录 | 说明 |
|-----------|------|
| **project-cleanup-v4.4** ⭐ | **当前 Spec** — 项目整理 & 文档更新：清理根目录散落脚本/过期日志、创建 README.md 入口、更新 AGENTS.md、归档老版本 spec |
| **live-run-v4.4** ✅ | **最新验证通过** — L2 门控修复实战验证：修复 `state.current_collection` 未赋值导致 L2 门控 100% 失败的 bug，验证四型分类决策树多分支触发（max_iterations=4） |
| **automate-docs-pipeline** | Agent0 文档预处理自动化 + 契约门控对齐：cache-first 策略、契约 fallback 规则库、L1+L2 双层门控完整实现、四型分类决策树严格对齐理论框架 |
| **live-run-v4.3** | v4.3 实战验证运行：验证文档缓存命中、allowed_dimensions 填充、L1/L2 门控日志输出、四型分类结果分布（max_iterations=6） |
| **relax-l1-gating-and-diversity** | 放宽 L1 门控 + 增强测试多样性：允许维度不匹配测试执行并记录为 Type-1 缺陷、Agent2 prompt 增加多样性约束、论文搜索可行性评估 |
| **live-run-6-iter-v4.1** | 6 轮完整实战运行：虚拟环境隔离、依赖安装验证、完整 Agent0→6 流程执行、实时问题修复 |

---

## v3.x 归档规格 (Archived)

### 📋 审计与评估 (Audit & Evaluation)

| Spec 目录 | 说明 |
|-----------|------|
| `ai_db_qc_current_state` | 项目现状分析：v3.5.2 版本全模块状态评估、识别待优化领域、制定改进计划 |
| `project-audit-v3.2` | 首次全量审计：10 轮以上 Fuzzing 实战、理论框架符合性分析、Issue 质量专项审计（链接有效性/MRE 可复现/证据链完整性） |
| `project-audit-v3.3` | 第二轮项目审计 |
| `project-audit-v3.4` | 第三轮项目审计 |
| `project-evaluation-v3.5.3` | 实战评估：验证深度爬取效果（文档量 5-10x）、产出文件质量、系统性能（含 EVALUATION_REPORT.md） |
| `project-evaluation-v3.6.0` | 评估报告（含 EVALUATION_REPORT.md） |
| `live-evaluation-v3.7.0` | v3.6.1 修复后完整实战评估：缺陷验证一致性深度审查、误报率分析、客观评估报告（含 EVALUATION_REPORT.md） |
| `analyze-defect-efficiency` | 缺陷产出效率分析：对比 6 轮 vs 3 轮运行数据，根因分析（L1 过滤率高/发现随机性/去重阈值），提出放宽门控等 3 项建议 |

### 🔧 功能增强 (Feature Enhancement)

| Spec 目录 | 说明 |
|-----------|------|
| `enhance-documentation-pipeline` | 文档爬取与分析增强：扩展至 5-8 个 URL、新增结构化 doc_parser、混合 RAG（语义+BM25）、引用相关性验证器 |
| `deep-crawling-optimization` | 深度爬取能力优化：Crawl4AI 深度 3 层递归爬取、智能同域名链接过滤、爬取进度监控、文档去重 |
| `enhance-mre-real-vectors` | MRE 真实语义向量注入：检测占位符模式（uniform/random/手写简单值）并替换为 SentenceTransformer 生成的真实嵌入向量 |
| `expand-mre-vector-coverage` | 扩展 MRE 向量覆盖面：Pattern 从 3 种扩展到 5 种（新增列表推导式/嵌套数据结构匹配），LLM Prompt 格式约束引导 |
| `upgrade-harness-v3.3` | 测试台升级 v3.3：恢复 Crawl4AI（Chromium headless）、意图-数据闭环生成（expected_ground_truth）、MRE 自动化自校验 |
| `refactor-harness-v3.4` | 智能测试台重构 v3.4：MRE 验证精细化（区分语法错误 vs 真实 Bug）、自适应爬虫二级回退（Community/Wiki）、语料库去噪 |
| `adversarial-fuzzing-v3.5` | 对抗性攻击升级：攻击性变异算子（契约违约/时序混沌）、Agent3 放行模式（透传+观测）、四型缺陷判定重构、Cross-Encoder Reranker、万级维度压力注入 |
| `tag-contract-sources` | 深度契约提取与来源标注：时序契约（operational_sequences）、全参数深度覆盖、source_url 标注贯穿全流程 |
| `upgrade-semantic-deduplication` | 语义去重升级：从字符截断（前50字符）升级为多维相似度（bug_type/operation/error_message/semantic 四维加权），sentence-transformers 向量化 |
| `optimize-runtime-and-logging` | 运行时性能优化：本地 RAG 缓存层（增量更新/TTL）、Docker 沙箱连接池、异步日志+文件轮转（50MB）、隔离式 MRE 验证环境 |
| `use-local-docs-library-v2.6` | 本地文档库模式：从 JSONL 加载 Milvus v2.6.x 文档、禁用 Crawl4AI 自动爬取、版本过滤、Fail Fast 策略 |

### 🐛 关键修复 (Bug Fix)

| Spec 目录 | 说明 |
|-----------|------|
| `fix-critical-issues-v3.5.4` | P0 修复：Crawl4AI 兼容性（移除不支持的 API）、Windows 数据库权限（临时目录）、证据相关性过滤（≥0.6 相似度）、MRE 真实向量、状态压缩 50%+ |
| `fix-critical-issues-v3.6.1` | P0 修复：去重器初始化 NoneType 崩溃、异步遥测队列刷新、优化功能可观测性日志、psutil 性能监控、缺陷验证与报告一致性（避免误报） |
| `fix-p0-and-regenerate-issues` | P0 修复：agent6 docs_context 6.6MB 超出 token 限制 → 智能截断至 8000 字符/缺陷 + 按需检索；补生成 _regenerate_issues.py 脚本产出 GitHub Issue |

### 🏃 实战验证 (Live Run / Verification)

| Spec 目录 | 说明 |
|-----------|------|
| `execution-run-local-docs-v1` | 使用本地文档的生产级回归测试：零 Mock/零硬编码、实时观测诊断、阻塞性报错必须当轮修复 |
| `verify-doc-references-v3.5.2` | 文档引用真实性验证：5 轮迭代验证 PRE-VALIDATED 引用机制，确保 Issue 引用均来自 raw_docs.json 真实文本 |
| `live-run-verify-v4.2` | L1 门控放宽 + 多样性增强实战验证：验证 Type-1 缺陷生成、缺陷分布均匀性、产出数量提升（max_iterations=6） |

---

## 版本演进时间线

```
v3.2  ──┬── enhance-documentation-pipeline     文档管道增强
       ├── project-audit-v3.2                  首次全量审计
       │
v3.3  ──┼── upgrade-harness-v3.3               测试台升级（Crawl4AI恢复/闭环生成）
       ├── project-audit-v3.3                  第二轮审计
       │
v3.4  ──┼── refactor-harness-v3.4              测试台重构（MRE精细化/回退机制）
       ├── project-audit-v3.4                  第三轮审计
       │
v3.5  ──┼── upgrade-semantic-deduplication     语义去重升级
       ├── tag-contract-sources                深度契约提取+来源标注
       ├── verify-doc-references-v3.5.2        引用真实性验证
       ├── adversarial-fuzzing-v3.5             对抗性攻击升级（四型全覆盖）
       ├── deep-crawling-optimization           深度爬取优化（3层递归）
       ├── enhance-mre-real-vectors            MRE真实向量注入
       ├── fix-critical-issues-v3.5.4          P0修复（兼容性/权限/证据）
       ├── project-evaluation-v3.5.3           评估报告
       ├── expand-mre-vector-coverage          MRE覆盖面扩展（3→5 Pattern）
       ├── fix-p0-and-regenerate-issues        P0修复（docs_context膨胀）
       ├── use-local-docs-library-v2.6         本地文档库模式
       ├── ai_db_qc_current_state              项目现状分析
       │
v3.6  ──┼── optimize-runtime-and-logging       性能优化（缓存/连接池/日志轮转）
       ├── project-evaluation-v3.6.0           评估报告
       ├── fix-critical-issues-v3.6.1          P0修复（去重器/遥测/一致性）
       │
v3.7  ──┼── live-evaluation-v3.7.0            完整实战评估
       │
v4.1  ──┼── live-run-6-iter-v4.1              6轮完整实战（venv隔离）
       │
v4.2  ──┼── live-run-verify-v4.2              L1放宽+多样性验证
       ├── analyze-defect-efficiency           缺陷效率分析
       ├── relax-l1-gating-and-diversity       L1放宽+多样性增强
       │
v4.3  ──┼── automate-docs-pipeline             文档自动化+契约门控+四型分类
       ├── live-run-v4.3                      v4.3实战验证
       │
v4.4  ──┴── live-run-v4.4 ✅                   L2门控修复验证（最新通过）
            project-cleanup-v4.4 ⭐             当前Spec（项目整理）
```

---

## 快速查找指南

**想了解某功能何时引入？**
- 双层门控 (L1+L2) → `automate-docs-pipeline` (v4.3)
- 四型分类决策树 → `adversarial-fuzzing-v3.5` (v3.5) 引入 → `automate-docs-pipeline` (v4.3) 对齐
- MRE 真实向量 → `enhance-mre-real-vectors` (v3.5) → `expand-mre-vector-coverage` 扩展
- 本地文档库 → `use-local-docs-library-v2.6` (v3.5)
- 语义去重 → `upgrade-semantic-deduplication` (v3.5)
- 深度爬取 → `deep-crawling-optimization` (v3.5)

**含评估报告的 Spec（有 EVALUATION_REPORT.md）：**
- `project-evaluation-v3.5.3`
- `project-evaluation-v3.6.0`
- `live-evaluation-v3.7.0`
