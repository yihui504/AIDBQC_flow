# AI-DB-QC 理论框架报告 v2.0

**项目名称**：AI-DB-QC (LLM-Enhanced Contract-Driven Vector Database QA Framework)
**报告日期**：2026-03-27
**项目版本**：v2.0 (基于2024-2025年最新调研更新)
**测试数据库**：Milvus v2.6.12, Qdrant v1.17.0, Weaviate v1.36.5, Pgvector v0.8.2

---

## 更新日志

**v2.0 主要更新：**
- ✅ 引入LLM增强模块（基于arXiv:2502.20812调研）
- ✅ 新增语义预言机系统（解决语义验证挑战）
- ✅ 强化双层有效性模型的理论基础
- ✅ 完善四型分类法（与1671个实际bug对比验证）
- ✅ 增加自适应测试策略
- ✅ 明确与现有工作的差异化

---

## 目录

1. [项目概述](#一项目概述)
2. [研究背景与动机](#二研究背景与动机)
3. [核心研究假设与创新点](#三核心研究假设与创新点)
4. [双层有效性模型](#四双层有效性模型)
5. [四型缺陷分类法](#五四型缺陷分类法)
6. [契约驱动架构](#六契约驱动架构)
7. [LLM增强测试生成](#七llm增强测试生成)
8. [智能预言机系统](#八智能预言机系统)
9. [测试维度体系](#九测试维度体系)
10. [证据链方法论](#十证据链方法论)
11. [设计原则](#十一设计原则)
12. [与现有工作的对比](#十二与现有工作的对比)

---

## 一、项目概述

### 1.1 研究背景（2025年最新发现）

**关键洞察：** 根据2025年3月的最新研究 [arXiv:2502.20812](https://arxiv.org/abs/2502.20812)，向量数据库质量保证面临**三大核心挑战**：

| 挑战类别 | 具体问题 | 现有方法的局限 |
|---------|---------|--------------|
| **测试输入生成** | 高维向量空间的有效采样、语义相关性测试用例生成 | 无法生成语义相关的测试用例 |
| **预言机定义** | 近似正确性的验证标准、语义一致性的判断方法 | 传统预言机无法处理语义验证 |
| **测试执行** | 大规模数据集的性能测试、长期运行的稳定性测试 | 缺乏系统性框架 |

**实证数据支持：**
- [arXiv:2506.02617](https://arxiv.org/pdf/2506.02617) 分析了15个开源VDBMS的**1671个bug修复PR**
- 缺陷分布：索引相关35%、查询处理28%、内存管理18%、API接口12%、分布式7%

### 1.2 项目定位（更新后）

**AI-DB-QC 是一个 LLM增强的、契约驱动的、适配器化的向量数据库质量保障系统**

```
核心思想：
├─ 契约驱动：保证测试的系统性和可追溯性
├─ LLM增强：突破传统方法在语义验证上的局限
└─ 双层模型：确保测试的有效性和准确性

定位：研究型框架 + 工程化实现
├─ 学术贡献：双层有效性模型、四型分类法、语义预言机
└─ 实用价值：可测试多数据库、自动化缺陷发现
```

### 1.3 核心能力（增强版）

```
场景理解 → 语义测试生成 → 多数据库执行 → 智能预言机验证 → 缺陷分类 → 证据链
    ↓           ↓              ↓             ↓            ↓         ↓
  LLM增强   LLM+规则混合    适配器层    传统+语义    四型分类    自动报告
```

---

## 二、研究背景与动机

### 2.1 为什么向量数据库测试如此困难？

| 维度 | 传统数据库 | 向量数据库 | 测试挑战 |
|------|-----------|-----------|----------|
| **数据类型** | 结构化数据 | 高维向量（128-4096维） | 难以生成有效测试数据 |
| **查询语义** | 精确匹配 | 相似性搜索（近似） | 难以定义"正确"结果 |
| **算法特性** | 确定性算法 | 近似算法（ANN） | 结果可接受偏差 |
| **状态管理** | 无状态 | 有状态（集合生命周期） | 需要状态转换测试 |
| **错误诊断** | 明确错误信息 | "内部错误"常见 | 根因分析困难 |

### 2.2 现有测试方法的不足

**1. 规则驱动的测试生成：**
```python
# 传统方法：规则生成
def generate_test_cases():
    for dim in [0, 128, 4096, -1, 999999]:
        yield create_vector_test(dim)
    # ❌ 问题：只考虑语法，不考虑语义
```

**2. 传统预言机：**
```python
# 传统预言机
def verify_top_k(results, k):
    return len(results) == k
    # ❌ 问题：只验证数量，不验证语义正确性
```

**3. 缺乏语义理解：**
- 无法判断结果是否与查询意图相关
- 无法处理模糊查询和语义相似性
- 无法探索语义边界情况

### 2.3 我们的解决方案

**核心创新：引入LLM处理语义层**

```
传统层（已验证有效）
├─ 契约驱动测试生成 ✅
├─ 四型分类法 ✅
└─ 基础预言机 ✅

    ↓ 增强（我们的创新）

智能层（新增）
├─ 场景理解：从应用文档提取测试场景
├─ 语义测试生成：生成语义相关的测试用例
├─ 语义预言机：验证语义正确性
└─ 自适应策略：优化测试序列
```

---

## 三、核心研究假设与创新点

### 3.1 三大核心创新点

#### **创新点1：LLM驱动的语义测试用例生成**

**研究假设：**
> 对于向量数据库的语义测试（如"找相似商品"），基于语义理解的LLM生成的测试用例比纯规则生成的用例能发现更多的Type-4语义违规缺陷。

**技术路线：**
```
应用场景分析
    ↓
LLM场景理解
    ↓
┌─────────────┬─────────────┬─────────────┐
│ 语义等价类  │ 语义边界    │ 对抗样本    │
│ "手机"→    │ 模糊查询    │ 语义干扰    │
│ "移动电话" │ 边缘概念    │ 概念漂移    │
└─────────────┴─────────────┴─────────────┘
    ↓
融合规则生成的测试用例
```

**预期效果：**
- 语义覆盖率提升 > 50%
- Type-4缺陷发现率提升 > 30%

---

#### **创新点2：语义预言机系统**

**研究假设：**
> 基于LLM的语义预言机可以判断查询结果是否符合查询意图，从而发现传统预言机无法检测的语义违规。

**技术路线：**
```python
class SemanticOracle:
    """语义预言机"""

    def verify(self, query, results, context):
        # 1. 理解查询意图
        intent = self.llm.parse_intent(query, context)

        # 2. 评估结果相关性
        relevance = self.llm.score_relevance(results, intent)

        # 3. 检测语义异常
        anomalies = self.detect_anomalies(results, intent, relevance)

        return {
            'passed': len(anomalies) == 0,
            'anomalies': anomalies,
            'explanation': self.llm.explain(anomalies)
        }
```

**与传统预言机的对比：**

| 预言机类型 | 检查内容 | 局限 | 我们的突破 |
|-----------|---------|------|-----------|
| 单调性预言机 | top-K单调性 | 只检查数量 | ✅ 保留 |
| 一致性预言机 | 写读一致性 | 只检查精确匹配 | ✅ 保留 |
| **语义预言机** | **结果相关性、完整性、排序** | **N/A** | **🆕 新增** |

---

#### **创新点3：双层有效性模型**

**研究假设：**
> 区分"抽象合法性"和"运行时就绪性"两个正交维度，可以更精确地分类向量数据库的缺陷。

**理论贡献：**
```
传统单层模型：
输入有效 → 执行 → 分类结果

我们的双层模型：
第一层：抽象合法性（静态）
    ├─ 类型约束
    ├─ 参数范围
    └─ 必填字段

第二层：运行时就绪性（动态）
    ├─ 集合存在性
    ├─ 索引加载状态
    └─ 一致性状态

    → 正交组合 → 精确分类
```

**理论依据：**
- 形式化方法中的前置条件/后置条件
- 契约式设计理论
- 与[arXiv:2406.09469](https://arxiv.org/abs/2406.09469)中的符合性测试理论呼应

---

### 3.2 研究问题（Research Questions）

**RQ1：LLM增强的有效性**
- 相比规则生成，LLM生成的测试用例是否能发现更多缺陷？
- 在语义测试场景下，LLM的优势是否显著？

**RQ2：语义预言机的有效性**
- 语义预言机的误报率和召回率如何？
- 与传统预言机结合是否能提升整体检测能力？

**RQ3：双层有效性模型的实用性**
- 双层模型是否能改进缺陷分类的准确性？
- 与单层模型相比，分类一致性是否提升？

**RQ4：框架整体有效性**
- 框架能否发现真实的向量数据库缺陷？
- 跨数据库的通用性如何？

---

## 四、双层有效性模型

### 4.1 形式化定义

**第一层：抽象合法性 (Abstract Legality, L₁)**

```
L₁(request) = (type_check(request) ∧
               range_check(request) ∧
               required_check(request))

评估方式：契约验证器（静态分析）
评估时机：请求构造时、编译时
```

**第二层：运行时就绪性 (Runtime Readiness, L₂)**

```
L₂(request, state) = (collection_exists(request, state) ∧
                       index_loaded(request, state) ∧
                       consistency_check(request, state))

评估方式：前置条件门控（动态检查）
评估时机：运行时、执行前
```

### 4.2 正交性矩阵

| L₁\L₂ | ✓ Ready | ✗ Not Ready |
|-------|---------|-------------|
| **✓ Legal** | **有效就绪**<br/>可执行，正常分类 | **有效但未就绪**<br/>Type-2.PF |
| **✗ Illegal** | **无效但就绪**<br/>Type-1/2 | **无效未就绪**<br/>Type-1/2 |

**关键洞察：**
```
传统模型混淆了：
1. 真正的bug（Type-3/4）：
   L₁=✓, L₂=✓ 下的失败

2. 预期失败：
   L₁=✓, L₂=✗ 下的失败

双层模型明确区分这两种情况 → 更精确的分类
```

### 4.3 伪有效案例

以下案例**不应该**归类为Type-3或Type-4：

| 场景 | L₁ | L₂ | 正确分类 |
|------|----|----|----------|
| 搜索不存在的集合 | ✓ | ✗ | Type-2.PF |
| 插入前查询 | ✓ | ✗ | Type-2.PF |
| 索引加载前搜索 | ✓ | ✗ | Type-2.PF |
| 对不支持的字段过滤 | ✓ | ✗ | Type-2.PF |

**红线原则：**
```
Type-3和Type-4必须要求：
L₁ = ✓ ∧ L₂ = ✓

否则无法区分：
• 真正的语义违规
• 因状态不满足而导致的预期失败
```

### 4.4 与现有工作的对比

| 模型 | 提出者 | 维度 | 局限 | 我们的优势 |
|------|--------|------|------|-----------|
| IEEE 1044 | IEEE | 8维分类 | 通用，不针对VDB | **领域特化** |
| ODC | IBM | 正交维度 | 关注开发过程 | **关注运行时** |
| **双层模型** | 我们 | **2层正交** | - | **VDB专用** |

---

## 五、四型缺陷分类法

### 5.1 分类决策树（更新版）

```
                    L₁: 契约有效？
                         │
           ┌─────────────┴─────────────┐
          NO                        YES
           │                          │
    L₂检查（可选）              操作成功？
           │              ┌─────────┴─────────┐
      操作成功？          NO               YES
       │     │           │                 │
     YES    NO    L₂:前置条件通过？    L₂:前置条件通过？
      │      │         │                 │
   Type-1  Type-2  NO         YES    NO         YES
(非法成功)(诊断)  │           │      │           │
                └───┬───────┬──┘      ↓           ↓
                    ↓       ↓      L₂检查失败  L₂:预言机通过？
                Type-2.PF  L₂有效？   (Type-2.PF)  │
                           │              ┌────┴────┐
                          YES             NO       YES
                           │               │        │
                       可忽略           Type-4    Type-3
                                       (语义违规) (运行时失败)
```

### 5.2 四型详细定义（v2.0）

| 类型 | 名称 | 正式条件 | L₁ | L₂ | 严重程度 | 示例 |
|------|------|----------|----|----|----------|------|
| **Type-1** | 非法操作成功 | `¬L₁ ∧ success` | ✗ | - | HIGH | 插入0维向量、使用负数top_K |
| **Type-2** | 诊断信息不足 | `¬L₁ ∧ failed ∧ poor_error` | ✗ | - | MEDIUM | "内部错误"无根因 |
| **Type-2.PF** | 前置条件失败 | `L₁ ∧ ¬L₂ ∧ poor_error` | ✓ | ✗ | MEDIUM | 搜索不存在集合，错误不明确 |
| **Type-3** | 运行时失败 | `L₁ ∧ L₂ ∧ failed` | ✓ | ✓ | HIGH | 有效插入崩溃、有效查询超时 |
| **Type-4** | 语义违规 | `L₁ ∧ L₂ ∧ oracle_failed` | ✓ | ✓ | MEDIUM | top-K单调性违反、过滤器失效 |

### 5.3 Type-3子类型

| 子类型 | 描述 | 实际案例（来自GitHub） |
|--------|------|----------------------|
| Type-3.A | 抛出异常/错误 | Qdrant: [#2268](https://github.com/qdrant/qdrant/issues/2268) 错误维度导致服务宕机 |
| Type-3.B | 崩溃/段错误 | Milvus: 某些查询导致进程崩溃 |
| Type-3.C | 挂起/无限等待 | Qdrant: [#2493](https://github.com/qdrant/qdrant/issues/2493) 集群同步问题导致请求挂起 |
| Type-3.D | 超时 | 大规模查询超时 |

### 5.4 Type-4子类型（扩展）

| 子类型 | 预言机 | 违规类型 | 实际案例 |
|--------|--------|----------|----------|
| Type-4.单调性 | 单调性预言机 | top-K单调性违反 | K=10的结果不是K=5的超集 |
| Type-4.一致性 | 写读一致性预言机 | 写读不一致 | 写入后读回数据不同 |
| Type-4.严格性 | 过滤器预言机 | 过滤器严格性违反 | 过滤后结果更多 |
| **Type-4.语义** | **语义预言机** | **结果不相关** | **查询"手机"返回"电脑"** |

**🆕 新增Type-4.语义：**
```python
# 传统Type-4只能检查数学性质
assert monotonicity(results)
assert consistency(write, read)

# 语义Type-4可以检查语义正确性
assert semantic_relevance(results, query_intent)
```

### 5.5 分类法有效性验证

**与实际bug数据对比：**
- 来源：[arXiv:2506.02617](https://arxiv.org/pdf/2506.02617) 的1671个bug
- 对比结果：四型分类法可以覆盖所有类型的bug

**一致性验证实验设计：**
```
数据集：500个测试用例
标注：3位专家独立标注
指标：Kappa系数 > 0.8
```

---

## 六、契约驱动架构

### 6.1 三层契约系统

```
┌─────────────────────────────────────────────────────────┐
│                    L3: 应用契约                          │
│         (Application Contracts - 场景级)                │
│  • 金融场景：风控向量查询                               │
│  • 推荐场景：商品相似度搜索                             │
│  • 医疗场景：医学影像相似性                             │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────┐
│                    L2: 语义契约                          │
│         (Semantic Contracts - 语义级)                   │
│  • 查询意图：相似性、精确匹配、混合检索                 │
│  • 结果相关性：语义相似度阈值                           │
│  • 上下文约束：领域知识、业务规则                      │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────┐
│                    L1: API契约                           │
│         (API Contracts - 接口级)                        │
│  • 类型约束：向量维度、数据类型                         │
│  • 参数范围：top_K、metric_type                         │
│  • 状态约束：集合存在、索引加载                         │
└─────────────────────────────────────────────────────────┘
```

### 6.2 契约分类系统（v2.0）

| 级别 | 名称 | 定义 | 来源 | 可报告bug |
|------|------|------|------|-----------|
| **L1** | 强约束 | 文档明确承诺的行为 | 官方文档 | ✅ 可报告 |
| **L2** | 弱约束 | 逻辑推导或行业标准 | 语义契约 | ⚠️ 需确认 |
| **L3** | 建议 | 最佳实践 | 应用经验 | ❌ 仅建议 |

**🆕 新增L3应用契约：**
```yaml
# 示例：电商推荐场景
application_contract:
  scenario: "商品推荐"
  semantic_expectations:
    - "结果应该是商品，不是其他类别"
    - "相似度应基于商品特征，而非随机"
    - "价格过滤应该生效"
  context_constraints:
    - domain: "e-commerce"
    - user_intent: "find similar products"
```

### 6.3 契约到测试用例的映射

```
契约定义
    ↓
契约解析器
    ↓
┌────────────────┬────────────────┬────────────────┐
│  规则生成器    │  LLM生成器     │  混合生成器    │
│  (现有)        │  (新增)        │  (推荐)        │
└────────────────┴────────────────┴────────────────┘
    ↓                ↓                ↓
规则测试用例    语义测试用例    融合测试用例
```

---

## 七、LLM增强测试生成

### 7.1 场景理解模块

**功能：**从应用文档中提取测试场景

```python
class ScenarioUnderstanding:
    """场景理解器"""

    def parse_application_scenario(self, app_docs):
        """
        从应用文档提取测试场景

        输入：应用领域文档（金融、医疗、电商等）
        输出：结构化场景描述
        """
        scenarios = []

        for doc in app_docs:
            # 1. 提取关键场景
            scenario = self.llm.extract_scenario(doc)

            # 2. 识别测试目标
            scenario['test_objectives'] = self.llm.identify_objectives(scenario)

            # 3. 评估风险
            scenario['risk_level'] = self.llm.assess_risk(scenario)

            scenarios.append(scenario)

        return scenarios
```

**应用示例：**
```
电商推荐场景：
1. 商品相似度搜索
   ├─ 目标：找到相似商品
   ├─ 风险：推荐不相关商品
   └─ 优先级：高

2. 用户行为向量存储
   ├─ 目标：高效存储和检索
   ├─ 风险：性能问题
   └─ 优先级：中

3. 实时推荐更新
   ├─ 目标：快速更新用户偏好
   ├─ 风险：一致性问题
   └─ 优先级：高
```

### 7.2 语义测试生成器

**功能：**生成语义相关的测试用例

```python
class SemanticTestGenerator:
    """语义测试用例生成器"""

    def generate_semantic_equivalents(self, query):
        """
        生成语义等价类测试

        示例：
        查询："找类似的手机"

        等价类：
        1. 同义词："手机" → "移动电话" → "智能手机"
        2. 相关词："手机" → "通讯设备" → "电子产品"
        3. 上下文："推荐类似商品" → "相似产品" → "同类物品"
        """
        equivalents = []

        # 1. 同义词扩展
        synonyms = self.llm.get_synonyms(query)
        equivalents.extend(synonyms)

        # 2. 上下文变体
        contextual = self.llm.generate_contextual_variants(query)
        equivalents.extend(contextual)

        # 3. 跨语言（如果适用）
        multilingual = self.llm.translate_to_multilingual(query)
        equivalents.extend(multilingual)

        return equivalents

    def generate_boundary_cases(self, query):
        """
        生成语义边界测试

        目标：探索语义理解的边界
        """
        boundaries = []

        # 1. 模糊查询
        fuzzy_queries = self.llm.generate_fuzzy_queries(query)
        boundaries.extend(fuzzy_queries)

        # 2. 边缘概念
        edge_cases = self.llm.identify_edge_concepts(query)
        boundaries.extend(edge_cases)

        # 3. 多概念组合
        combinations = self.llm.generate_combinations(query)
        boundaries.extend(combinations)

        return boundaries

    def generate_adversarial_cases(self, query):
        """
        生成对抗样本测试

        目标：欺骗语义理解
        """
        adversarial = []

        # 1. 语义干扰
        perturbations = self.llm.add_semantic_noise(query)
        adversarial.extend(perturbations)

        # 2. 概念漂移
        drifts = self.llm.simulate_concept_drift(query)
        adversarial.extend(drifts)

        # 3. 跨域混淆
        cross_domain = self.llm.generate_cross_domain_queries(query)
        adversarial.extend(cross_domain)

        return adversarial
```

### 7.3 混合生成策略

**推荐方案：**规则 + LLM混合

```python
class HybridTestGenerator:
    """混合测试用例生成器"""

    def generate(self, contract):
        """
        混合生成策略

        策略：
        1. 基础功能：规则生成（高效、可靠）
        2. 语义测试：LLM生成（智能、覆盖广）
        3. 边界探索：融合（最佳平衡）
        """
        test_cases = []

        # 1. 规则生成（保证覆盖率）
        rule_cases = self.rule_generator.generate(contract)
        test_cases.extend(rule_cases)

        # 2. LLM生成（提升语义覆盖率）
        semantic_cases = self.llm_generator.generate(contract)
        test_cases.extend(semantic_cases)

        # 3. 去重与优先级排序
        unique_cases = self.deduplicate(test_cases)
        prioritized_cases = self.prioritize(unique_cases)

        return prioritized_cases
```

**预期效果：**
- 基础功能覆盖率：100%（规则保证）
- 语义覆盖率：>50%（LLM增强）
- 整体缺陷发现率：>30%（相比纯规则）

---

## 八、智能预言机系统

### 8.1 预言机层次结构

```
┌─────────────────────────────────────────────────────────┐
│              第一层：传统预言机（快速）                    │
│  • 单调性预言机                                         │
│  • 一致性预言机                                         │
│  • 严格性预言机                                         │
│  → 执行速度快，误报率低                                 │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ↓ 通过
┌─────────────────────────────────────────────────────────┐
│              第二层：语义预言机（深度）                    │
│  • 语义相关性预言机                                      │
│  • 语义完整性预言机                                      │
│  • 语义排序预言机                                        │
│  → 处理复杂语义，发现深层缺陷                            │
└─────────────────────────────────────────────────────────┘
```

### 8.2 语义预言机设计

```python
class SemanticOracle:
    """语义预言机"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.RELEVANCE_THRESHOLD = 0.7

    def verify(self, test_case, result, context):
        """
        语义验证
        """
        # 1. 理解查询意图
        intent = self.llm.parse_intent(test_case.query, context)

        # 2. 评估结果相关性
        relevance_scores = [
            self.llm.score_relevance(result_item, intent)
            for result_item in result.items
        ]

        # 3. 检测语义异常
        anomalies = self.detect_semantic_anomalies(
            result, intent, relevance_scores
        )

        # 4. 生成解释
        explanation = self.llm.explain_anomalies(anomalies)

        return {
            'passed': len(anomalies) == 0,
            'anomalies': anomalies,
            'explanation': explanation,
            'relevance_scores': relevance_scores
        }

    def detect_semantic_anomalies(self, result, intent, scores):
        """
        检测语义异常

        异常类型：
        1. 不相关结果：分数 < 阈值
        2. 遗漏重要结果：覆盖率不足
        3. 排序不合理：分数不单调递减
        """
        anomalies = []

        # 1. 不相关结果
        for i, score in enumerate(scores):
            if score < self.RELEVANCE_THRESHOLD:
                anomalies.append({
                    'type': 'irrelevant_result',
                    'index': i,
                    'score': score,
                    'reason': f'Result not relevant to query intent (score={score:.2f})'
                })

        # 2. 遗漏重要结果
        expected_coverage = self.llm.infer_expected_coverage(intent)
        actual_coverage = len([s for s in scores if s > 0.7])
        if actual_coverage < expected_coverage * 0.8:
            anomalies.append({
                'type': 'missing_results',
                'expected': expected_coverage,
                'actual': actual_coverage,
                'reason': f'Expected {expected_coverage} relevant results, got {actual_coverage}'
            })

        # 3. 排序不合理
        if not self._is_monotonically_decreasing(scores):
            anomalies.append({
                'type': 'poor_ranking',
                'reason': 'Results not properly sorted by relevance'
            })

        return anomalies

    def _is_monotonically_decreasing(self, scores):
        """检查分数是否单调递减"""
        return all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
```

### 8.3 预言机协调器

```python
class OracleCoordinator:
    """预言机协调器"""

    def __init__(self):
        self.traditional_oracles = [
            MonotonicityOracle(),
            ConsistencyOracle(),
            StrictnessOracle()
        ]
        self.semantic_oracle = SemanticOracle()

    def verify(self, test_case, result, context):
        """
        分层验证
        """
        # 第一层：传统预言机
        for oracle in self.traditional_oracles:
            check_result = oracle.verify(test_case, result)
            if not check_result['passed']:
                return {
                    'passed': False,
                    'oracle_type': 'traditional',
                    'oracle_name': oracle.name,
                    'violation': check_result['violation']
                }

        # 第二层：语义预言机
        semantic_result = self.semantic_oracle.verify(
            test_case, result, context
        )

        if not semantic_result['passed']:
            return {
                'passed': False,
                'oracle_type': 'semantic',
                'anomalies': semantic_result['anomalies'],
                'explanation': semantic_result['explanation']
            }

        return {'passed': True}
```

---

## 九、测试维度体系

### 9.1 四大测试维度（保持不变）

| 维度 | 名称 | 测试重点 | 生成方式 | 预言机 |
|------|------|----------|----------|--------|
| **R1** | 参数边界测试 | 输入验证、错误处理 | 规则生成 | 契约验证 |
| **R2** | API验证/可用性 | 参数处理、API特性 | 规则生成 | 契约验证 |
| **R3** | 序列/状态转换测试 | 状态转换、幂等性 | 规则生成 | 序列预言机 |
| **R4** | 差分测试 | 跨数据库行为差异 | 规则生成 | 差分预言机 |

### 9.2 🆕 新增：语义测试维度

| 维度 | 名称 | 测试重点 | 生成方式 | 预言机 |
|------|------|----------|----------|--------|
| **R5** | 语义相关性测试 | 结果与查询意图的相关性 | **LLM生成** | **语义预言机** |
| **R6** | 语义边界测试 | 语义理解的边界情况 | **LLM生成** | **语义预言机** |
| **R7** | 对抗鲁棒性测试 | 对抗样本的抵抗力 | **LLM生成** | **语义预言机** |

### 9.3 维度互补关系

```
传统维度（R1-R4）：
├─ R1: 输入验证正确性 ✅
├─ R2: API行为一致性 ✅
├─ R3: 状态管理健壮性 ✅
└─ R4: 跨数据库一致性 ✅

新增语义维度（R5-R7）：
├─ R5: 语义相关性 ✅
├─ R6: 语义边界探索 ✅
└─ R7: 对抗鲁棒性 ✅

    = 全面的向量数据库质量保证
```

---

## 十、证据链方法论

### 10.1 三部分证据链（保持不变）

```
文档证据 → 实际行为 → 分析
```

### 10.2 🆕 三级证据链

**级别定义：**

| 级别 | 名称 | 条件 | 报告方式 | 示例 |
|------|------|------|----------|------|
| **L1** | 确认缺陷 | 文档清晰 + 行为违反 | 确认的bug | 违反API规范的错误 |
| **L2** | 潜在问题 | 文档模糊 + 行为可疑 | 潜在问题 | 行为异常但文档未明确 |
| **L3** | 行为观察 | 无文档 + 异常行为 | 观察记录 | 独特的行为模式 |

**改进效果：**
```
旧方法（过于严格）：
文档模糊 → 不报告
→ 可能漏掉真正的bug ❌

新方法（三级证据）：
文档模糊 + 行为可疑 → 报告为L2潜在问题
→ 不漏掉有价值发现 ✅
→ 同时标注置信度 ✅
```

---

## 十一、设计原则

### 11.1 核心原则（更新）

| 原则 | 说明 | 变化 |
|------|------|------|
| **Schema优先** | 所有模块交互使用结构化schemas | 保持 |
| **LLM增强** | LLM用于语义层，传统方法用于基础层 | 🆕 从"可选"改为"增强" |
| **证据可追溯** | 每个结论都可追溯到证据 | 保持 |
| **YAGNI** | 最小可行原型，而非平台 | 保持 |
| **研究导向** | 设计选择服务于研究清晰性 | 保持 |

### 11.2 LLM定位（明确化）

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                    ║
║  LLM的核心职责：处理语义层                                        ║
║                                                                    ║
║  LLM应该做：                                                       ║
║  • 理解查询意图和场景                                             ║
║  • 生成语义相关的测试用例                                         ║
║  • 验证语义正确性（语义预言机）                                    ║
║  • 解释语义异常                                                   ║
║                                                                    ║
║  LLM不应该做：                                                     ║
║  • 最终的bug类型分类（由四型分类法负责）                          ║
║  • 契约有效性检查（由契约验证器负责）                             ║
║  • 运行时就绪性评估（由前置条件门控负责）                         ║
║                                                                    ║
║  关键：LLM是增强工具，不是最终决策者                              ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════╝
```

### 11.3 分层实施策略

```
阶段1：基础框架（已实现）
├─ 契约驱动测试生成 ✅
├─ 四型分类法 ✅
├─ 基础预言机 ✅
└─ 双层有效性模型 ✅

阶段2：LLM增强（新增）
├─ 场景理解模块
├─ 语义测试生成
├─ 语义预言机
└─ 自适应策略

阶段3：优化与评估
├─ 性能优化
├─ 误报率降低
└─ 大规模实验验证
```

---

## 十二、与现有工作的对比

### 12.1 与最新研究的对比

| 工作 | 提出时间 | 核心贡献 | 局限 | 我们的差异化 |
|------|---------|---------|------|-------------|
| [arXiv:2502.20812](https://arxiv.org/abs/2502.20812) | 2025.03 | 测试路线图 | 理论为主，无实现 | **我们提供完整实现** |
| [arXiv:2506.02617](https://arxiv.org/pdf/2506.02617) | 2025.06 | 缺陷分析 | 仅有分析 | **我们提供检测方法** |
| [arXiv:2505.02012](https://arxiv.org/abs/2505.02012) | 2025.05 | LLM生成SQL | 关注SQL | **我们关注向量操作** |
| [arXiv:2406.09469](https://arxiv.org/abs/2406.09469) | 2024.06 | 符合性测试 | 关注关系数据库 | **我们针对向量数据库** |

### 12.2 我们的独特贡献

**1. 双层有效性模型（理论创新）**
```
现有工作：单层有效性
我们的贡献：双层正交模型
→ 更精确的缺陷分类
```

**2. 语义预言机（技术创新）**
```
现有工作：传统预言机（单调性、一致性）
我们的贡献：语义预言机（相关性、完整性）
→ 处理语义验证难题
```

**3. LLM增强测试生成（方法创新）**
```
现有工作：规则生成或纯LLM生成
我们的贡献：混合生成策略
→ 平衡效率和覆盖率
```

**4. 完整实现（工程贡献）**
```
现有工作：理论或部分实现
我们的贡献：开源完整框架
→ 可复用、可扩展
```

---

## 附录

### A. 支持的数据库（保持不变）

| 数据库 | 版本 | 状态 |
|--------|------|------|
| **Milvus** | v2.6.12 | ✅ 支持 |
| **Qdrant** | v1.17.0 | ✅ 支持 |
| **Weaviate** | v1.36.5 | ✅ 支持 |
| **Pgvector** | v0.8.2 | ✅ 支持 |
| **SeekDB** | - | ⚠️ 实验性 |
| **Mock** | - | ✅ 测试用 |

### B. 参考文献

**核心参考文献：**
1. Towards Reliable Vector Database Management Systems: A Software Testing Roadmap for 2030. arXiv:2502.20812, 2025.
2. Toward Understanding Bugs in Vector Database Management Systems. arXiv:2506.02617, 2025.
3. Conformance Testing of Relational DBMS Against SQL Specifications. arXiv:2406.09469, 2024.
4. Testing Database Systems with Large Language Model Synthesized SQL. arXiv:2505.02012, 2025.

**GitHub项目参考：**
1. qdrant/vector-db-benchmark - 向量数据库基准测试
2. phodal/mest - 契约测试框架
3. aduquet/RENE-PredictingMetamorphicRelations - 元变态关系预测

---

**文档版本：** v2.0
**最后更新：** 2026-03-27
**下次评审：** 开发方案确定后
