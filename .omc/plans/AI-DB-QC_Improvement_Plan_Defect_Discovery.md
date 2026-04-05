# AI-DB-QC 缺陷发现能力提升计划

**计划日期**: 2026-03-30
**核心目标**: 提升真实缺陷发现能力
**改进方向**: 测试能力 + 可观测性 + 工程可靠性
**计划周期**: 8周

---

## 一、当前问题分析

### 1.1 缺陷发现瓶颈

基于代码审查和Harness方法论评估，当前系统在缺陷发现方面存在以下瓶颈：

| 问题类别 | 具体问题 | 影响 | 优先级 |
|---------|---------|------|--------|
| **测试生成** | 语义覆盖率监控已实现，但测试用例多样性不足 | 缺陷发现率受限 | 高 |
| **预言机验证** | 传统预言机完善，语义预言机实现较弱 | Type-4语义缺陷漏检 | 高 |
| **执行可靠性** | 环境故障（Type-2噪声）干扰真实缺陷判断 | 误报率高 | 高 |
| **证据质量** | 缺陷去重简化，证据链不够完整 | 缺陷可信度低 | 中 |
| **可观测性** | JSONL日志完善，但缺少实时监控 | 调试效率低 | 中 |

### 1.2 与目标差距

```
当前状态:                          目标状态:
├─ 测试生成: 混合策略 ✅           ├─ 测试生成: 高多样性 ✅
├─ 预言机: 传统完善 ✅             ├─ 预言机: 语义增强 ✅
├─ 语义预言机: 基础实现 ⚠️         ├─ 语义预言机: 生产级 ✅
├─ 环境可靠性: 基础熔断 ⚠️         ├─ 环境可靠性: 高稳定性 ✅
├─ 缺陷验证: 简化去重 ⚠️           ├─ 缺陷验证: 精确去重 ✅
└─ 可观测性: 文件日志 ⚠️           └─ 可观测性: 实时监控 ✅
```

---

## 二、改进计划概览

### 2.1 三阶段路线图

```
Week 1-2                    Week 3-5                    Week 6-8
┌─────────────┐            ┌─────────────┐            ┌─────────────┐
│  Phase 1:   │            │  Phase 2:   │            │  Phase 3:   │
│  基础加固   │     ──→    │  能力增强   │     ──→    │  实验验证   │
└─────────────┘            └─────────────┘            └─────────────┘
工程可靠性                  测试能力 + 可观测性          缺陷发现实验
```

### 2.2 预期成果

| 指标 | 当前 | 目标 | 提升幅度 |
|------|------|------|----------|
| 真实缺陷发现数 | 0-2/运行 | 5-10/运行 | >300% |
| Type-4语义缺陷检出 | 基础 | 生产级 | 新增能力 |
| 环境噪声误报 | ~30% | <5% | -83% |
| 缺陷验证准确率 | ~70% | >95% | +36% |

---

## 三、Phase 1: 工程可靠性加固 (Week 1-2)

### 目标
消除环境噪声，提升系统稳定性，为缺陷发现提供可靠基础

### 3.1 任务清单

#### P0-1: 环境可靠性提升

**问题**: Milvus异步删除延迟导致"找不到集合"误报

**解决方案**:
```python
# 新增 src/pools/collection_pool.py
from typing import Dict, Optional
import asyncio
from src.adapters.db_adapter import MilvusAdapter

class PersistentCollectionPool:
    """
    持久化集合池 - 解决Type-2环境噪声

    策略：
    1. 预创建固定数量的测试集合
    2. 逻辑删除而非物理删除
    3. 定期清理过期数据
    """

    def __init__(self, adapter: MilvusAdapter, pool_size: int = 5):
        self.adapter = adapter
        self.pool_size = pool_size
        self.collections: Dict[str, bool] = {}  # name -> available
        self.prefix = f"ai_db_qc_pool_{int(time.time())}"

    async def initialize(self, dimensions: [int]):
        """预创建集合池"""
        for i, dim in enumerate(dimensions[:self.pool_size]):
            name = f"{self.prefix}_dim{dim}_{i}"
            success = self.adapter.setup_harness(name, dimension=dim)
            if success:
                self.collections[name] = True
                # 插入初始测试数据
                self._seed_collection(name, dim)

    async def acquire(self, dimension: int) -> Optional[str]:
        """获取可用集合"""
        # 查找匹配维度的可用集合
        for name, available in self.collections.items():
            if available and f"_dim{dimension}_" in name:
                self.collections[name] = False
                return name
        return None

    async def release(self, name: str, clean_data: bool = True):
        """释放集合（逻辑删除）"""
        if clean_data:
            # 清空数据但保留集合结构
            self.adapter.delete_collection_data(name)
        self.collections[name] = True

    def _seed_collection(self, name: str, dimension: int):
        """预填充测试数据"""
        from src.data_generator import ControlledDataGenerator
        generator = ControlledDataGenerator()
        corpus = generator.generate_corpus(size=1000, noise_ratio=0.3)
        # ... 插入数据逻辑
```

**验收标准**:
- [ ] 集合池预创建成功率 > 95%
- [ ] Type-2环境噪声误报率 < 5%
- [ ] 集合获取延迟 < 100ms

---

#### P0-2: 错误处理标准化

**问题**: 错误处理分散，部分失败被静默忽略

**解决方案**:
```python
# 新增 src/exceptions.py
class AIDBQCException(Exception):
    """基础异常类 - 支持证据链"""
    def __init__(self, message: str, evidence: dict = None):
        super().__init__(message)
        self.evidence = evidence or {}

class ContractViolationError(AIDBQCException):
    """契约违规异常"""
    pass

class OracleValidationError(AIDBQCException):
    """预言机验证失败异常"""
    def __init__(self, message: str, oracle_type: str, violation: dict):
        super().__init__(message, evidence={"oracle": oracle_type, "violation": violation})
        self.oracle_type = oracle_type
        self.violation = violation

class EnvironmentNotReadyError(AIDBQCException):
    """环境未就绪异常"""
    pass

class CircuitBreakerOpenError(AIDBQCException):
    """熔断器开启异常"""
    def __init__(self, message: str, failure_count: int, threshold: int):
        super().__init__(message, evidence={
            "failure_count": failure_count,
            "threshold": threshold
        })

# 修改 src/agents/agent3_executor.py
def execute(self, state: WorkflowState) -> WorkflowState:
    try:
        # ... 执行逻辑
        pass
    except EnvironmentNotReadyError as e:
        # 明确的环境错误 - 不计入连续失败
        state.consecutive_failures = 0
        raise
    except ContractViolationError as e:
        # 契约违规 - 记录证据
        state.defect_reports.append(DefectReport(
            case_id=tc.case_id,
            bug_type="Type-1",
            evidence_level="L1",
            root_cause_analysis=str(e),
            raw_evidence=e.evidence
        ))
    except Exception as e:
        # 未知错误 - 计入连续失败
        state.consecutive_failures += 1
        raise
```

**验收标准**:
- [ ] 所有异常继承自 AIDBQCException
- [ ] 每个异常都携带证据信息
- [ ] 错误处理覆盖率 > 90%

---

#### P0-3: 单元测试补充

**问题**: 核心模块缺少单元测试

**解决方案**:
```python
# 新增 tests/unit/test_coverage_monitor.py
import pytest
import numpy as np
from src.coverage_monitor import SemanticCoverageMonitor
from src.state import WorkflowState, TestCase

def test_cosine_similarity():
    monitor = SemanticCoverageMonitor()
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert monitor._cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert monitor._cosine_similarity(v1, v3) == pytest.approx(0.0)

def test_mode_collapse_detection():
    monitor = SemanticCoverageMonitor(similarity_threshold=0.9)
    state = WorkflowState()

    # 添加历史向量
    state.history_vectors = [[1.0, 0.0]] * 20

    # 添加相似的新向量
    state.current_test_cases = [
        TestCase(case_id="test1", query_vector=[1.0, 0.0], dimension=2)
    ]

    new_state = monitor.evaluate_and_mutate(state)

    assert "[FORCED MUTATION]" in new_state.fuzzing_feedback

def test_history_pruning():
    monitor = SemanticCoverageMonitor(history_limit=10)
    state = WorkflowState()

    # 添加超过限制的历史向量
    state.history_vectors = [[i] for i in range(20)]
    state.current_test_cases = [
        TestCase(case_id="test1", query_vector=[100], dimension=1)
    ]

    new_state = monitor.evaluate_and_mutate(state)

    assert len(new_state.history_vectors) == 10
    assert new_state.history_vectors[-1] == [100]

# 新增 tests/unit/test_state.py
def test_workflow_state_validation():
    from src.state import WorkflowState

    state = WorkflowState(
        run_id="test_001",
        target_db_input="Milvus v2.6.12"
    )

    assert state.consecutive_failures == 0
    assert state.max_consecutive_failures == 3
    assert state.max_token_budget == 100000

def test_circuit_breaker_conditions():
    state = WorkflowState(run_id="test", target_db_input="Milvus")

    # 测试token预算熔断
    state.total_tokens_used = 100001
    state.should_terminate = True

    from src.graph import should_continue_fuzzing
    result = should_continue_fuzzing(state)
    assert result == "verify"
```

**验收标准**:
- [ ] 核心模块测试覆盖率 > 80%
- [ ] 所有边界条件有测试覆盖
- [ ] CI集成自动运行测试

---

### 3.2 Phase 1 交付物

| 交付物 | 描述 | 验收标准 |
|--------|------|----------|
| PersistentCollectionPool | 集合池实现 | Type-2误报 < 5% |
| 异常体系 | 标准化错误处理 | 100%新代码使用 |
| 单元测试 | 核心模块测试 | 覆盖率 > 80% |
| 配置中心 | 环境配置统一管理 | 支持多环境切换 |

---

## 四、Phase 2: 测试能力增强 (Week 3-5)

### 目标
提升测试用例生成质量和预言机验证能力，直接提高缺陷发现率

### 4.1 任务清单

#### P1-1: 语义预言机增强

**问题**: 当前语义预言机实现较弱，Type-4语义缺陷检出能力不足

**解决方案**:
```python
# 修改 src/oracles/semantic_oracle.py
from typing import List, Dict, Any
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

class SemanticValidation(BaseModel):
    """语义验证结果"""
    passed: bool
    relevance_scores: List[float] = Field(description="每个结果的相关性分数")
    anomalies: List[Dict[str, Any]] = Field(description="检测到的异常")
    explanation: str = Field(description="异常解释")

class EnhancedSemanticOracle:
    """
    增强语义预言机

    特性：
    1. 少样本学习 - 提供示例提升判断准确性
    2. 多维度评估 - 相关性、完整性、排序
    3. 自适应阈值 - 根据场景调整
    """

    def __init__(self):
        self.llm = ChatAnthropic(
            model_name="glm-4-plus",
            temperature=0.1,
            anthropic_api_url=os.getenv("ANTHROPIC_BASE_URL")
        )
        self.structured_llm = self.llm.with_structured_output(SemanticValidation)

    def verify(self, test_case, result, context) -> Dict[str, Any]:
        """
        语义验证主函数
        """
        # 1. 构建少样本示例
        few_shot_examples = self._build_few_shot_examples(context)

        # 2. 构建验证提示
        prompt = self._build_validation_prompt(
            test_case, result, context, few_shot_examples
        )

        # 3. 执行验证
        validation = self.structured_llm.invoke(prompt)

        return {
            'passed': validation.passed,
            'relevance_scores': validation.relevance_scores,
            'anomalies': validation.anomalies,
            'explanation': validation.explanation
        }

    def _build_few_shot_examples(self, context: str) -> List[Dict]:
        """
        构建少样本示例

        策略：根据业务场景选择相关示例
        """
        examples = {
            "e-commerce": [
                {
                    "query": "查找类似的手机",
                    "results": ["苹果iPhone 15", "华为Mate 60", "小米14"],
                    "judgment": "passed",
                    "reason": "结果都是手机，与查询意图高度相关"
                },
                {
                    "query": "查找类似的手机",
                    "results": ["苹果iPhone 15", "联想笔记本", "小米14"],
                    "judgment": "failed",
                    "reason": "结果中包含笔记本（非手机），属于语义违规"
                }
            ],
            "medical": [
                {
                    "query": "查找类似的心脏病诊断案例",
                    "results": ["病例A: 冠心病", "病例B: 心肌梗死", "病例C: 高血压"],
                    "judgment": "passed",
                    "reason": "结果都是心脏相关疾病"
                }
            ]
        }

        # 根据场景选择示例
        scenario = self._detect_scenario(context)
        return examples.get(scenario, examples["e-commerce"])

    def _build_validation_prompt(self, test_case, result, context, examples):
        """
        构建验证提示词
        """
        return f"""你是一个向量数据库语义验证专家。

你的任务是判断查询结果是否符合查询意图。

**业务场景**: {context.get('scenario', '通用')}

**查询信息**:
- 查询文本: {test_case.query_text}
- 查询意图: {test_case.semantic_intent}
- Top-K: {len(result.items)}

**查询结果**:
{self._format_results(result.items)}

**验证标准**:
1. 相关性: 结果是否与查询意图相关
2. 完整性: 是否遗漏明显相关的结果
3. 排序: 结果是否按相关性排序

**参考示例**:
{self._format_examples(examples)}

**请执行验证并返回结构化结果。"""

    def _detect_scenario(self, context: str) -> str:
        """检测业务场景"""
        keywords = {
            "e-commerce": ["商品", "推荐", "价格", "购物"],
            "medical": ["诊断", "病例", "症状", "治疗"],
            "financial": ["风险", "信用", "交易", "账户"]
        }

        for scenario, kw_list in keywords.items():
            if any(kw in context for kw in kw_list):
                return scenario
        return "general"
```

**验收标准**:
- [ ] 语义预言机准确率 > 85%
- [ ] Type-4缺陷检出率提升 > 50%
- [ ] 验证延迟 < 2秒/case

---

#### P1-2: 测试用例生成优化

**问题**: 测试用例多样性不足，覆盖的边界情况有限

**解决方案**:
```python
# 修改 src/agents/agent2_test_generator.py
class EnhancedTestGenerator:
    """
    增强测试生成器

    策略：
    1. 多样性保证 - 通过聚类确保语义覆盖
    2. 边界探索 - 主动探索语义边界
    3. 对抗生成 - 生成可能欺骗系统的测试
    """

    def __init__(self):
        self.llm = ChatAnthropic(model_name="glm-4-plus", temperature=0.8)
        self.kb = DefectKnowledgeBase()

    def generate_diverse_cases(self, contracts, iteration, feedback, scenario, external_knowledge):
        """
        生成多样化测试用例
        """
        # 1. 基础生成（规则 + LLM）
        base_cases = self._generate_base_cases(contracts, scenario)

        # 2. 语义聚类 - 确保多样性
        diverse_cases = self._cluster_and_select(base_cases, min_diversity=0.7)

        # 3. 边界探索
        boundary_cases = self._generate_boundary_cases(contracts, diverse_cases)

        # 4. 对抗生成
        adversarial_cases = self._generate_adversarial_cases(contracts, diverse_cases)

        # 5. 融合并去重
        all_cases = diverse_cases + boundary_cases + adversarial_cases
        unique_cases = self._deduplicate_by_semantics(all_cases)

        return unique_cases

    def _cluster_and_select(self, cases, min_diversity):
        """
        基于语义聚类选择多样化用例
        """
        from sklearn.cluster import KMeans
        import numpy as np

        # 提取语义向量
        vectors = np.array([self._get_semantic_vector(c) for c in cases])

        # 聚类
        n_clusters = min(len(cases), 5)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(vectors)

        # 从每个簇选择代表
        selected = []
        for i in range(n_clusters):
            cluster_cases = [c for c, l in zip(cases, labels) if l == i]
            # 选择距离簇中心最近的
            selected.append(cluster_cases[0])

        return selected

    def _generate_boundary_cases(self, contracts, existing_cases):
        """
        生成边界测试用例

        策略：在现有用例的语义边界生成新用例
        """
        boundary_cases = []

        for case in existing_cases:
            # 1. 模糊边界
            fuzzy = self.llm.invoke(f"""
            基于以下测试用例，生成一个位于语义模糊边界的测试用例：

            原始用例：
            - 查询: {case.query_text}
            - 意图: {case.semantic_intent}

            请生成一个模糊查询，使得：
            1. 意图不够明确，可能产生多种理解
            2. 可能导致数据库返回不一致的结果
            """)

            # 2. 概念漂移
            drift = self.llm.invoke(f"""
            基于以下测试用例，生成一个概念漂移的测试用例：

            原始用例：
            - 查询: {case.query_text}

            请生成一个用例，其中：
            1. 使用相似但不同的概念
            2. 可能测试数据库的概念泛化能力
            """)

            boundary_cases.extend([fuzzy, drift])

        return boundary_cases

    def _generate_adversarial_cases(self, contracts, existing_cases):
        """
        生成对抗测试用例

        目标：欺骗数据库的语义理解
        """
        adversarial_cases = []

        # 1. 语义干扰
        for case in existing_cases:
            noise_case = self._add_semantic_noise(case)
            adversarial_cases.append(noise_case)

        # 2. 跨域混淆
        cross_domain = self._generate_cross_domain_cases(existing_cases)
        adversarial_cases.extend(cross_domain)

        # 3. 长尾攻击
        long_tail = self._generate_long_tail_cases(existing_cases)
        adversarial_cases.extend(long_tail)

        return adversarial_cases

    def _add_semantic_noise(self, case):
        """添加语义噪声"""
        return TestCase(
            case_id=f"adversarial_noise_{case.case_id}",
            query_text=f"{case.query_text} （但实际查询的是完全无关的内容）",
            dimension=case.dimension,
            semantic_intent="语义干扰测试",
            is_adversarial=True
        )
```

**验收标准**:
- [ ] 测试用例语义多样性 > 0.7
- [ ] 边界用例覆盖率 > 60%
- [ ] 对抗用例检出缺陷率 > 20%

---

#### P1-3: 缺陷去重增强

**问题**: 当前缺陷去重过于简化，可能合并不同的缺陷

**解决方案**:
```python
# 修改 src/agents/agent6_verifier.py
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class EnhancedDefectDeduplicator:
    """
    增强缺陷去重器

    策略：
    1. 多维度相似度计算
    2. 层次化聚类
    3. 人工确认机制
    """

    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = 0.85

    def deduplicate(self, defects: List[DefectReport]) -> List[DefectReport]:
        """
        智能去重
        """
        if len(defects) <= 1:
            return defects

        # 1. 计算多维度相似度矩阵
        similarity_matrix = self._compute_similarity_matrix(defects)

        # 2. 层次化聚类
        clusters = self._hierarchical_clustering(similarity_matrix)

        # 3. 从每个簇选择代表
        unique_defects = []
        for cluster in clusters:
            if len(cluster) == 1:
                unique_defects.append(defects[cluster[0]])
            else:
                # 选择证据最充分的
                representative = self._select_representative(
                    [defects[i] for i in cluster]
                )
                unique_defects.append(representative)

        return unique_defects

    def _compute_similarity_matrix(self, defects):
        """
        计算多维度相似度
        """
        n = len(defects)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i+1, n):
                # 1. bug类型相似度
                type_sim = 1.0 if defects[i].bug_type == defects[j].bug_type else 0.0

                # 2. 根因语义相似度
                cause_i_emb = self.embedder.encode(defects[i].root_cause_analysis)
                cause_j_emb = self.embedder.encode(defects[j].root_cause_analysis)
                cause_sim = cosine_similarity([cause_i_emb], [cause_j_emb])[0][0]

                # 3. case_id相似度（可能测试相同功能）
                case_sim = self._case_similarity(defects[i].case_id, defects[j].case_id)

                # 加权融合
                matrix[i][j] = 0.3 * type_sim + 0.5 * cause_sim + 0.2 * case_sim
                matrix[j][i] = matrix[i][j]

        return matrix

    def _hierarchical_clustering(self, similarity_matrix):
        """
        层次化聚类
        """
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import squareform

        # 转换为距离矩阵
        distance_matrix = 1 - similarity_matrix
        condensed = squareform(distance_matrix)

        # 层次聚类
        Z = linkage(condensed, method='average')
        clusters = fcluster(Z, t=1-self.similarity_threshold, criterion='distance')

        # 组织为簇列表
        cluster_dict = {}
        for i, c in enumerate(clusters):
            if c not in cluster_dict:
                cluster_dict[c] = []
            cluster_dict[c].append(i)

        return list(cluster_dict.values())

    def _select_representative(self, defects):
        """
        选择代表性缺陷

        标准：
        1. 证据最充分
        2. MRE最完整
        3. 错误信息最明确
        """
        def score(defect):
            s = 0
            if defect.raw_evidence:
                s += 3
            if defect.mre_code:
                s += 2
            if defect.error_message and "internal" not in defect.error_message.lower():
                s += 1
            return s

        return max(defects, key=score)
```

**验收标准**:
- [ ] 去重准确率 > 90%
- [ ] 相似缺陷合并率 < 5%
- [ ] 去重延迟 < 1秒

---

### 4.2 Phase 2 交付物

| 交付物 | 描述 | 验收标准 |
|--------|------|----------|
| EnhancedSemanticOracle | 增强语义预言机 | 准确率 > 85% |
| EnhancedTestGenerator | 多样化测试生成器 | 多样性 > 0.7 |
| EnhancedDefectDeduplicator | 智能缺陷去重 | 准确率 > 90% |
| 测试报告 | 能力评估报告 | 量化改进效果 |

---

## 五、Phase 3: 可观测性升级 (Week 6-7)

### 目标
实现实时监控，提升调试效率，快速定位缺陷根因

### 5.1 任务清单

#### P2-1: 实时监控仪表板

**解决方案**:
```python
# 新增 src/dashboard/app.py
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="AI-DB-QC 实时监控", layout="wide")

def load_telemetry(run_id):
    """加载遥测数据"""
    path = f".trae/runs/{run_id}/telemetry.jsonl"
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)

def main():
    st.title("🔍 AI-DB-QC 实时监控仪表板")

    # 侧边栏 - 运行选择
    with st.sidebar:
        st.header("运行控制")
        run_id = st.text_input("Run ID", value="latest")
        auto_refresh = st.checkbox("自动刷新", value=True)
        refresh_interval = st.slider("刷新间隔(秒)", 1, 60, 5)

    # 主界面
    col1, col2, col3, col4 = st.columns(4)

    try:
        df = load_telemetry(run_id)

        # 关键指标卡片
        with col1:
            st.metric("总Token消耗", f"{df['token_usage'].sum():,}")

        with col2:
            st.metric("测试用例数", len(df[df['node_name'] == 'agent2_generator']))

        with col3:
            st.metric("发现缺陷数", len(df[df['event_type'] == 'ERROR']))

        with col4:
            st.metric("运行时长", f"{len(df) * 0.1:.1f}s")

        # Token消耗趋势
        st.subheader("Token消耗趋势")
        df['cumsum_tokens'] = df['token_usage'].cumsum()
        fig = px.line(df, x='timestamp', y='cumsum_tokens',
                     title='累计Token消耗', markers=True)
        st.plotly_chart(fig, use_container_width=True)

        # 节点执行时间
        st.subheader("节点执行分析")
        node_stats = df.groupby('node_name').agg({
            'token_usage': 'sum',
            'event_type': 'count'
        }).reset_index()
        fig = px.bar(node_stats, x='node_name', y='token_usage',
                     title='各节点Token消耗')
        st.plotly_chart(fig, use_container_width=True)

        # 熔断器状态
        st.subheader("熔断器状态")
        consecutive_failures = df['state_delta'].apply(
            lambda x: x.get('consecutive_failures', 0) if isinstance(x, dict) else 0
        ).max()

        if consecutive_failures >= 3:
            st.error(f"⚠️ 熔断器已触发 ({consecutive_failures}/3)")
        else:
            st.success(f"✅ 正常运行 ({consecutive_failures}/3)")

        # 缺陷列表
        st.subheader("发现的缺陷")
        defects = df[df['event_type'] == 'ERROR']
        if not defects.empty:
            for _, defect in defects.iterrows():
                with st.expander(f"❌ {defect['node_name']} - {defect['timestamp']}"):
                    st.json(defect['state_delta'])

    except FileNotFoundError:
        st.warning(f"未找到运行数据: {run_id}")
    except Exception as e:
        st.error(f"加载失败: {str(e)}")

    # 自动刷新
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
```

**启动命令**:
```bash
streamlit run src/dashboard/app.py --server.port 8501
```

**验收标准**:
- [ ] 仪表板实时更新延迟 < 5秒
- [ ] 支持多run_id对比
- [ ] 关键指标可视化完整

---

#### P2-2: 告警系统

**解决方案**:
```python
# 新增 src/alerting/alert_manager.py
from typing import Callable, List
from dataclasses import dataclass

@dataclass
class Alert:
    level: str  # INFO, WARNING, ERROR, CRITICAL
    source: str
    message: str
    metadata: dict

class AlertManager:
    """
    告警管理器

    支持多种告警渠道：
    - 控制台输出
    - 文件日志
    - Webhook（企业微信/钉钉）
    """

    def __init__(self):
        self.handlers: List[Callable] = []
        self.alert_history = []

    def add_handler(self, handler: Callable):
        """添加告警处理器"""
        self.handlers.append(handler)

    def alert(self, level: str, source: str, message: str, **metadata):
        """发送告警"""
        alert = Alert(level=level, source=source, message=message, metadata=metadata)
        self.alert_history.append(alert)

        # 调用所有处理器
        for handler in self.handlers:
            handler(alert)

    def check_circuit_breaker(self, state: WorkflowState):
        """检查熔断器状态"""
        if state.consecutive_failures >= state.max_consecutive_failures:
            self.alert(
                level="CRITICAL",
                source="CircuitBreaker",
                message=f"熔断器触发: 连续失败 {state.consecutive_failures} 次",
                failures=state.consecutive_failures,
                threshold=state.max_consecutive_failures
            )

    def check_token_budget(self, state: WorkflowState):
        """检查Token预算"""
        usage_ratio = state.total_tokens_used / state.max_token_budget
        if usage_ratio > 0.9:
            self.alert(
                level="WARNING",
                source="TokenBudget",
                message=f"Token预算即将耗尽: {usage_ratio*100:.1f}%",
                used=state.total_tokens_used,
                budget=state.max_token_budget
            )
        elif usage_ratio >= 1.0:
            self.alert(
                level="CRITICAL",
                source="TokenBudget",
                message=f"Token预算已耗尽",
                used=state.total_tokens_used,
                budget=state.max_token_budget
            )

# 告警处理器
def console_handler(alert: Alert):
    """控制台输出"""
    colors = {
        "INFO": "\033[94m",     # 蓝色
        "WARNING": "\033[93m",  # 黄色
        "ERROR": "\033[91m",    # 红色
        "CRITICAL": "\033[95m"  # 紫色
    }
    color = colors.get(alert.level, "")
    reset = "\033[0m"
    print(f"{color}[{alert.level}] {reset}{alert.source}: {alert.message}")

def webhook_handler(alert: Alert, webhook_url: str):
    """Webhook通知"""
    import requests

    if alert.level in ["ERROR", "CRITICAL"]:
        payload = {
            "level": alert.level,
            "source": alert.source,
            "message": alert.message,
            "metadata": alert.metadata,
            "timestamp": datetime.now().isoformat()
        }
        requests.post(webhook_url, json=payload)
```

**验收标准**:
- [ ] 关键事件告警覆盖率 100%
- [ ] 告警延迟 < 1秒
- [ ] 支持多种告警渠道

---

### 5.2 Phase 3 交付物

| 交付物 | 描述 | 验收标准 |
|--------|------|----------|
| Streamlit仪表板 | 实时监控界面 | 延迟 < 5秒 |
| AlertManager | 告警管理系统 | 覆盖率 100% |
| 日志聚合器 | 集中日志管理 | 支持查询 |

---

## 六、Phase 4: 缺陷发现实验 (Week 8)

### 目标
在实际数据库上运行，验证缺陷发现能力提升

### 6.1 实验设计

#### 实验A: 基线对比

```
实验组: 使用增强后的系统
对照组: 使用原始系统

变量:
- 测试用例生成策略
- 预言机验证能力
- 环境可靠性

指标:
- 发现的缺陷数量
- 缺陷类型分布
- 误报率
- 运行稳定性
```

#### 实验B: 跨数据库验证

```
测试数据库:
- Milvus v2.6.12
- Qdrant v1.17.0
- Weaviate v1.36.5

场景:
- 电商推荐
- 医疗诊断
- 金融风控

指标:
- 各数据库缺陷数
- Type-4检出率
- 跨数据库一致性
```

#### 实验C: 长期运行测试

```
运行时长: 24小时连续运行

监控:
- 系统稳定性
- 内存泄漏
- Token消耗趋势
- 缺陷发现速率

预期:
- 无崩溃
- 内存稳定
- 缺陷发现持续
```

### 6.2 验收标准

| 指标 | 目标值 | 当前值 | 提升 |
|------|--------|--------|------|
| 真实缺陷发现/运行 | 5-10 | 0-2 | >300% |
| Type-4检出率 | >30% | ~5% | +500% |
| 环境误报率 | <5% | ~30% | -83% |
| 系统稳定性 | 24h无崩溃 | 2-3h | >800% |

---

## 七、风险评估与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM API不稳定 | 高 | 高 | 多模型回退机制 |
| 集合池初始化失败 | 中 | 中 | Fallback到单集合模式 |
| 语义预言机误报高 | 中 | 中 | 人工标注校准集 |
| 性能下降 | 低 | 中 | 异步处理优化 |
| Token成本超预算 | 中 | 低 | 更细粒度预算控制 |

---

## 八、成功标准

### 8.1 技术指标

| 指标 | 目标 |
|------|------|
| 真实缺陷发现数 | ≥5/运行 |
| Type-4检出率 | ≥30% |
| 环境误报率 | ≤5% |
| 系统稳定性 | 24h连续运行 |
| 测试覆盖率 | ≥80% |

### 8.2 学术指标

- 可发表的实验数据
- 与实际bug数据的对比分析
- 理论模型的有效性验证

### 8.3 工程指标

- 代码质量提升
- 文档完善度
- 可复现性保证

---

## 九、后续方向

完成本计划后，可以考虑：

1. **论文撰写**: 基于实验数据撰写学术论文
2. **开源发布**: 清理代码，开源到GitHub
3. **工具化**: 封装为易用的CLI工具
4. **扩展支持**: 添加更多数据库支持

---

**计划制定**: Claude Code (Opus 4.6)
**基于**: Harness方法论 + GitHub同类项目对比
**核心目标**: 提升真实缺陷发现能力
