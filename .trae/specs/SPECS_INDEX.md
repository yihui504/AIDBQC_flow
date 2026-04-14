# Spec 版本索引

> AI-DB-QC 项目规格（Spec）目录总览。
> **活跃版本**: v4.x | **归档历史**: v3.2 ~ v3.7

---

## 🟢 v4.x 活跃规格 (Active)

| Spec 目录 | 状态 | 说明 |
|-----------|------|------|
| **tech-report-and-cross-db-support** | ⭐ 当前 | 技术报告整理 + Qdrant/Weaviate 跨数据库支持 |
| **roadmap-from-proposal** | ✅ 完成 | 基于开题报告的项目发展规划 |
| **project-cleanup-v4.4** | ✅ 完成 | 项目整理 & 文档更新 |
| **live-run-v4.4** | ✅ 验证通过 | L2 门控修复验证，四型分类多分支触发 |
| **automate-docs-pipeline** | ✅ 完成 | 文档预处理自动化 + L1+L2 双层门控 |
| **live-run-v4.3** | ✅ 完成 | v4.3 实战验证 |
| **relax-l1-gating-and-diversity** | ✅ 完成 | L1 门控放宽 + 测试多样性增强 |
| **live-run-6-iter-v4.1** | ✅ 完成 | 6 轮完整实战运行 |

---

## 📦 v3.x 归档规格 (Archived)

> 以下 spec 为历史开发记录，功能已合并至 v4.x，仅供参考。

### 审计与评估
| Spec 目录 | 说明 |
|-----------|------|
| `ai_db_qc_current_state` | v3.5.2 项目现状分析 |
| `project-audit-v3.2/v3.3/v3.4` | 三轮项目审计 |
| `project-evaluation-v3.5.3/v3.6.0` | 评估报告（含 EVALUATION_REPORT.md） |
| `live-evaluation-v3.7.0` | v3.7.0 完整实战评估 |
| `analyze-defect-efficiency` | 缺陷产出效率分析 |

### 功能增强
| Spec 目录 | 说明 |
|-----------|------|
| `adversarial-fuzzing-v3.5` | 对抗性攻击升级（四型分类引入） |
| `deep-crawling-optimization` | 深度爬取优化（3层递归） |
| `enhance-mre-real-vectors` | MRE 真实向量注入 |
| `expand-mre-vector-coverage` | MRE 覆盖面扩展 |
| `upgrade-harness-v3.3` | 测试台升级 |
| `refactor-harness-v3.4` | 测试台重构 |
| `tag-contract-sources` | 深度契约提取 + 来源标注 |
| `upgrade-semantic-deduplication` | 语义去重升级 |
| `optimize-runtime-and-logging` | 运行时性能优化 |
| `use-local-docs-library-v2.6` | 本地文档库模式 |
| `enhance-documentation-pipeline` | 文档管道增强 |
| `enhance-documentation-pipeline` | 文档管道增强 |

### 关键修复
| Spec 目录 | 说明 |
|-----------|------|
| `fix-critical-issues-v3.5.4` | P0 修复（兼容性/权限/证据） |
| `fix-critical-issues-v3.6.1` | P0 修复（去重器/遥测/一致性） |
| `fix-p0-and-regenerate-issues` | P0 修复（docs_context 膨胀） |

### 实战验证
| Spec 目录 | 说明 |
|-----------|------|
| `execution-run-local-docs-v1` | 本地文档回归测试 |
| `live-run-verify-v4.2` | L1 放宽验证 |

---

## 版本演进时间线

```
v3.2  ── 项目审计启动
v3.3  ── 测试台升级（Crawl4AI恢复）
v3.4  ── 测试台重构（MRE精细化）
v3.5  ── 对抗性攻击 + 四型分类 + 语义去重 + MRE真实向量
v3.6  ── 性能优化 + 评估报告
v3.7  ── 完整实战评估
v4.1  ── 6轮完整实战
v4.2  ── L1放宽 + 多样性增强
v4.3  ── 文档自动化 + 双层门控对齐
v4.4  ── L2门控修复 + 项目整理 + 跨数据库支持 ✅
```

---

## 快速查找

**核心功能引入版本：**
| 功能 | 引入 Spec |
|------|-----------|
| 双层门控 (L1+L2) | `automate-docs-pipeline` (v4.3) |
| 四型分类决策树 | `adversarial-fuzzing-v3.5` (v3.5) |
| MRE 真实向量 | `enhance-mre-real-vectors` (v3.5) |
| 本地文档库 | `use-local-docs-library-v2.6` (v3.5) |
| 语义去重 | `upgrade-semantic-deduplication` (v3.5) |
| 跨数据库支持 | `tech-report-and-cross-db-support` (v4.4) |
| 技术报告 | `tech-report-and-cross-db-support` (v4.4) |

**含评估报告的 Spec：**
- `project-evaluation-v3.5.3`
- `project-evaluation-v3.6.0`
- `live-evaluation-v3.7.0`
