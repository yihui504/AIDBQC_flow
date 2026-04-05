# 项目整理 & 文档更新 Spec

## Why

项目经过从 v3.2 到 v4.4 的多轮迭代，积累了 28 个 spec 目录、多个版本的审计报告、散落的工具脚本，以及过时的文档。当前项目缺少一个清晰的 README 入口，新开发者难以快速理解项目架构和最新状态。需要在 v4.4 验证通过后，对项目进行一次全面整理，使代码库处于可交付、可维护的状态。

## What Changes

### 1. 项目结构整理
- 清理根目录散落脚本（`_*.py`, `check_*.py`, `monitor_*.py`, `manual_*.py`, `finish_*.py`, `regenerate_*.py`）→ 归入 `scripts/` 或确认是否仍需要
- 清理过期日志文件（`debug.log`, `run_error.log`, `run_final.log`, `run_output.log`, `test_redir.log`）
- 清理重复配置文件（`config.yaml.example`, `config.example.yaml` → 保留一个或合并）

### 2. 文档更新
- **创建/更新 `README.md`**：作为项目主入口，包含：
  - 项目简介（AI-DB-QC：基于 LLM Agent 的向量数据库自动化质量检测系统）
  - 架构概览（Agent0-Agent6 + Reranker + Reflection 流水线）
  - 核心特性（双模型门控 L1+L2、四型缺陷分类决策树、文档预处理管道、Contract Fallback）
  - 快速开始（环境配置、运行命令、配置说明）
  - v4.4 版本状态与验证结果
- **更新 `AGENTS.md`**：反映当前 Agent 架构（如有变化）
- **清理 `.trae/specs/`**：归档已完成的老版本 spec（v3.x 系列），保留 v4.x 活跃 spec

### 3. .trae 目录整理
- 保留活跃 spec: `live-run-v4.4/`, `automate-docs-pipeline/`, `relax-l1-gating-and-diversity/`
- 老版本 spec 标记或归档说明

## Impact

- Affected code: 根目录文件组织、README.md、AGENTS.md、docs/ 目录
- 不影响 src/ 核心代码逻辑
- 不影响 .trae/config.yaml 运行配置

## ADDED Requirements

### Requirement: Project README
系统 SHALL 提供一个完整的 README.md 作为项目入口：

#### Scenario: 新开发者快速上手
- **WHEN** 新开发者克隆仓库并打开 README.md
- **THEN** 能理解项目目的、架构、如何运行、最新状态

### Requirement: Root Directory Cleanliness
系统 SHALL 保持根目录整洁：

#### Scenario: 无过期文件
- **WHEN** 查看 root 目录
- **THEN** 无临时日志、无重复配置、工具脚本有明确归属

## MODIFIED Requirements

### Requirement: AGENTS.md Accuracy
AGENTS.md SHALL 反映 v4.4 的实际 Agent 架构（含 L1/L2 双门控、DecisionTree 分类器、文档预处理管道等新增能力）

## REMOVED Requirements

无（不删除任何 spec，仅做归类整理）
