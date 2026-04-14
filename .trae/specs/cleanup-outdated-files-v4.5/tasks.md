# Tasks

- [x] Task 1: 删除根目录一次性分析脚本（7 个文件）
  - [x] 删除 `_analyze_all_new.py`
  - [x] 删除 `_analyze_milvus_new.py`
  - [x] 删除 `_collect_issues.py`
  - [x] 删除 `_deep_analysis.py`
  - [x] 删除 `_extract_overview_data.py`
  - [x] 删除 `_final_analysis.py`
  - [x] 删除 `_run_verification.py`

- [x] Task 2: 删除根目录数据产物（3 个文件）
  - [x] 删除 `_issue_candidates.json`
  - [x] 删除 `overview_data.json`
  - [x] 删除 `project_overview.html`

- [x] Task 3: 删除根目录过时工具文件（4 个文件）
  - [x] 删除 `get-pip.py`
  - [x] 删除 `harness_engineering_blueprint.json`
  - [x] 删除 `reliability_upgrade_blueprint.json`
  - [x] 删除 `rollback_documentation_enhancement.sh`

- [x] Task 4: 删除根目录过时报告（3 个文件）
  - [x] 删除 `AUDIT_REPORT_V3.3.md`
  - [x] 删除 `AUDIT_REPORT_V3.4.md`
  - [x] 删除 `PROJECT_STATUS_REPORT_V3.2.md`

- [x] Task 5: 删除旧版虚拟环境 venv_run/
  - [x] 删除整个 `venv_run/` 目录

- [x] Task 6: 清理 scripts/ 目录中的一次性脚本（6 个文件）
  - [x] 删除 `scripts/_analyze_defects.py`
  - [x] 删除 `scripts/_regenerate_issues.py`
  - [x] 删除 `scripts/check_defects.py`
  - [x] 删除 `scripts/finish_remaining_issues.py`
  - [x] 删除 `scripts/manual_issue_generator.py`
  - [x] 删除 `scripts/regenerate_failed_issues.py`

- [x] Task 7: 删除过时工具目录
  - [x] 删除 `.omc/` 目录
  - [x] 删除 `.claude/` 目录

- [x] Task 8: 清理 .trae/documents/ 过时交接文档（8 个文件）
  - [x] 删除 `handoff_state.md`
  - [x] 删除 `handoff_v3.5.md`
  - [x] 删除 `handoff_v3.5.2.md`
  - [x] 删除 `ai_db_qc_development_plan.md`
  - [x] 删除 `ai_db_qc_v2_plan.md`
  - [x] 删除 `ai_db_qc_v2_1_harness_plan.md`
  - [x] 删除 `ai_db_qc_v2_2_production_plan.md`
  - [x] 删除 `ai_db_qc_technical_report.md`

- [x] Task 9: 删除 docs/superpowers/ 目录
  - [x] 删除整个 `docs/superpowers/` 目录

- [x] Task 10: 更新相关文档
  - [x] 更新 `docs/TECHNICAL_REPORT.md` 版本号从 v4.4 到 v4.5
  - [x] 更新 `.gitignore` 添加新的忽略规则
  - [x] 更新 `README.md` 项目结构树（移除已删除文件的引用）

# Task Dependencies

- Task 1~9 之间无依赖，可并行执行
- Task 10 依赖 Task 1~9 完成（需要知道哪些文件已被删除）
