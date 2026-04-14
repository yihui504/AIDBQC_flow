# 项目文件整理与过时文件清理 Spec

## Why

项目经过 v3.2 ~ v4.5 的多轮迭代开发，根目录和各子目录中积累了大量一次性分析脚本、过时报告、旧版蓝图、废弃虚拟环境等文件。这些文件干扰项目结构清晰度，增加新开发者上手成本，且部分文件包含硬编码路径已无法正常运行。需要在 v4.5 稳定后对项目进行一次全面整理。

## What Changes

### 1. 删除根目录一次性分析脚本（7 个）
- `_analyze_all_new.py` — 特定 run 的对比分析脚本，硬编码路径
- `_analyze_milvus_new.py` — 特定 run 的 Milvus 分析脚本，硬编码路径
- `_collect_issues.py` — 一次性 Issue 收集脚本，硬编码路径
- `_deep_analysis.py` — 特定 run 的深度分析脚本，硬编码路径
- `_extract_overview_data.py` — 一次性数据提取脚本，生成 overview_data.json
- `_final_analysis.py` — 特定 run 的最终分析脚本，硬编码路径
- `_run_verification.py` — 与 main.py 完全重复的入口文件

### 2. 删除根目录数据产物（3 个）
- `_issue_candidates.json` — 一次性 Issue 候选数据
- `overview_data.json` — project_overview.html 的数据源
- `project_overview.html` — 一次性生成的可视化 HTML

### 3. 删除根目录过时工具文件（4 个）
- `get-pip.py` — pip 安装器，不属于项目代码
- `harness_engineering_blueprint.json` — v3.0 旧版蓝图，已被 .trae/specs 替代
- `reliability_upgrade_blueprint.json` — v3.2 旧版蓝图，已被 .trae/specs 替代
- `rollback_documentation_enhancement.sh` — 一次性回滚脚本

### 4. 删除根目录过时报告（3 个）
- `AUDIT_REPORT_V3.3.md` — v3.3 审计报告，项目已到 v4.5
- `AUDIT_REPORT_V3.4.md` — v3.4 审计报告，项目已到 v4.5
- `PROJECT_STATUS_REPORT_V3.2.md` — v3.2 状态报告，项目已到 v4.5

### 5. 删除旧版虚拟环境
- `venv_run/` — Python 3.8 旧虚拟环境，与 venv312 重复

### 6. 清理 scripts/ 目录中的一次性脚本（6 个）
- `scripts/_analyze_defects.py` — 硬编码特定 run ID
- `scripts/_regenerate_issues.py` — 一次性 Issue 重新生成脚本
- `scripts/check_defects.py` — 硬编码特定 run ID
- `scripts/finish_remaining_issues.py` — 一次性 Issue 完成脚本
- `scripts/manual_issue_generator.py` — 一次性手动 Issue 生成脚本
- `scripts/regenerate_failed_issues.py` — 一次性失败 Issue 重新生成脚本

### 7. 删除过时工具目录
- `.omc/` — OpenMissionControl 工具状态目录，包含过时 mission 数据
- `.claude/` — Claude 工具配置目录，与当前 Trae 环境无关

### 8. 清理 .trae/documents/ 过时交接文档（6 个）
- `handoff_state.md` — 旧版交接状态
- `handoff_v3.5.md` — v3.5 交接文档
- `handoff_v3.5.2.md` — v3.5.2 交接文档
- `ai_db_qc_development_plan.md` — 旧版开发计划
- `ai_db_qc_v2_plan.md` — v2 计划
- `ai_db_qc_v2_1_harness_plan.md` — v2.1 harness 计划
- `ai_db_qc_v2_2_production_plan.md` — v2.2 生产计划
- `ai_db_qc_technical_report.md` — 旧版技术报告

### 9. 删除 docs/superpowers/ 目录
- `docs/superpowers/` — 其他工具生成的计划/规格文档，不属于项目文档体系

### 10. 更新相关文档
- 更新 `docs/TECHNICAL_REPORT.md` 版本号从 v4.4 到 v4.5
- 更新 `.gitignore` 添加 `venv_run/`、`.omc/`、`.claude/`、`docs/superpowers/` 等忽略规则

## Impact

- Affected code: 不影响 `src/` 核心代码逻辑
- Affected docs: README.md 项目结构树需同步更新
- Affected configs: .gitignore 需更新
- 删除的文件均为一次性脚本、过时报告、废弃环境，不影响项目运行

## ADDED Requirements

### Requirement: 根目录整洁性
系统 SHALL 保持根目录仅包含项目入口文件、核心配置、核心文档：

#### Scenario: 新开发者查看根目录
- **WHEN** 新开发者克隆仓库并查看根目录
- **THEN** 仅看到必要的入口文件（main.py）、配置文件（requirements.txt, .env.example 等）、核心文档（README.md, AGENTS.md, ROADMAP.md）和 Docker 编排文件，无一次性脚本和数据产物

### Requirement: .gitignore 完整性
.gitignore SHALL 覆盖所有不应入库的目录和文件类型：

#### Scenario: 防止废弃文件再次入库
- **WHEN** 新的虚拟环境或工具目录被创建
- **THEN** .gitignore 规则能正确忽略它们

## MODIFIED Requirements

### Requirement: README.md 项目结构树准确性
README.md 中的项目结构树 SHALL 与实际文件系统一致，删除的文件不再出现在结构树中。

## REMOVED Requirements

无（不删除任何核心功能或 spec）
