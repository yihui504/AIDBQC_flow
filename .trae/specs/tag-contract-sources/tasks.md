# Tasks

- [x] Task 1: 扩展数据模型以支持时序契约与来源标注
  - [x] SubTask 1.1: 在 `src/state.py` 的 `TestCase` 和 `DefectReport` 中增加 `assigned_source_url` 和 `source_url`
  - [x] SubTask 1.2: 在 `src/agents/agent1_contract_analyst.py` 中更新合约模型，增加 `operational_sequences` 和 `source_urls`

- [x] Task 2: 改造 Agent 1 (Contract Analyst) 深度提取逻辑
  - [x] SubTask 2.1: 更新 Agent 1 的 LLM Prompt，增加“时序契约”提取指令，要求穷举文档中的操作顺序和状态要求
  - [x] SubTask 2.2: 确保所有提取项（L1/L2/L3）都通过 `source_urls` 字典映射到具体的文档 URL
  - [x] SubTask 2.3: 验证合约 JSON 中包含丰富的时序约束和来源标注

- [x] Task 3: 改造 Agent 2 (Test Generator) 时序测试生成
  - [x] SubTask 3.1: 更新 Agent 2 的 LLM Prompt，使其能够解析 `operational_sequences`
  - [x] SubTask 3.2: 生成专门针对非法时序（如未加载即搜索）的测试用例，并标注 `assigned_source_url`

- [x] Task 4: 改造 Agent 6 (Verifier) 引用验证逻辑
  - [x] SubTask 4.1: 更新 Agent 6 的 Issue 生成 Prompt，优先利用预标注的来源 URL 进行真实性和相关性验证
  - [x] SubTask 4.2: 验证生成的 Issue 能够准确引用文档中关于时序或参数深层限制s的描述

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 3
- Task 5 depends on Task 4
