# Update Project Knowledge Spec

## Why
用户希望通读整个项目，全面更新对项目当前状态、架构、核心模块以及各类配置的认知，以确保后续开发、问题排查和系统维护能基于最新的项目上下文进行。

## What Changes
- 扫描并分析项目根目录的核心文件（如 `README.md`, `ROADMAP.md`, `AGENTS.md` 等）
- 分析 `src/` 目录下的核心源码结构（如 agents, adapters, context, oracles, pools 等）
- 分析 `docs/` 和 `.trae/` 下的关键文档和规范文件
- 将获取到的重要架构信息、设计规范和经验总结，通过 `manage_core_memory` 工具记录到核心记忆（Core Memory）中，或以总结形式输出给用户

## Impact
- Affected specs: 无直接影响，但会提升全局上下文的准确性
- Affected code: 无，此任务为只读（Read-only）分析操作

## ADDED Requirements
### Requirement: Project Knowledge Update
The system SHALL provide an updated understanding of the project's current architecture, multi-agent workflow, test generation logic, and overall status.

#### Scenario: Success case
- **WHEN** the agent finishes reading and analyzing the codebase
- **THEN** core memories are updated with the latest project context, and a comprehensive summary is presented to the user.