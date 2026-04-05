# 修复关键问题规范 v3.6.1

## 为什么
根据项目评估报告 v3.6.0，系统在运行过程中崩溃，存在以下关键问题需要立即解决：
1. **P0**: 去重器初始化失败 - `self.defects` 未正确初始化导致 `'NoneType' object is not subscriptable` 错误
2. **P1**: telemetry.jsonl 文件未生成 - 异步日志队列可能未正确刷新
3. **P2**: 优化功能未验证 - 文档缓存、Docker 连接池等功能状态不明
4. **P3**: 缺少性能监控 - 无内存、CPU 使用监控
5. **P0**: 缺陷验证与报告不一致 - 产出的 Issue 与 MRE 验证日志出现矛盾，导致误报率高、无法沉淀 verified_defects

## 变更内容
- **修复去重器初始化 Bug**：在 `EnhancedDefectDeduplicator.__init__` 中正确初始化 `self.defects` 属性
- **修复遥测文件生成**：确保异步日志队列正确刷新，文件路径正确配置
- **增强优化功能可观测性**：添加明确的状态日志，显示缓存命中/未命中、连接池状态
- **添加性能监控**：集成 psutil 监控内存和 CPU 使用
- **修复缺陷验证与报告一致性**：统一“复现成功/失败/无效 MRE”的语义，避免将“预期拒绝/脚本错误”误报为产品缺陷，并将已验证缺陷写入状态

## 影响
- 受影响文件：
  - `src/defects/enhanced_deduplicator.py` - 去重器初始化
  - `src/telemetry.py` - 遥测文件生成
  - `src/agents/agent0_env_recon.py` - 缓存状态日志
  - `src/state.py` - 连接池状态日志
  - `src/main.py` - 性能监控集成
  - `src/agents/agent5_diagnoser.py` - 缺陷归因与严重性分类
  - `src/agents/agent6_verifier.py` - MRE 验证结果结构化与落盘
  - `src/agents/agent_reflection.py` - 基于已验证缺陷生成总结与去重

## ADDED Requirements

### Requirement: 去重器正确初始化
系统 SHALL 在 EnhancedDefectDeduplicator 初始化时正确设置 self.defects 属性，确保后续访问不会出现 NoneType 错误。

#### Scenario: 去重器初始化成功
- **WHEN** 创建 EnhancedDefectDeduplicator 实例
- **THEN** self.defects 被正确初始化为空列表 []
- **AND** 后续访问 self.defects 不会抛出 NoneType 错误
- **AND** 去重功能正常工作

### Requirement: 遥测文件正确生成
系统 SHALL 确保遥测数据正确写入 telemetry.jsonl 文件，并在程序结束时刷新异步队列。

#### Scenario: 遥测文件生成成功
- **WHEN** 系统运行并产生遥测数据
- **THEN** telemetry.jsonl 文件在运行目录中正确创建
- **AND** 遥测数据按 JSONL 格式正确写入
- **AND** 程序结束时队列中的数据被刷新到文件

#### Scenario: 异常退出时遥测数据保存
- **WHEN** 系统异常退出或崩溃
- **THEN** 遥测队列中的数据被紧急刷新
- **AND** 已产生的遥测数据不丢失

### Requirement: 优化功能状态可见
系统 SHALL 为所有优化功能提供明确的状态日志，便于验证功能是否正常工作。

#### Scenario: 文档缓存状态日志
- **WHEN** 文档缓存功能启用
- **THEN** 日志显示缓存命中/未命中状态
- **AND** 日志显示缓存大小和 TTL 信息
- **AND** 日志显示增量更新情况

#### Scenario: Docker 连接池状态日志
- **WHEN** Docker 连接池功能启用
- **THEN** 日志显示容器获取/释放状态
- **AND** 日志显示空闲容器清理情况
- **AND** 日志显示连接池大小

### Requirement: 性能监控
系统 SHALL 监控并记录内存和 CPU 使用情况，便于性能分析和优化。

#### Scenario: 性能数据收集
- **WHEN** 系统运行
- **THEN** 定期收集内存使用数据
- **AND** 定期收集 CPU 使用数据
- **AND** 性能数据记录到遥测日志

#### Scenario: 性能数据包含在状态转储
- **WHEN** 系统执行紧急状态转储
- **THEN** 转储数据包含当前内存使用
- **AND** 转储数据包含当前 CPU 使用
- **AND** 转储数据包含性能历史记录

### Requirement: 缺陷验证与报告一致性
系统 SHALL 将缺陷报告产出与 MRE 验证结果保持一致，并避免误报。

#### Scenario: 真实缺陷被验证并沉淀
- **WHEN** verifier 对某条缺陷给出“复现成功且违反预期”的结论
- **THEN** 缺陷报告标记为已验证（is_verified=True 或等价字段）
- **AND** 缺陷进入 state.verified_defects（或等价聚合字段）
- **AND** 仅对已验证缺陷生成可投递的 Issue 文件

#### Scenario: 预期拒绝不应被当作缺陷
- **WHEN** verifier 发现 MRE 触发的是“输入非法被正确拒绝/正确报错”
- **THEN** 缺陷报告被标记为误报（false_positive 或等价字段）
- **AND** 不生成可投递 Issue（或 Issue 顶部明确标记 FALSE_POSITIVE）

#### Scenario: MRE 无效时不生成缺陷
- **WHEN** verifier 判定 MRE 为 invalid_code / invalid_assumption（例如脚本自身插入类型错误、依赖缺失、调用 API 不存在）
- **THEN** 缺陷报告标记为无效
- **AND** 不生成可投递 Issue

#### Scenario: 结论-证据一致性校验
- **WHEN** 缺陷报告文本宣称“应失败但成功/应成功但失败”等断言
- **THEN** 系统 SHALL 以 verifier 的执行日志为准进行一致性校验
- **AND** 当断言与日志矛盾时，自动降级为误报并记录原因

## MODIFIED Requirements

### Requirement: 去重器错误处理
系统 SHALL 在去重器操作中添加详细的错误处理和日志，便于问题诊断。

#### Scenario: 去重器错误处理
- **WHEN** 去重器操作遇到错误
- **THEN** 记录详细的错误信息和堆栈跟踪
- **AND** 提供清晰的错误诊断信息
- **AND** 确保错误不会导致系统静默失败

## REMOVED Requirements
无
