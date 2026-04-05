# Deep Contract Extraction & Source Tagging Spec

## Why
目前合约（Contract）提取深度不足，主要局限在单一参数的硬限制（L1），缺乏对**操作时序关系（Sequential Relationships）**和**深层业务逻辑约束**的覆盖。此外，Agent 6 在生成 Issue 时缺乏精准的证据链支持。
通过增强 Agent 1 的提取能力，引入时序契约，并贯穿来源标注，可以显著提升模糊测试的逻辑覆盖深度 and Issue 的专业度。

## What Changes
- **Agent 1 (Contract Analyst)**: 
    - **深度提取**：要求 LLM 穷举所有可见的 API 参数约束，而不限于 dimension/top_k 等常用项。
    - **时序契约 (Sequential Contracts)**：在 L2 层面引入 `operational_sequences` 字段，记录操作间的前置条件和时序依赖（如：Create -> Insert -> Flush -> Index -> Load -> Search）。
    - **状态机定义**：记录各操作触发的状态转换要求。
    - **来源标注**：在所有提取项（参数、时序、状态）中增加 `source_urls` 标注。
- **Workflow State**: 
    - `Contract` 模型扩展以容纳时序契约和更复杂的 L1 描述。
    - `TestCase` 和 `DefectReport` 继续保持 `source_url` 标注字段。
- **Agent 2 (Test Generator)**: 
    - 能够解析时序契约，生成专门针对“非法时序”（Chaotic Sequence）和“长路径状态转换”的测试用例。
- **Agent 6 (Verifier)**: 
    - 生成 Issue 时，利用深层合约信息和预标注的 `source_url` 提供更具说服力的“预期行为”描述。

## Impact
- Affected specs: `verify-doc-references-v3.5.2`, `adversarial-fuzzing-v3.5`
- Affected code:
    - [agent1_contract_analyst.py](file:///c:/Users/11428/Desktop/ralph/src/agents/agent1_contract_analyst.py)
    - [agent2_test_generator.py](file:///c:/Users/11428/Desktop/ralph/src/agents/agent2_test_generator.py)
    - [state.py](file:///c:/Users/11428/Desktop/ralph/src/state.py)

## ADDED Requirements
### Requirement: 时序契约提取
系统必须从文档中识别出操作的先后顺序要求。

#### Scenario: 提取索引创建时序
- **WHEN** 文档指出“索引必须在数据加载前创建”
- **THEN** 合约中应包含一个时序约束：`{"sequence": ["create_index", "load_collection"], "type": "strict_order"}`。

### Requirement: 全参数深度覆盖
Agent 1 不得仅提取预定义的几个参数，必须扫描文档中所有出现的 API 参数。

## MODIFIED Requirements
### Requirement: 合约来源追溯
所有提取的契约（包括新增的时序契约）必须带有 `source_url` 标注。
