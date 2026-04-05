# 增强 MRE 真实语义向量 Spec

## 为什么

评估报告（3.47/5）确认：12 个 GitHub Issue 的 MRE 代码全部使用占位符向量（`[0.1]*768`、`np.random.rand()`），MRE 真实性维度得分 **0/5**。这是当前最大的质量短板。

项目中已有 `EmbeddingGenerator.generate_search_vector_code()` 方法能生成真实的 SentenceTransformer 嵌入向量，但从未在 Issue 生成流程中被调用——LLM 生成的占位符被原样保留。

## 变更内容

### 变更：agent6_verifier.py — 注入真实向量替换占位符

- **文件**: `src/agents/agent6_verifier.py`
- **新增方法**: `_inject_real_vectors(self, mre_code: str, defect) -> str`
  - 检测 MRE 代码中的占位符模式：
    - `[constant] * N`（uniform fill，如 `[0.1] * 768`）
    - `np.random.rand(N)` / `np.random.randn(N)`（随机生成）
    - 手写的短简单列表（如 `[0.1, 0.2, 0.3, 0.4]` — 维度≤10 且值单调递增/相同）
  - 从缺陷的 `operation` 字段提取查询文本（如 "wireless noise cancelling headphones"）
  - 调用 `self.embedding_generator.generate_search_vector_code(query_text, dimension)` 获取真实向量代码
  - 替换匹配到的占位符行
  - 返回修改后的 MRE 代码
- **修改方法**: `execute()` 中，在 `_extract_mre_code()` 之后、写入 Issue 文件和 `_verify_mre()` 之前，调用 `_inject_real_vectors()`
- **修改方法**: `_regenerate_issues.py` 补生成脚本同步更新（如果该脚本独立调用 `_generate_issue_for_defect()`）

### 变更：重新生成 12 个 Issue 验证效果

- 执行 `_regenerate_issues.py` 覆盖生成
- 验证新 Issue 中 MRE 包含真实向量数值

## 影响范围

- **影响代码**: `src/agents/agent6_verifier.py`（新增 1 方法 + 修改 1 处调用点）
- **影响产出**: `.trae/runs/run_5af0cc02/GitHub_Issue_*.md`（覆盖更新）
- **不影响**: agent0-agent5、state 格式、telemetry 系统、其他任何模块

## ADDED 需求

### 需求：MRE 真实向量自动注入

系统 SHALL 在从 LLM 输出中提取 MRE 代码后、执行验证前，自动将占位符向量替换为真实语义嵌入。

#### 场景：检测到 uniform fill 占位符
- **WHEN** MRE 代码包含 `search_vector = [0.1] * 768` 或类似模式
- **THEN** 该行被替换为 `search_vector = [0.034217, -0.089123, 0.156782, ...]`（384 个真实浮点数）
- **AND** 行首注释标注来源：`# 使用真实语义向量 (由 SentenceTransformer 生成)`

#### 场景：检测到 random 向量
- **WHEN** MRE 代码包含 `np.random.rand(dim)` 或 `np.random.randn(dim)`
- **THEN** 替换为预计算的固定 seed 真实向量（确保可复现）

#### 场景：无法检测或模型未加载
- **WHEN** EmbeddingGenerator 模型加载失败或代码中无可识别的占位符模式
- **THEN** 保持原始 MRE 不变，不崩溃，日志输出 "No vector injection needed"

#### 场景：dimension 推断
- **WHEN** 占位符中的 dimension 来自变量引用（如 `dim=768; vec=[0.1]*dim`）
- **THEN** 通过上下文分析推断实际维度值（从 collection schema 或 field 定义中提取）

## 验收标准

1. 重新生成的 12 个 Issue 中，至少 8 个的 MRE 代码包含真实语义向量（非 uniform/random/手写简单值）
2. 每个 Issue 文件大小仍在合理范围（<20KB，真实向量约增加 ~3KB/个）
3. `_regenerate_issues.py` 执行无错误，100% 成功率
4. EVALUATION_REPORT.md 中 MRE 真实性评分从 0/5 更新为 ≥3/5
