# 修复 P0-1 并补生成 Issue Spec

## 为什么

评估报告 run_5af0cc02 确认：系统已能完成 3 轮 fuzzing 迭代并发现 12 条缺陷，但 agent6_verifier 因 docs_context=6.6MB 超出 ZhipuAI API token 限制（400 Bad Request）而崩溃，导致：
1. 0 条缺陷获得验证判定（全部 pending）
2. 0 条 MRE 代码生成
3. 0 个 GitHub Issue 文件产出

必须修复此问题并补生成缺失的 Issue，才能首次实现 Defect→Verify→Issue 完整闭环。

## 变更内容

### 变更 1：修复 agent6_verifier.py 的 docs_context 膨胀问题（P0-1 修复）

- **文件**: `src/agents/agent6_verifier.py`
- **修改点 1**: `execute()` 方法（第 594-606 行）— 不再从 raw_docs.json 加载完整文档，改为加载截断版本或按需检索
- **修改点 2**: `_generate_issue_for_defect()` 方法（第 510-514 行）— env_context 中的 docs_context 必须截断到合理大小（如每条缺陷最多 8000 字符的相关文档片段）
- **新增方法**: `_get_relevant_docs_for_defect(defect, docs_map, max_chars=8000)` — 根据缺陷的 case_id、bug_type、operation、root_cause_analysis 中的关键词，从 docs_map 中检索最相关的文档片段
- **修改点 3**: 新增配置项 `agent6.max_docs_chars_per_defect` 控制单条缺陷的最大文档上下文量

### 变更 2：为 run_5af0cc02 的 12 条缺陷补生成 GitHub Issue

- **文件**: `.trae/runs/run_5af0cc02/GitHub_Issue_*.md`
- **方式**: 编写并执行一个独立脚本 `_regenerate_issues.py`，加载 run_5af0cc02 的 state.json.gz，使用修复后的 agent6 逻辑逐条生成 Issue
- **要求**: 
  - 每条缺陷生成一个符合模板的 .md 文件
  - MRE 代码使用 EmbeddingGenerator 生成的真实语义向量（非随机数）
  - Evidence 部分引用 milvus_io_docs_depth3.jsonl 中的真实文档内容
  - 对每条 Issue 给出质量评分

## 影响范围

- **影响代码**: `src/agents/agent6_verifier.py`（execute、_generate_issue_for_defect 方法）
- **影响配置**: `.trae/config.yaml`（可选新增 agent6 配置段）
- **影响产出**: `.trae/runs/run_5af0cc02/` 下新生成 ~8-12 个 GitHub_Issue_*.md 文件
- **不影响**: agent0-agent5 的任何逻辑、state 格式、telemetry 系统

## ADDED 需求

### 需求：智能文档截断

系统 SHALL 在 agent6_verifier 向 LLM 发送请求前，将 docs_context 截断到 API 可接受的范围内。

#### 场景：正常情况
- **WHEN** agent6_verifier 处理一条缺陷报告
- **THEN** 发送给 LLM 的 docs_context 不超过 `max_docs_chars_per_defect`（默认 8000 字符）
- **AND** 截取的内容应与当前缺陷相关（基于 case_id、operation、root_cause_analysis 的关键词匹配）

#### 场景：文档不可用
- **WHEN** raw_docs.json 不存在或 docs_context 为空
- **THEN** agent6 使用空字符串作为文档上下文，不崩溃，并在 Issue 中标注 "No direct documentation reference found"

### 需求：Issue 补生成脚本

系统 SHALL 提供独立脚本从已有 state 中补生成 GitHub Issue。

#### 场景：成功生成
- **WHEN** 执行 `_regenerate_issues.py` 脚本，指定 run_id=run_5af0cc02
- **THEN** 为每条 verified defect（reproduced_bug=True）生成一个 GitHub_Issue_*.md 文件
- **AND** 每个 Issue 包含完整的 Environment/Describe bug/Steps To Reproduce/Expected-Actual Behavior/Evidence 模板结构
- **AND** MRE 代码包含由 EmbeddingGenerator 生成的真实语义向量

## MODIFIED 需求

### 需求：DefectVerifierAgent.execute()

原有的 execute() 方法 SHALL 被修改，不再将完整 docs_context（6.6MB）嵌入 env_context。

**修改前行为**:
```python
full_docs_context = doc_data.get("full_docs", full_docs_context)  # 加载完整 6.6MB
env_context = {"db_version": ..., "docs_context": full_docs_context, ...}  # 全量传入
```

**修改后行为**:
```python
full_docs_context = doc_data.get("full_docs", full_docs_context)  # 仍加载用于本地检索
docs_map = self._parse_docs_context(full_docs_context)  # 解析为 URL->content 映射
# 在 _generate_issue_for_defect 中按需截断:
relevant_docs = self._get_relevant_docs_for_defect(defect, docs_map, max_chars=8000)
env_context = {"db_version": ..., "docs_context": relevant_docs, ...}  # 只传截断后内容
```

## 验收标准

1. 修复后的 agent6_verifier 能够在不触发 400 Bad Request 的情况下处理 run_5af0cc02 的 12 条缺陷
2. 至少生成 8 个以上的 GitHub Issue 文件（预期 12 个中部分可能被判为 false_positive 或 invalid_mre）
3. 每个 Issue 文件的 MRE 代码包含真实的语义向量数值（非 random.random()）
4. 每个 Issue 文件大小在 2KB-15KB 之间（不会因文档膨胀而异常大）
5. 补生成脚本可独立运行，不依赖完整流水线
