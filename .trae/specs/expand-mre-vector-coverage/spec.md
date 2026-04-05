# 扩展 MRE 向量占位符覆盖面 Spec

## 为什么

`_inject_real_vectors()` 已实现并验证可用（TC_002 注入 384 维真实嵌入成功），但当前注入率仅 **16.7%（2/12）**，远低于验收标准 **≥67%（≥8/12）**。

根因是 LLM 生成的占位符模式高度多样化——列表推导式、变量引用维度、嵌套数据结构等——现有 3 种正则 Pattern 仅覆盖最简单的场景。需要扩展覆盖面以达成"不再回退至 LLM 自编占位符"的目标。

## 变更内容

### 变更：agent6_verifier.py — 扩展 `_inject_real_vectors()` 的 Pattern 覆盖

- **文件**: `src/agents/agent6_verifier.py`
- **新增 Pattern 4**: 列表推导式匹配 — `[np.random.rand(N) for _ in range(M)]` / `[np.random.randn(dim).astype(np.float32) for _ in range(n)]`
  - 从推导式中提取 inner dimension（rand/randn 的参数）
  - 对每个元素生成独立的真实向量
  - 替换为预计算的真实向量列表
- **增强 Pattern 2**: 变量名维度解析 — 当 dim 参数是变量名（如 `dim=768; vec=np.random.rand(dim)`）时
  - 通过 `_resolve_dimension()` 已有的上下文推断能力解析实际整数值
  - 回退到 `_infer_dim_from_context()` 做启发式推断
- **新增 Pattern 5**: 嵌入数据结构中的向量 — 检测 dict/list 内嵌的向量赋值（如 `data = {"vector": np.random.rand(768)}`）
  - 解析 JSON-like 结构中的向量字段
  - 替换为真实向量值

### 变更：agent6_verifier.py — LLM Prompt 增强（可选但推荐）

- **修改方法**: `_generate_mre_code()` 或 `_build_verification_prompt()`
- 在 system prompt 中增加 MRE 格式约束：
  > "生成 MRE 时，所有查询/搜索向量必须使用以下格式之一：
  > 1. `query_vector = [float_value] * dimension` （uniform fill 格式）
  > 2. `embedding = np.random.rand(dimension)` （random 格式）
  > 禁止使用列表推导式或嵌套结构来初始化向量。"
- 目的：引导 LLM 输出可被现有 Pattern 匹配的格式，从源头提高命中率

### 变更：重新生成 12 个 Issue 并验证注入率

- 执行 `_regenerate_issues.py` 覆盖生成
- 验证新注入率 ≥ 67%（≥8/12）

## 影响范围

- **影响代码**: `src/agents/agent6_verifier.py`（扩展 `_inject_real_vectors()` + 可选 prompt 修改）
- **影响产出**: `.trae/runs/run_5af0cc02/GitHub_Issue_*.md`（覆盖更新）
- **不影响**: agent0-agent5、state 格式、API 渠道、其他模块

## ADDED 需求

### 需求：列表推导式向量占位符检测与替换

系统 SHALL 能检测并替换形如 `[np.random.rand(N) for _ in range(M)]` 的列表推导式占位符。

#### 场景：标准列表推导式
- **WHEN** MRE 包含 `vectors = [np.random.rand(768) for _ in range(3)]`
- **THEN** 替换为 3 个独立真实向量的列表，每个维度 768
- **AND** 总行数合理增长（每维 ~100 字符 → 3×768×8 ≈ 18KB，需控制上限）

#### 场景：带类型转换的推导式
- **WHEN** MRE 包含 `[np.random.randn(dim).astype(np.float32) for _ in range(n)]`
- **THEN** 提取 dim 和 n，生成对应数量的 float32 真实向量

### 需求：变量名维度解析

系统 SHALL 能将变量名形式的维度参数解析为实际整数值。

#### 场景：变量已定义
- **WHEN** MRE 包含 `dim = 768; query_vec = np.random.rand(dim)`
- **THEN** 通过上下文扫描找到 `dim = 768` 并用 768 作为实际维度

#### 场景：变量来自 schema
- **WHEN** MRE 包含 `vec = np.random.rand(collection.dimension)` 且 collection 有 schema 定义
- **THEN** 从 schema 中提取 dimension 字段值

### 需需求：MRE 格式 Prompt 约束（可选增强）

系统 SHOULD 在 LLM prompt 中引导 MRE 使用易匹配的向量格式。

#### 场景：Prompt 生效后重新生成
- **WHEN** LLM 收到格式约束指令后生成 MRE
- **THEN** ≥80% 的向量初始化语句符合 Pattern 1/2/3 的可匹配格式

## MODIFIED 需求

### 需求：MRE 真实向量自动注入（原 enhance-mre-real-vectors spec）

**修改内容**: 将 Pattern 数量从 3 种扩展到 5 种，增加对复杂占位符格式的覆盖能力。

## 验收标准

1. 重新生成的 12 个 Issue 中，**至少 8 个**的 MRE 代码包含真实语义向量（非 uniform/random/手写简单值）
2. 每个 Issue 文件大小仍在合理范围（<30KB，多向量注入可能增加体积）
3. `_regenerate_issues.py` 执行无错误，100% 成功率
4. EVALUATION_REPORT.md 中 MRE 真实性评分从 **1.5/5 更新为 ≥3/5**
5. 不引入回归——已有 TC_002/TC_102 的真实向量不被破坏
