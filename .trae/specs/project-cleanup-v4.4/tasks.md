# 项目整理 & 文档更新 - 任务列表

## [x] Task 1：清理根目录文件
- **优先级**：P0
- **子任务**：
  - [x] 1.1：识别并归类根目录工具脚本（`_*.py`, `check_*.py`, `monitor_*.py`, `manual_*.py`, `finish_*.py`, `regenerate_*.py`）→ 移入 `scripts/` 目录
  - [x] 1.2：删除过期日志文件（`debug.log`, `run_error.log`, `run_final.log`, `run_output.log`, `test_redir.log`）
  - [x] 1.3：合并重复配置文件（`config.yaml.example` + `config.example.yaml` → 保留一个标准模板）
  - [x] 1.4：确认 `requirements.txt` 和 `requirements-dashboard.txt` 是否需要合并（结论：零重叠，无需合并）

## [x] Task 2：创建/更新 README.md
- **优先级**：P0
- **依赖**：Task 1
- **子任务**：
  - [x] 2.1：编写项目简介与架构概览（Agent0-6 流水线图）
  - [x] 2.2：记录核心特性（L1+L2 双门控、四型分类、文档管道、Contract Fallback）
  - [x] 2.3：编写快速开始指南（环境配置、安装、运行命令）
  - [x] 2.4：记录 v4.4 验证结果（12 Issues, Type-4+Type-2 多类型分布）
  - [x] 2.5：添加项目结构说明

## [x] Task 3：更新 AGENTS.md
- **优先级**：P1
- **依赖**：无
- **子任务**：
  - [x] 3.1：读取现有 AGENTS.md
  - [x] 3.2：更新 Agent 描述以反映 v4.4 能力（L2 门控、DecisionTree、文档预处理、Contract Fallback）
  - [x] 3.3：补充新增模块说明（contract_fallbacks.py, 文档缓存等）

## [x] Task 4：整理 .trae/specs/ 目录
- **优先级**：P2
- **依赖**：无
- **子任务**：
  - [x] 4.1：列出所有 spec 目录，标记 v3.x 已完成归档 vs v4.x 活跃
  - [x] 4.4：创建 SPECS_INDEX.md 索引文件作为 spec 版本历史说明

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] 无依赖，可与 Task 1 并行
- [Task 4] 无依赖，可与 Task 1 并行
