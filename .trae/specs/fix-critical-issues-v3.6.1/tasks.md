# 修复关键问题 - 任务列表

## [x] 任务 1：修复去重器初始化 Bug（P0）
- **优先级**：P0
- **依赖**：None
- **描述**：
  - 定位 `src/defects/enhanced_deduplicator.py` 中的 `__init__` 方法
  - 分析 `self.defects` 的使用方式（列表还是字典）
  - 添加正确的初始化语句
  - 添加类型注解
  - 添加单元测试验证初始化
- **子任务**：
  - [x] 1.1：阅读 enhanced_deduplicator.py，理解 self.defects 的使用方式
  - [x] 1.2：修复 from_state 方法中的 None 值处理
  - [x] 1.3：添加类型注解和文档字符串
  - [x] 1.4：验证修复后去重器可以正常初始化

## [x] 任务 2：修复遥测文件生成问题（P1）
- **优先级**：P1
- **依赖**：None
- **描述**：
  - 检查 telemetry.py 中的文件路径配置
  - 确认异步队列正确刷新机制
  - 添加程序退出时的队列刷新钩子
  - 添加日志文件创建失败的错误提示
- **子任务**：
  - [x] 2.1：阅读 telemetry.py，理解当前文件路径配置
  - [x] 2.2：检查 QueueListener 是否正确配置
  - [x] 2.3：添加 atexit 钩子确保程序退出时刷新队列
  - [x] 2.4：添加文件创建失败的错误处理和日志
  - [x] 2.5：验证 telemetry.jsonl 文件正确生成

## [x] 任务 3：增强优化功能可观测性（P2）
- **优先级**：P2
- **依赖**：None
- **描述**：
  - 为 DocumentCache 添加状态日志
  - 为 DockerContainerPool 添加状态日志
  - 确保日志信息清晰、有用
- **子任务**：
  - [x] 3.1：在 agent0_env_recon.py 中添加缓存命中/未命中日志
  - [x] 3.2：在 state.py 中添加连接池状态日志
  - [x] 3.3：验证日志输出清晰可读

## [x] 任务 4：添加性能监控（P3）
- **优先级**：P3
- **依赖**：None
- **描述**：
  - 集成 psutil 库
  - 添加内存使用监控
  - 添加 CPU 使用监控
  - 在状态转储中包含性能数据
- **子任务**：
  - [x] 4.1：检查 psutil 是否已在依赖中，如无则添加
  - [x] 4.2：创建性能监控模块或函数
  - [x] 4.3：在 main.py 中集成性能监控
  - [x] 4.4：在紧急状态转储中包含性能数据
  - [x] 4.5：验证性能数据正确收集和记录

## [x] 任务 5：集成测试和验证
- **优先级**：P0
- **依赖**：任务 1-4
- **描述**：
  - 执行完整的系统运行测试
  - 验证所有修复彻底生效
  - 确认系统稳定性和质量
  - 生成详细的测试报告
- **子任务**：
  - [x] 5.1：执行完整的项目运行，监控所有智能体执行
  - [x] 5.2：验证去重器正常工作，无 NoneType 错误
  - [x] 5.3：验证 telemetry.jsonl 文件正确生成
  - [x] 5.4：验证优化功能状态日志清晰可见
  - [x] 5.5：验证性能监控数据正确记录
  - [x] 5.6：验证系统完整运行，生成 GitHub Issue

## [ ] 任务 6：修复缺陷验证与报告一致性，并重新跑一轮（P0）
- **优先级**：P0
- **依赖**：任务 1-5
- **描述**：
  - 识别“Issue 描述/bug_type”与“verifier 执行日志”矛盾的根因
  - 统一 verifier 的结论语义（真实缺陷 / 预期拒绝 / MRE 无效）
  - 将已验证缺陷聚合写入 state（例如 verified_defects）
  - 以 verifier 结论为门禁控制 Issue 生成，降低误报
  - 修复后执行完整系统运行（max_iterations=3），对产出进行统计评估
- **子任务**：
  - [x] 6.1：定位误报来源（Type-1 Illegal Success 等标签与日志矛盾、invalid_code 仍生成 Issue、verified_defects 未落盘）
  - [x] 6.2：在 agent6_verifier 输出结构化 verdict（reproduced_bug / expected_rejection / invalid_mre / inconclusive）并写回 defect_reports
  - [x] 6.3：在 issue 生成阶段增加门禁：仅对 reproduced_bug 生成可投递 Issue（其他标记为 FALSE_POSITIVE 或不生成）
  - [x] 6.4：在 state 中落盘 verified_defects（或等价字段），并在 reflection 使用该字段汇总
  - [x] 6.5：补充最小回归验证（至少覆盖：预期拒绝不当作 bug、invalid_mre 不生成可投递 Issue）
  - [ ] 6.6：重新跑一轮并评估产出（Issue 数量、verified_defects 数量、误报率）

# 任务依赖关系
- 任务 5 依赖任务 1-4（需要所有修复完成后进行集成测试）
- 任务 1、2、3、4 可并行执行
- 任务 6 依赖任务 1-5（需要系统可完整跑通后再修复一致性并回归验证）
