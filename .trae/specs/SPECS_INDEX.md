# Spec & Plan 索引

> AI-DB-QC 项目文档统一索引
> 当前活跃版本：**v6.0** | 更新日期：2026-05-07

---

## 文件结构（清理后）

```
.trae/
├── plans/                          ← 所有计划文件统一存放
│   ├── aidbqc-v6-arch-redesign.md  ⭐ 当前活跃开发计划
│   ├── roadmap_status.json         路线图状态（15个任务，9完成，3进行中，完成度90%）
│   └── deep-interview-v6-plan-update.md  Deep Interview规格（4轮，模糊度18%）
├── specs/
│   └── SPECS_INDEX.md              本文件
├── documents/
│   ├── handoff_state.md            项目交接状态
│   └── ai_db_qc_development_plan.md 原始开发计划（已标注被v6.0替代）
└── state/
    └── deep-interview-state.json   Deep Interview状态

根目录/
├── README.md                       项目说明（v6.0架构）
├── AGENTS.md                       架构文档（v6.0概要+v4.4历史）
└── AI-DB-QC_理论框架报告_v2.md     理论框架（开题报告基础）
```

---

## v6.0 活跃文档

| 文件 | 说明 | 状态 |
|------|------|------|
| `.trae/plans/aidbqc-v6-arch-redesign.md` ⭐ | **当前活跃计划** -- v6.0架构重设计，20步依赖图，整体完成度90% | 已完成 |
| `.trae/plans/roadmap_status.json` | 路线图状态 -- 15个任务追踪，9完成3进行中，v6.0最小验收已通过 | 已完成 |
| `.trae/plans/deep-interview-v6-plan-update.md` | Deep Interview规格 — 4轮访谈，模糊度18%，确定最小验收目标 | ✅ 完成 |
| `.trae/documents/handoff_state.md` | 项目交接状态 — v6.0架构概要+剩余工作 | ✅ 完成 |
| `.trae/documents/ai_db_qc_development_plan.md` | 原始6个月开发计划 — 已标注被v6.0替代 | ⚠️ 已废弃 |
| `README.md` | 项目说明 — v6.0架构描述 | ✅ 完成 |
| `AGENTS.md` | 架构文档 — v6.0概要+v4.4历史参考 | ✅ 完成 |
| `AI-DB-QC_理论框架报告_v2.md` | 理论框架 — 三大创新+四型缺陷+三层契约+七维测试 | 📋 参考 |

---

## v6.0 最小验收目标 (Deep Interview决策)

**验收结果: 已通过** -- 真实数据库E2E测试发现4个真实缺陷

**唯一必须项：** 真实数据库E2E测试 (Milvus+Qdrant)

**验收标准：**
- 连接真实Milvus执行完整测试流程（create->insert->search->delete） -- 已通过
- 连接真实Qdrant执行基本CRUD操作 -- 已通过
- 多轮Fuzzing后发现>=2个真实缺陷（任意类型） -- 已通过（发现4个）
- 真实缺陷有完整证据链（执行日志+数据库状态+MRE代码） -- 已通过
- 真实缺陷能生成格式正确的BugIssue -- 已通过

**推迟至v6.1：** Docker Compose统一、DBAdapter测试、工具函数测试、模块配置化、EventBus并发安全、DeepSeek Think验证、Pgvector/Weaviate E2E

---

## 历史版本参考

| 版本 | 说明 | 文档位置 |
|------|------|----------|
| v4.4 | 9-Agent LangGraph流水线，L2门控修复验证通过 | AGENTS.md（历史部分） |
| v5.0 | 完全重设计计划，已被v6.0替代 | 已删除（内容已合并到v6.0计划） |
| v3.x | 早期版本，含审计/增强/修复/实战验证 | 根目录AUDIT_REPORT/PROJECT_STATUS文件 |
