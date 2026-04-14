# 全量审计与 Weaviate 4 轮实战 Spec

## Why
当前需要从“功能可运行”升级到“可审计、可观测、可稳定复现”的交付标准。必须先建立项目全景认知并完成漏洞闭环，再在 Weaviate 1.36.9 上进行真实 4 轮实战与连续稳定性验证。

## What Changes
- 建立项目全景图：文档、模块、依赖、数据流、关键业务链路
- 完整代码与配置审计：安全、性能、逻辑、配置、兼容性五类漏洞清单
- 每条漏洞输出修复方案与对应测试用例（单元/集成/回归）
- 逐条修复并验证：每次改动必须通过测试门禁后再继续下一项
- 文档同步更新：代码、注释、文档三方一致
- 在 Weaviate 1.36.9 上执行 4 轮实战并接入实时监控与阈值告警
- 出现异常立即中断，提交最小复现并做根因修复，不允许降级/替代/模拟
- 修复后清空环境并重新执行完整 4 轮，直至连续两轮无异常且指标稳定
- 完成交付物：代码、文档、测试报告、监控报告、Issue 质量评审表、复盘报告

## Impact
- Affected specs:
  - 测试执行稳定性与回归质量保障
  - 文档治理与证据链完整性
  - 实战运行可观测性与告警能力
- Affected code:
  - `src/agents/*`、`src/adapters/*`、`src/oracles/*`、`src/validators/*`
  - `main.py`、`src/config.py`、`.trae/config.yaml`
  - `scripts/*`、`tests/*`、`docs/*`

## ADDED Requirements
### Requirement: 项目全景认知与依赖拓扑
系统 SHALL 产出项目结构、依赖关系、业务链路的可审计全景图。

#### Scenario: 全景图建立成功
- **WHEN** 完成对核心文档与核心代码模块的通读和结构化梳理
- **THEN** 输出模块职责、调用链、关键配置项与外部依赖关系

### Requirement: 漏洞清单与测试映射
系统 SHALL 形成按严重级别排序的漏洞清单，并为每项漏洞绑定修复方案和测试用例。

#### Scenario: 清单可执行
- **WHEN** 完成文档与代码审计
- **THEN** 每个漏洞均包含严重级别、影响面、复现条件、修复动作、测试项

### Requirement: 修复门禁
系统 SHALL 对每次漏洞修复执行单元测试、集成测试、回归测试门禁。

#### Scenario: 修复可接受
- **WHEN** 某漏洞修复完成
- **THEN** 对应测试全部通过且未引入回归

### Requirement: Weaviate 4 轮实战与监控
系统 SHALL 在 Weaviate 1.36.9 上执行真实 4 轮流程并采集监控指标。

#### Scenario: 实战执行成功
- **WHEN** `target_db_input` 指向 Weaviate 1.36.9 且 `max_iterations=4`
- **THEN** 采集 CPU、内存、网络、日志、异常栈并触发阈值告警

### Requirement: 异常中断与根治
系统 SHALL 在出现死循环、资源泄漏、超时、逻辑错误时立即中断并根治。

#### Scenario: 异常闭环
- **WHEN** 监控或运行检测到异常
- **THEN** 立即中断、输出最小复现、完成根因修复并重新验证

### Requirement: 连续稳定性验收
系统 SHALL 在“清空环境后重跑”达到连续两轮无异常且指标稳定后才可验收。

#### Scenario: 稳定性达标
- **WHEN** 完成完整 4 轮重跑并连续两轮满足稳定阈值
- **THEN** 判定实战通过并进入最终质量评审

### Requirement: 交付物完整性
系统 SHALL 输出可审计交付包并保证 Issue 证据链完整可验证。

#### Scenario: 交付合规
- **WHEN** 进入收尾交付阶段
- **THEN** 所有 Issue 包含日志、快照、指标、代码 diff、测试报告与有效文档引用

## MODIFIED Requirements
### Requirement: 实战最大轮次
`harness.max_iterations` SHALL 设为 4（本次实战环境限定）。

### Requirement: 运行策略
禁止降级、替代或模拟执行；必须使用真实环境、真实链路、真实监控。

## REMOVED Requirements
### Requirement: 无
**Reason**: 本次不移除既有能力，仅新增与强化执行约束。  
**Migration**: 不涉及迁移。

