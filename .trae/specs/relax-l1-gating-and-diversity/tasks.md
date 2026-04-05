# 放宽 L1 门控 + 增强测试多样性 - 任务列表

## [x] Task 1：放宽 L1 门控限制
- **优先级**：P0
- **依赖**：None
- **子任务**：
  - [x] 1.1：修改 `agent3_executor.py` 中 `_l1_gating()` 方法
  - [x] 1.2：将维度不匹配从"直接返回 False"改为"允许执行，记录警告"
  - [x] 1.3：确保维度不匹配的测试能生成 Type-1 缺陷

## [x] Task 2：评估论文搜索功能可行性
- **优先级**：P1
- **依赖**：None
- **结论**：可行性 LOW，仅修改 prompt
- **子任务**：
  - [x] 2.1：检查 `agent_web_search.py` 当前实现
  - [x] 2.2：评估 DuckDuckGo 搜索论文的可行性
  - [x] 2.3：评估 LLM 提取论文策略的可行性
  - [x] 2.4：输出可行性报告

## [x] Task 3：增强 Agent2 prompt 多样性
- **优先级**：P0
- **依赖**：Task 2（根据可行性决定是否使用论文搜索）
- **子任务**：
  - [x] 3.1：分析当前 Agent2 prompt
  - [x] 3.2：增加多样性约束指令（策略 6-8、Bug Type Coverage）
  - [x] 3.3：移除重复的 Distribution Requirement 部分

## [x] Task 4：验证改进效果
- **优先级**：P0
- **依赖**：Task 1 + Task 3
- **子任务**：
  - [x] 4.1：运行短测试验证 L1 门控放宽
  - [x] 4.2：检查维度不匹配测试是否生成缺陷
  - [x] 4.3：检查测试多样性是否提升

# Task Dependencies
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 1, Task 3]
