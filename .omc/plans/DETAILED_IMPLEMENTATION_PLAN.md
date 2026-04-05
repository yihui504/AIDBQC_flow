# AI-DB-QC 详细实施计划
## 硬编码任务清单与验收标准

**计划版本**: v1.0
**制定日期**: 2026-03-30
**计划周期**: 8周
**核心目标**: 提升真实缺陷发现能力至5-10个/运行

---

## 目录

- [Phase 1: 工程可靠性加固 (Week 1-2)](#phase-1)
- [Phase 2: 测试能力增强 (Week 3-5)](#phase-2)
- [Phase 3: 可观测性升级 (Week 6-7)](#phase-3)
- [Phase 4: 缺陷发现实验 (Week 8)](#phase-4)
- [验收标准汇总](#验收标准汇总)

---

<a name="phase-1"></a>
## Phase 1: 工程可靠性加固 (Week 1-2)

### 目标
消除环境噪声（Type-2误报），提升系统稳定性，为缺陷发现提供可靠基础

---

### TASK-1.1: PersistentCollectionPool 实现

**优先级**: P0 (Critical)
**预估工时**: 3天
**负责模块**: `src/pools/collection_pool.py`

#### 1.1.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **预创建集合** | 系统启动时预创建固定数量的测试集合 | 集合池初始化成功率 ≥ 95% |
| **逻辑删除** | 删除数据但保留集合结构，避免Milvus异步删除延迟 | 集合复用延迟 < 100ms |
| **自动清理** | 定期清理过期数据，保持集合可用 | 数据清理成功率 ≥ 99% |
| **维度匹配** | 支持多维度集合的智能分配 | 维度匹配准确率 = 100% |
| **并发安全** | 支持多线程/异步并发获取集合 | 无竞态条件 |

#### 1.1.2 接口规范

```python
# src/pools/collection_pool.py
from typing import Dict, List, Optional
import asyncio
import time
from src.adapters.db_adapter import DatabaseAdapter

class CollectionPool:
    """
    持久化集合池

    职责:
    1. 预创建和管理测试集合
    2. 提供线程安全的集合获取/释放
    3. 自动清理过期数据
    4. 监控集合健康状态
    """

    def __init__(
        self,
        adapter: DatabaseAdapter,
        pool_size: int = 5,
        dimensions: List[int] = [128, 256, 384, 512, 768],
        prefix: str = None
    ):
        """
        初始化集合池

        Args:
            adapter: 数据库适配器
            pool_size: 每个维度预创建的集合数量
            dimensions: 支持的维度列表
            prefix: 集合名称前缀（默认: ai_db_qc_pool_{timestamp}）
        """
        self.adapter = adapter
        self.pool_size = pool_size
        self.dimensions = dimensions
        self.prefix = prefix or f"ai_db_qc_pool_{int(time.time())}"

        # 集合状态: name -> {available: bool, dimension: int, created_at: float}
        self.collections: Dict[str, dict] = {}

        # 并发锁
        self._lock = asyncio.Lock()

        # 健康检查
        self._health_check_interval = 300  # 5分钟

    async def initialize(self) -> bool:
        """
        预创建集合池

        Returns:
            bool: 初始化是否成功

        验收标准:
        - 所有维度集合创建成功
        - 每个集合预填充1000条测试数据
        - 初始化时间 < 30秒
        """
        pass

    async def acquire(self, dimension: int, timeout: float = 5.0) -> Optional[str]:
        """
        获取可用集合

        Args:
            dimension: 需要的向量维度
            timeout: 最大等待时间（秒）

        Returns:
            str: 集合名称，失败返回None

        验收标准:
        - 返回匹配维度的可用集合
        - 获取延迟 < 100ms (P99)
        - 超时后返回None
        """
        pass

    async def release(self, collection_name: str, clean_data: bool = True) -> bool:
        """
        释放集合

        Args:
            collection_name: 集合名称
            clean_data: 是否清理数据（保留集合结构）

        Returns:
            bool: 释放是否成功

        验收标准:
        - 数据清理成功率 ≥ 99%
        - 集合标记为可用状态
        - 清理延迟 < 1秒 (1000条数据)
        """
        pass

    async def cleanup(self, max_age_seconds: int = 3600):
        """
        清理过期数据

        Args:
            max_age_seconds: 数据最大保留时间

        验收标准:
        - 保留最近创建的数据
        - 集合结构完整
        - 清理不影响正在使用的集合
        """
        pass

    async def health_check(self) -> Dict[str, bool]:
        """
        健康检查

        Returns:
            Dict[str, bool]: 每个集合的健康状态

        验收标准:
        - 检查集合是否存在
        - 检查集合是否可查询
        - 返回健康状态报告
        """
        pass

    def get_stats(self) -> dict:
        """
        获取池统计信息

        Returns:
            dict: 包含以下字段:
            - total_collections: 总集合数
            - available_collections: 可用集合数
            - acquired_collections: 已获取集合数
            - utilization_rate: 使用率

        验收标准:
        - 统计信息准确
        - 实时更新
        """
        pass
```

#### 1.1.3 测试要求

```python
# tests/unit/test_collection_pool.py
import pytest
import asyncio
from src.pools.collection_pool import CollectionPool
from src.adapters.mock import MockAdapter

@pytest.mark.asyncio
async def test_initialization():
    """测试集合池初始化"""
    adapter = MockAdapter()
    pool = CollectionPool(adapter, pool_size=3, dimensions=[128, 256])

    success = await pool.initialize()

    assert success is True
    stats = pool.get_stats()
    assert stats['total_collections'] == 6  # 3 * 2
    assert stats['available_collections'] == 6

@pytest.mark.asyncio
async def test_acquire_release():
    """测试集合获取和释放"""
    adapter = MockAdapter()
    pool = CollectionPool(adapter, pool_size=2, dimensions=[128])
    await pool.initialize()

    # 获取集合
    collection1 = await pool.acquire(128)
    assert collection1 is not None

    stats = pool.get_stats()
    assert stats['available_collections'] == 1

    # 释放集合
    await pool.release(collection1)
    stats = pool.get_stats()
    assert stats['available_collections'] == 2

@pytest.mark.asyncio
async def test_concurrent_access():
    """测试并发访问"""
    adapter = MockAdapter()
    pool = CollectionPool(adapter, pool_size=5, dimensions=[128])
    await pool.initialize()

    async def acquire_release():
        name = await pool.acquire(128)
        await asyncio.sleep(0.1)
        await pool.release(name)

    # 并发获取
    tasks = [acquire_release() for _ in range(10)]
    await asyncio.gather(*tasks)

    stats = pool.get_stats()
    assert stats['available_collections'] == 5

@pytest.mark.asyncio
async def test_timeout():
    """测试超时机制"""
    adapter = MockAdapter()
    pool = CollectionPool(adapter, pool_size=1, dimensions=[128])
    await pool.initialize()

    # 获取唯一集合
    await pool.acquire(128)

    # 再次获取应该超时
    collection = await pool.acquire(128, timeout=0.5)
    assert collection is None

@pytest.mark.asyncio
async def test_dimension_matching():
    """测试维度匹配"""
    adapter = MockAdapter()
    pool = CollectionPool(adapter, pool_size=2, dimensions=[128, 256])
    await pool.initialize()

    # 获取128维集合
    c128 = await pool.acquire(128)
    assert "_dim128_" in c128

    # 获取256维集合
    c256 = await pool.acquire(256)
    assert "_dim256_" in c256

    # 验证维度不同
    assert c128 != c256
```

#### 1.1.4 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **功能完整性** | 所有接口实现 | 代码审查 |
| **初始化成功率** | ≥ 95% | 运行测试 |
| **获取延迟P99** | < 100ms | 性能测试 |
| **并发安全性** | 无竞态条件 | 并发测试 |
| **数据清理率** | ≥ 99% | 功能测试 |
| **测试覆盖率** | ≥ 90% | pytest-cov |
| **文档完整性** | Docstring覆盖率100% | pydocstyle |

#### 1.1.5 交付物

- [ ] `src/pools/collection_pool.py` - 实现代码
- [ ] `tests/unit/test_collection_pool.py` - 单元测试
- [ ] `docs/collection_pool.md` - 使用文档
- [ ] 性能测试报告 - 延迟、并发数据

---

### TASK-1.2: 异常处理标准化

**优先级**: P0 (Critical)
**预估工时**: 2天
**负责模块**: `src/exceptions.py`

#### 1.2.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **异常层次** | 清晰的异常继承层次 | 所有异常继承自AIDBQCException |
| **证据携带** | 每个异常携带上下文证据 | 100%新异常携带evidence |
| **错误分类** | 按来源分类（契约/预言机/环境） | 分类准确率100% |
| **错误码** | 每个异常有唯一错误码 | 错误码不重复 |

#### 1.2.2 接口规范

```python
# src/exceptions.py
from typing import Dict, Any, Optional
from datetime import datetime

class AIDBQCError(Exception):
    """
    AI-DB-QC 基础异常类

    所有自定义异常必须继承此类

    Attributes:
        message: 错误消息
        error_code: 唯一错误码 (格式: AIDBQC_XXX_YYY)
        evidence: 证据字典
        timestamp: 发生时间
        stack_trace: 堆栈跟踪
    """

    # 错误码计数器（确保唯一性）
    _error_code_counter = 1

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.evidence = evidence or {}
        self.timestamp = datetime.utcnow()
        self.stack_trace = self._capture_stack_trace()

    def _generate_error_code(self) -> str:
        """生成唯一错误码"""
        code = f"AIDBQC_ERR_{AIDBQCError._error_code_counter:04d}"
        AIDBQCError._error_code_counter += 1
        return code

    def _capture_stack_trace(self) -> str:
        """捕获堆栈跟踪"""
        import traceback
        return traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志/序列化）"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace
        }

# ============================================================================
# 契约相关异常
# ============================================================================

class ContractError(AIDBQCError):
    """契约违规异常基类"""
    pass

class L1ContractViolationError(ContractError):
    """
    L1 API契约违规

    触发条件:
    - 参数类型错误
    - 参数范围超出
    - 必填参数缺失

    示例:
        dimension = -1  # 非法维度
        raise L1ContractViolationError(
            message="维度必须为正整数",
            evidence={"dimension": -1, "allowed_range": "[1, 32768]"}
        )
    """

    def __init__(self, message: str, **evidence):
        super().__init__(
            message=message,
            error_code="AIDBQC_L1_001",
            evidence=evidence
        )

class L2ContractViolationError(ContractError):
    """
    L2 运行时契约违规

    触发条件:
    - 集合不存在但错误消息不明确
    - 索引未加载但未正确提示
    - 一致性检查失败

    示例:
        raise L2ContractViolationError(
            message="集合不存在",
            evidence={"collection": "test_collection", "state": "not_found"}
        )
    """

    def __init__(self, message: str, **evidence):
        super().__init__(
            message=message,
            error_code="AIDBQC_L2_001",
            evidence=evidence
        )

# ============================================================================
# 预言机相关异常
# ============================================================================

class OracleError(AIDBQCError):
    """预言机异常基类"""
    pass

class OracleValidationError(OracleError):
    """
    预言机验证失败

    触发条件:
    - 单调性违反
    - 一致性违反
    - 语义违规

    示例:
        raise OracleValidationError(
            message="Top-K单调性违反",
            oracle_type="monotonicity",
            evidence={
                "k10_results": 10,
                "k5_results": 7,
                "expected": "k10应该包含k5的所有结果"
            }
        )
    """

    def __init__(
        self,
        message: str,
        oracle_type: str,
        violation: Dict[str, Any],
        **evidence
    ):
        super().__init__(
            message=message,
            error_code="AIDBQC_ORA_001",
            evidence={
                "oracle_type": oracle_type,
                "violation": violation,
                **evidence
            }
        )
        self.oracle_type = oracle_type
        self.violation = violation

class SemanticOracleError(OracleError):
    """
    语义预言机异常

    触发条件:
    - LLM调用失败
    - 语义解析失败
    - 相关性计算异常
    """

    def __init__(self, message: str, **evidence):
        super().__init__(
            message=message,
            error_code="AIDBQC_SEM_001",
            evidence=evidence
        )

# ============================================================================
# 环境相关异常
# ============================================================================

class EnvironmentError(AIDBQCError):
    """环境异常基类"""
    pass

class EnvironmentNotReadyError(EnvironmentError):
    """
    环境未就绪

    触发条件:
    - 数据库连接失败
    - 集合创建失败
    - 资源不足

    示例:
        raise EnvironmentNotReadyError(
            message="无法连接到数据库",
            evidence={"endpoint": "localhost:19530", "timeout": 5}
        )
    """

    def __init__(self, message: str, **evidence):
        super().__init__(
            message=message,
            error_code="AIDBQC_ENV_001",
            evidence=evidence
        )

class CircuitBreakerOpenError(EnvironmentError):
    """
    熔断器开启异常

    触发条件:
    - 连续失败达到阈值

    示例:
        raise CircuitBreakerOpenError(
            message="连续失败超过阈值",
            failure_count=3,
            threshold=3
        )
    """

    def __init__(self, message: str, failure_count: int, threshold: int):
        super().__init__(
            message=message,
            error_code="AIDBQC_CB_001",
            evidence={
                "failure_count": failure_count,
                "threshold": threshold
            }
        )

# ============================================================================
# 执行相关异常
# ============================================================================

class ExecutionError(AIDBQCError):
    """执行异常基类"""
    pass

class TestExecutionError(ExecutionError):
    """
    测试执行异常

    触发条件:
    - 测试用例执行失败
    - 超时
    - 资源不足
    """

    def __init__(self, message: str, case_id: str, **evidence):
        super().__init__(
            message=message,
            error_code="AIDBQC_EXEC_001",
            evidence={"case_id": case_id, **evidence}
        )

# ============================================================================
# 异常处理工具
# ============================================================================

def handle_exception(
    exc: Exception,
    state: 'WorkflowState',
    escalate: bool = False
) -> None:
    """
    统一异常处理函数

    Args:
        exc: 捕获的异常
        state: 工作流状态
        escalate: 是否升级为严重错误

    行为:
        - AIDBQCError: 记录到state.errors
        - EnvironmentNotReadyError: 不计入连续失败
        - 其他异常: 计入连续失败

    验收标准:
        - 正确处理所有异常类型
        - 证据完整记录到state
    """
    pass
```

#### 1.2.3 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **异常完整性** | 所有预期场景有对应异常 | 代码审查 |
| **错误码唯一性** | 100%不重复 | 自动化测试 |
| **证据携带率** | 100%异常携带evidence | 代码审查 |
| **文档覆盖率** | Docstring 100% | pydocstyle |
| **使用规范** | 所有新代码使用新异常 | 代码审查 |

#### 1.2.4 交付物

- [ ] `src/exceptions.py` - 异常定义
- [ ] `tests/unit/test_exceptions.py` - 单元测试
- [ ] `docs/exception_handling.md` - 异常处理指南
- [ ] 错误码清单文档

---

### TASK-1.3: 单元测试补充

**优先级**: P0 (Critical)
**预估工时**: 3天
**负责模块**: `tests/unit/`

#### 1.3.1 测试覆盖要求

| 模块 | 当前覆盖率 | 目标覆盖率 | 优先级 |
|------|-----------|-----------|--------|
| `coverage_monitor.py` | 0% | ≥90% | P0 |
| `state.py` | 0% | ≥90% | P0 |
| `telemetry.py` | 0% | ≥85% | P0 |
| `graph.py` | 0% | ≥80% | P1 |
| `agents/agent2_test_generator.py` | 0% | ≥75% | P1 |
| `agents/agent3_executor.py` | 0% | ≥75% | P1 |
| `agents/agent4_oracle.py` | 0% | ≥80% | P1 |

#### 1.3.2 测试模板

```python
# tests/unit/test_coverage_monitor.py
import pytest
import numpy as np
from src.coverage_monitor import SemanticCoverageMonitor
from src.state import WorkflowState, TestCase

class TestSemanticCoverageMonitor:
    """语义覆盖率监控器测试"""

    def test_initialization(self):
        """测试初始化"""
        monitor = SemanticCoverageMonitor(
            similarity_threshold=0.85,
            history_limit=50
        )

        assert monitor.similarity_threshold == 0.85
        assert monitor.history_limit == 50

    def test_cosine_similarity_identical(self):
        """测试相同向量余弦相似度"""
        monitor = SemanticCoverageMonitor()
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]

        similarity = monitor._cosine_similarity(v1, v2)

        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        """测试正交向量余弦相似度"""
        monitor = SemanticCoverageMonitor()
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]

        similarity = monitor._cosine_similarity(v1, v2)

        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_empty_vector(self):
        """测试空向量处理"""
        monitor = SemanticCoverageMonitor()

        similarity = monitor._cosine_similarity([], [1.0, 2.0])

        assert similarity == 0.0

    def test_cosine_similarity_different_length(self):
        """测试不同长度向量"""
        monitor = SemanticCoverageMonitor()
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0, 0.0]

        similarity = monitor._cosine_similarity(v1, v2)

        # 应该按最小长度计算
        assert similarity == pytest.approx(1.0)

    def test_mode_collapse_detected(self):
        """测试模式坍塌检测"""
        monitor = SemanticCoverageMonitor(similarity_threshold=0.9)
        state = WorkflowState(run_id="test", target_db_input="Milvus")

        # 添加20个相似的历史向量
        state.history_vectors = [[1.0, 0.0] for _ in range(20)]

        # 添加相似的新向量
        state.current_test_cases = [
            TestCase(
                case_id="test1",
                query_vector=[1.0, 0.0],
                dimension=2,
                query_text="test"
            )
        ]

        new_state = monitor.evaluate_and_mutate(state)

        assert "[FORCED MUTATION]" in new_state.fuzzing_feedback
        assert "Mode collapse detected" in new_state.fuzzing_feedback

    def test_mode_collapse_not_detected(self):
        """测试无模式坍塌"""
        monitor = SemanticCoverageMonitor(similarity_threshold=0.9)
        state = WorkflowState(run_id="test", target_db_input="Milvus")

        # 添加多样的历史向量
        state.history_vectors = [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.5, 0.5]
        ] * 7

        # 添加不同的新向量
        state.current_test_cases = [
            TestCase(
                case_id="test1",
                query_vector=[0.1, 0.9],
                dimension=2,
                query_text="test"
            )
        ]

        new_state = monitor.evaluate_and_mutate(state)

        assert "[FORCED MUTATION]" not in new_state.fuzzing_feedback

    def test_history_pruning(self):
        """测试历史记录裁剪"""
        monitor = SemanticCoverageMonitor(history_limit=10)
        state = WorkflowState(run_id="test", target_db_input="Milvus")

        # 添加超过限制的历史向量
        state.history_vectors = [[i] for i in range(20)]
        state.current_test_cases = [
            TestCase(
                case_id="test1",
                query_vector=[100],
                dimension=1,
                query_text="test"
            )
        ]

        new_state = monitor.evaluate_and_mutate(state)

        # 历史应该被裁剪到最近10个
        assert len(new_state.history_vectors) == 10
        # 最新的向量应该在末尾
        assert new_state.history_vectors[-1] == [100]

    def test_no_test_cases(self):
        """测试无测试用例情况"""
        monitor = SemanticCoverageMonitor()
        state = WorkflowState(run_id="test", target_db_input="Milvus")
        state.current_test_cases = []

        new_state = monitor.evaluate_and_mutate(state)

        assert new_state == state  # 状态不变

    def test_no_query_vector(self):
        """测试无查询向量情况"""
        monitor = SemanticCoverageMonitor()
        state = WorkflowState(run_id="test", target_db_input="Milvus")
        state.current_test_cases = [
            TestCase(
                case_id="test1",
                query_vector=None,
                dimension=2,
                query_text="test"
            )
        ]

        new_state = monitor.evaluate_and_mutate(state)

        assert len(new_state.history_vectors) == 0

# tests/unit/test_state.py
class TestWorkflowState:
    """工作流状态测试"""

    def test_default_values(self):
        """测试默认值"""
        state = WorkflowState(
            run_id="test_001",
            target_db_input="Milvus v2.6.12"
        )

        assert state.consecutive_failures == 0
        assert state.max_consecutive_failures == 3
        assert state.max_token_budget == 100000
        assert state.should_terminate is False
        assert state.iteration_count == 0

    def test_validation(self):
        """测试Pydantic验证"""
        with pytest.raises(ValueError):
            WorkflowState(
                run_id="",  # 空run_id应该失败
                target_db_input=""
            )

    def test_state_immutability_in_copy(self):
        """测试状态复制"""
        state1 = WorkflowState(
            run_id="test",
            target_db_input="Milvus"
        )
        state2 = state1.model_copy()

        state2.consecutive_failures = 5

        assert state1.consecutive_failures == 0
        assert state2.consecutive_failures == 5
```

#### 1.3.3 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **P0模块覆盖率** | ≥90% | pytest-cov |
| **P1模块覆盖率** | ≥75% | pytest-cov |
| **测试通过率** | 100% | pytest |
| **边界条件覆盖** | 100% | 代码审查 |
| **集成测试** | 关键流程有测试 | pytest |

#### 1.3.4 交付物

- [ ] `tests/unit/test_coverage_monitor.py` - 覆盖率监控测试
- [ ] `tests/unit/test_state.py` - 状态管理测试
- [ ] `tests/unit/test_telemetry.py` - 遥测测试
- [ ] `tests/unit/test_exceptions.py` - 异常处理测试
- [ ] 覆盖率报告 - HTML格式

---

### TASK-1.4: 配置中心化

**优先级**: P1 (High)
**预估工时**: 1天
**负责模块**: `src/config.py`

#### 1.4.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **环境变量支持** | 从环境变量读取配置 | 支持所有关键配置 |
| **配置文件支持** | 支持YAML配置文件 | 支持多环境配置 |
| **配置验证** | 启动时验证配置 | 无效配置启动失败 |
| **配置热更新** | 运行时更新配置 | 无需重启 |

#### 1.4.2 接口规范

```python
# src/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional

class AppConfig(BaseSettings):
    """
    应用配置

    从环境变量或配置文件读取
    """

    # LLM配置
    anthropic_api_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/",
        description="Anthropic API地址"
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API密钥"
    )
    llm_model: str = Field(
        default="glm-4-plus",
        description="LLM模型名称"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="LLM温度参数"
    )

    # Token预算配置
    max_token_budget: int = Field(
        default=100000,
        gt=0,
        description="最大Token预算"
    )
    token_warning_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Token警告阈值（比例）"
    )

    # 熔断器配置
    max_consecutive_failures: int = Field(
        default=3,
        gt=0,
        description="最大连续失败次数"
    )

    # 覆盖率监控配置
    similarity_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="语义相似度阈值"
    )
    history_limit: int = Field(
        default=100,
        gt=0,
        description="历史向量数量限制"
    )

    # 集合池配置
    collection_pool_size: int = Field(
        default=5,
        gt=0,
        description="每个维度的集合池大小"
    )
    collection_dimensions: str = Field(
        default="128,256,384,512,768",
        description="支持的维度（逗号分隔）"
    )

    # 数据库配置
    milvus_endpoint: str = Field(
        default="localhost:19530",
        description="Milvus连接地址"
    )

    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    log_file: str = Field(
        default=".trae/runs/telemetry.jsonl",
        description="日志文件路径"
    )

    @validator('collection_dimensions')
    def parse_dimensions(cls, v):
        """解析维度列表"""
        return [int(d.strip()) for d in v.split(',')]

    @validator('log_level')
    def validate_log_level(cls, v):
        """验证日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level: {v}')
        return v.upper()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 全局配置实例
config = AppConfig()
```

#### 1.4.3 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **配置完整性** | 所有配置项有默认值 | 代码审查 |
| **验证有效性** | 无效配置被拒绝 | 测试 |
| **环境变量支持** | 支持所有关键配置 | 测试 |

#### 1.4.4 交付物

- [ ] `src/config.py` - 配置实现
- [ ] `.env.example` - 环境变量模板
- [ ] `config.yaml.example` - 配置文件模板
- [ ] `docs/configuration.md` - 配置文档

---

<a name="phase-2"></a>
## Phase 2: 测试能力增强 (Week 3-5)

### 目标
提升测试用例生成质量和预言机验证能力，直接提高缺陷发现率

---

### TASK-2.1: EnhancedSemanticOracle 实现

**优先级**: P0 (Critical)
**预估工时**: 5天
**负责模块**: `src/oracles/enhanced_semantic_oracle.py`

#### 2.1.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **少样本学习** | 提供示例提升判断准确性 | 准确率 ≥85% |
| **多维度评估** | 相关性、完整性、排序 | 覆盖率 100% |
| **场景自适应** | 根据业务场景调整阈值 | 场景识别率 ≥90% |
| **可解释性** | 生成异常解释 | 解释清晰度评分 ≥4/5 |

#### 2.1.2 接口规范

```python
# src/oracles/enhanced_semantic_oracle.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic

class SemanticValidation(BaseModel):
    """语义验证结果"""
    passed: bool = Field(description="是否通过验证")
    relevance_scores: List[float] = Field(description="每个结果的相关性分数")
    anomalies: List[Dict[str, Any]] = Field(description="检测到的异常列表")
    explanation: str = Field(description="异常解释")
    confidence: float = Field(description="验证置信度", ge=0.0, le=1.0)

class EnhancedSemanticOracle:
    """
    增强语义预言机

    特性:
    1. 少样本学习 - 提供示例提升判断准确性
    2. 多维度评估 - 相关性、完整性、排序
    3. 场景自适应 - 根据场景调整阈值
    4. 可解释性 - 生成详细解释

    验收标准:
    - 准确率 ≥85%
    - 延迟 <2秒/case
    - 场景识别率 ≥90%
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """
        初始化

        Args:
            llm: LLM实例（可选，默认使用配置）
        """
        self.llm = llm or self._default_llm()
        self.structured_llm = self.llm.with_structured_output(SemanticValidation)

        # 场景模板
        self.scenario_templates = self._load_scenario_templates()

    def verify(
        self,
        test_case: 'TestCase',
        result: 'ExecutionResult',
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行语义验证

        Args:
            test_case: 测试用例
            result: 执行结果
            context: 上下文信息（包含场景、契约等）

        Returns:
            Dict: {
                'passed': bool,
                'relevance_scores': List[float],
                'anomalies': List[Dict],
                'explanation': str,
                'confidence': float
            }

        验收标准:
        - 准确率 ≥85%（基于标注集）
        - 延迟 <2秒/case
        - 所有异常包含type和reason字段
        """
        pass

    def _detect_scenario(self, context: Dict[str, Any]) -> str:
        """
        检测业务场景

        Returns:
            str: 场景标识 (e-commerce, medical, financial, general)

        验收标准:
        - 场景识别率 ≥90%
        - 识别延迟 <100ms
        """
        pass

    def _build_few_shot_examples(self, scenario: str) -> List[Dict]:
        """
        构建少样本示例

        Args:
            scenario: 业务场景

        Returns:
            List[Dict]: 示例列表

        验收标准:
        - 每个场景至少3个正例和3个负例
        - 示例覆盖主要缺陷类型
        """
        pass

    def _evaluate_relevance(
        self,
        query_intent: str,
        results: List[Any]
    ) -> List[float]:
        """
        评估结果相关性

        Args:
            query_intent: 查询意图
            results: 结果列表

        Returns:
            List[float]: 相关性分数列表

        验收标准:
        - 分数范围 [0, 1]
        - 与人工标注相关性 ≥0.8
        """
        pass

    def _detect_missing_results(
        self,
        query_intent: str,
        results: List[Any],
        relevance_scores: List[float]
    ) -> Optional[Dict]:
        """
        检测遗漏结果

        验收标准:
        - 召回率估算误差 <20%
        """
        pass

    def _detect_ranking_issues(
        self,
        results: List[Any],
        relevance_scores: List[float]
    ) -> Optional[Dict]:
        """
        检测排序问题

        验收标准:
        - 单调性违反检测率 ≥95%
        """
        pass
```

#### 2.1.3 测试要求

```python
# tests/unit/test_enhanced_semantic_oracle.py
import pytest
from src.oracles.enhanced_semantic_oracle import EnhancedSemanticOracle
from src.state import TestCase, ExecutionResult

class TestEnhancedSemanticOracle:
    """增强语义预言机测试"""

    @pytest.fixture
    def oracle(self):
        return EnhancedSemanticOracle()

    def test_scenario_detection_e_commerce(self, oracle):
        """测试电商场景检测"""
        context = {
            "scenario": "商品推荐",
            "domain": "e-commerce"
        }

        scenario = oracle._detect_scenario(context)

        assert scenario == "e-commerce"

    def test_scenario_detection_medical(self, oracle):
        """测试医疗场景检测"""
        context = {
            "scenario": "诊断案例",
            "domain": "medical"
        }

        scenario = oracle._detect_scenario(context)

        assert scenario == "medical"

    def test_relevance_evaluation(self, oracle):
        """测试相关性评估"""
        query_intent = "查找类似的手机"
        results = [
            {"id": "1", "name": "苹果iPhone 15", "category": "手机"},
            {"id": "2", "name": "华为Mate 60", "category": "手机"},
            {"id": "3", "name": "联想笔记本", "category": "电脑"}  # 不相关
        ]

        scores = oracle._evaluate_relevance(query_intent, results)

        assert len(scores) == 3
        assert scores[0] > 0.7  # iPhone相关
        assert scores[1] > 0.7  # 华为相关
        assert scores[2] < 0.5  # 笔记本不相关

    def test_full_verification_passed(self, oracle):
        """测试完整验证 - 通过"""
        test_case = TestCase(
            case_id="test1",
            query_text="查找类似的手机",
            dimension=128,
            semantic_intent="相似商品搜索"
        )

        result = ExecutionResult(
            case_id="test1",
            success=True,
            l1_passed=True,
            l2_passed=True,
            raw_response=[
                {"id": "1", "name": "苹果iPhone 15"},
                {"id": "2", "name": "华为Mate 60"}
            ]
        )

        context = {"scenario": "电商", "domain": "e-commerce"}

        validation = oracle.verify(test_case, result, context)

        assert validation['passed'] is True
        assert validation['confidence'] > 0.8

    def test_full_verification_failed_irrelevant(self, oracle):
        """测试完整验证 - 不相关结果"""
        test_case = TestCase(
            case_id="test1",
            query_text="查找类似的手机",
            dimension=128,
            semantic_intent="相似商品搜索"
        )

        result = ExecutionResult(
            case_id="test1",
            success=True,
            l1_passed=True,
            l2_passed=True,
            raw_response=[
                {"id": "1", "name": "苹果iPhone 15"},
                {"id": "2", "name": "联想笔记本"}  # 不相关
            ]
        )

        context = {"scenario": "电商", "domain": "e-commerce"}

        validation = oracle.verify(test_case, result, context)

        assert validation['passed'] is False
        assert len(validation['anomalies']) > 0
        assert any(a['type'] == 'irrelevant_result' for a in validation['anomalies'])
```

#### 2.1.4 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **准确率** | ≥85% | 标注集测试 |
| **召回率** | ≥80% | 标注集测试 |
| **延迟** | <2秒/case (P99) | 性能测试 |
| **场景识别率** | ≥90% | 测试集验证 |
| **测试覆盖率** | ≥85% | pytest-cov |

#### 2.1.5 交付物

- [ ] `src/oracles/enhanced_semantic_oracle.py` - 实现
- [ ] `tests/unit/test_enhanced_semantic_oracle.py` - 测试
- [ ] 标注集 - 至少100个样本
- [ ] 评估报告 - 准确率、召回率、F1

---

### TASK-2.2: EnhancedTestGenerator 实现

**优先级**: P0 (Critical)
**预估工时**: 4天
**负责模块**: `src/agents/enhanced_test_generator.py`

#### 2.2.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **多样性保证** | 通过聚类确保语义覆盖 | 语义多样性 ≥0.7 |
| **边界探索** | 主动探索语义边界 | 边界用例覆盖率 ≥60% |
| **对抗生成** | 生成对抗样本 | 对抗用例检出率 ≥20% |
| **RAG增强** | 基于历史缺陷生成 | 历史利用率 ≥80% |

#### 2.2.2 接口规范

```python
# src/agents/enhanced_test_generator.py
from typing import List, Dict, Any
from pydantic import BaseModel
from sklearn.cluster import KMeans
import numpy as np

class TestGenerationMetrics(BaseModel):
    """测试生成指标"""
    total_generated: int
    diverse_cases: int
    boundary_cases: int
    adversarial_cases: int
    diversity_score: float
    semantic_coverage: float

class EnhancedTestGenerator:
    """
    增强测试用例生成器

    特性:
    1. 语义聚类确保多样性
    2. 边界探索用例
    3. 对抗样本生成
    4. RAG历史缺陷利用

    验收标准:
    - 语义多样性 ≥0.7
    - 边界覆盖率 ≥60%
    - 对抗检出率 ≥20%
    """

    def __init__(self):
        self.llm = self._create_llm()
        self.kb = self._create_knowledge_base()
        self.embedder = self._create_embedder()

    def generate_diverse_cases(
        self,
        contracts: 'Contract',
        iteration: int,
        feedback: str,
        scenario: str,
        external_knowledge: str
    ) -> List['TestCase']:
        """
        生成多样化测试用例

        Args:
            contracts: 契约约束
            iteration: 当前迭代
            feedback: 反馈信息
            scenario: 业务场景
            external_knowledge: 外部知识

        Returns:
            List[TestCase]: 去重后的测试用例

        验收标准:
        - 语义多样性 ≥0.7
        - 至少包含50%规则用例和50%LLM用例
        """
        pass

    def _cluster_and_select(
        self,
        cases: List['TestCase'],
        min_diversity: float = 0.7
    ) -> List['TestCase']:
        """
        基于语义聚类选择多样化用例

        Args:
            cases: 候选用例
            min_diversity: 最小多样性阈值

        Returns:
            List[TestCase]: 选择后的用例

        验收标准:
        - 聚类内相似度 ≥0.8
        - 聚类间相似度 ≤0.3
        """
        pass

    def _generate_boundary_cases(
        self,
        contracts: 'Contract',
        existing_cases: List['TestCase']
    ) -> List['TestCase']:
        """
        生成边界测试用例

        类型:
        1. 模糊边界 - 意图不明确
        2. 概念边界 - 相似概念边缘
        3. 参数边界 - API参数边界

        验收标准:
        - 边界用例覆盖率 ≥60%
        """
        pass

    def _generate_adversarial_cases(
        self,
        contracts: 'Contract',
        existing_cases: List['TestCase']
    ) -> List['TestCase']:
        """
        生成对抗测试用例

        类型:
        1. 语义干扰 - 添加噪声
        2. 跨域混淆 - 不同领域混合
        3. 长尾攻击 - 罕见场景

        验收标准:
        - 对抗用例检出率 ≥20%
        """
        pass

    def calculate_metrics(
        self,
        cases: List['TestCase']
    ) -> TestGenerationMetrics:
        """
        计算生成指标

        Returns:
            TestGenerationMetrics: 生成指标

        验收标准:
        - 多样性分数准确
        - 语义覆盖率计算正确
        """
        pass
```

#### 2.2.3 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **语义多样性** | ≥0.7 | 多样性算法测试 |
| **边界覆盖率** | ≥60% | 边界检测测试 |
| **对抗检出率** | ≥20% | 对抗测试 |
| **测试覆盖率** | ≥80% | pytest-cov |

#### 2.2.4 交付物

- [ ] `src/agents/enhanced_test_generator.py` - 实现
- [ ] `tests/unit/test_enhanced_test_generator.py` - 测试
- [ ] 多样性评估报告

---

### TASK-2.3: EnhancedDefectDeduplicator 实现

**优先级**: P1 (High)
**预估工时**: 3天
**负责模块**: `src/defects/enhanced_deduplicator.py`

#### 2.3.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **多维度相似度** | bug类型、根因语义、case_id | 综合准确率 ≥90% |
| **层次化聚类** | 智能合并相似缺陷 | 合并准确率 ≥95% |
| **代表选择** | 选择证据最充分的缺陷 | 代表准确率 ≥90% |

#### 2.3.2 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **去重准确率** | ≥90% | 标注集测试 |
| **召回率** | ≥95% | 标注集测试 |
| **延迟** | <1秒/100缺陷 | 性能测试 |

#### 2.3.3 交付物

- [ ] `src/defects/enhanced_deduplicator.py` - 实现
- [ ] `tests/unit/test_enhanced_deduplicator.py` - 测试
- [ ] 去重评估报告

---

<a name="phase-3"></a>
## Phase 3: 可观测性升级 (Week 6-7)

### 目标
实现实时监控，提升调试效率，快速定位缺陷根因

---

### TASK-3.1: Streamlit实时监控仪表板

**优先级**: P1 (High)
**预估工时**: 3天
**负责模块**: `src/dashboard/app.py`

#### 3.1.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **实时更新** | 自动刷新数据 | 更新延迟 <5秒 |
| **多run对比** | 支持多次运行对比 | 支持至少3个run |
| **关键指标** | Token、缺陷、状态 | 完整显示 |
| **交互操作** | 暂停/继续/切换run | 响应时间 <500ms |

#### 3.1.2 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **更新延迟** | <5秒 | 性能测试 |
| **多run支持** | ≥3个run | 功能测试 |
| **响应时间** | <500ms | 性能测试 |

#### 3.1.3 交付物

- [ ] `src/dashboard/app.py` - 仪表板实现
- [ ] `requirements-dashboard.txt` - 依赖
- [ ] `docs/dashboard_guide.md` - 使用指南

---

### TASK-3.2: AlertManager告警系统

**优先级**: P1 (High)
**预估工时**: 2天
**负责模块**: `src/alerting/alert_manager.py`

#### 3.2.1 功能要求

| 功能点 | 描述 | 验收标准 |
|--------|------|----------|
| **多级告警** | INFO/WARNING/ERROR/CRITICAL | 4级完整 |
| **多渠道** | 控制台/文件/Webhook | 3种渠道 |
| **告警规则** | 可配置规则 | 支持自定义 |

#### 3.2.2 验收标准

| 检查项 | 标准 | 检测方法 |
|--------|------|----------|
| **告警覆盖率** | 100%关键事件 | 测试 |
| **延迟** | <1秒 | 性能测试 |

#### 3.2.3 交付物

- [ ] `src/alerting/alert_manager.py` - 告警管理器
- [ ] `src/alerting/handlers.py` - 处理器实现
- [ ] `docs/alerting_guide.md` - 配置指南

---

<a name="phase-4"></a>
## Phase 4: 缺陷发现实验 (Week 8)

### 目标
在实际数据库上运行，验证缺陷发现能力提升

---

### TASK-4.1: 基线对比实验

**优先级**: P0 (Critical)
**预估工时**: 2天

#### 4.1.1 实验设计

```
实验组: 增强后的系统
对照组: 原始系统

变量控制:
- 相同的测试时长
- 相同的数据库
- 相同的场景

指标对比:
- 发现缺陷数
- 缺陷类型分布
- 误报率
- 系统稳定性
```

#### 4.1.2 验收标准

| 指标 | 目标值 | 检测方法 |
|------|--------|----------|
| **缺陷发现数提升** | ≥300% | 统计分析 |
| **Type-4检出率** | ≥30% | 分类统计 |
| **误报率降低** | ≥80% | 对比分析 |

#### 4.1.3 交付物

- [ ] 实验报告 - 对比分析
- [ ] 缺陷清单 - 发现的所有缺陷
- [ ] 可复现脚本 - 实验复现

---

### TASK-4.2: 跨数据库验证

**优先级**: P1 (High)
**预估工时**: 2天

#### 4.2.1 实验设计

```
测试数据库:
- Milvus v2.6.12
- Qdrant v1.17.0
- Weaviate v1.36.5

场景:
- 电商推荐
- 医疗诊断
- 金融风控
```

#### 4.2.2 验收标准

| 指标 | 目标值 | 检测方法 |
|------|--------|----------|
| **跨数据库一致性** | ≥80% | 统计分析 |
| **缺陷发现总数** | ≥15 | 统计 |

#### 4.2.3 交付物

- [ ] 跨数据库实验报告
- [ ] 各数据库缺陷清单

---

### TASK-4.3: 长期稳定性测试

**优先级**: P1 (High)
**预估工时**: 1天

#### 4.3.1 实验设计

```
运行时长: 24小时连续运行

监控指标:
- 系统稳定性（无崩溃）
- 内存泄漏
- Token消耗趋势
- 缺陷发现速率
```

#### 4.3.2 验收标准

| 指标 | 目标值 | 检测方法 |
|------|--------|----------|
| **运行稳定性** | 24h无崩溃 | 监控 |
| **内存稳定** | 增长 <10%/h | 监控 |
| **缺陷持续发现** | 持续 | 统计 |

#### 4.3.3 交付物

- [ ] 稳定性测试报告
- [ ] 监控数据

---

<a name="验收标准汇总"></a>
## 验收标准汇总

### 技术指标

| 指标类别 | 指标名称 | 目标值 | 当前值 | 提升 |
|---------|---------|--------|--------|------|
| **缺陷发现** | 真实缺陷数/运行 | ≥5-10 | 0-2 | >300% |
| **缺陷发现** | Type-4检出率 | ≥30% | ~5% | +500% |
| **环境可靠性** | Type-2误报率 | <5% | ~30% | -83% |
| **系统稳定性** | 连续运行时长 | ≥24h | 2-3h | >800% |
| **测试质量** | 测试覆盖率 | ≥80% | ~20% | +300% |
| **预言机** | 语义预言机准确率 | ≥85% | ~60% | +42% |
| **测试生成** | 语义多样性 | ≥0.7 | ~0.3 | +133% |

### 学术指标

- [ ] 可发表的实验数据
- [ ] 与实际bug数据的对比分析
- [ ] 理论模型的有效性验证

### 交付物清单

#### 代码交付物

- [ ] `src/pools/collection_pool.py` - 集合池
- [ ] `src/exceptions.py` - 异常体系
- [ ] `src/config.py` - 配置中心
- [ ] `src/oracles/enhanced_semantic_oracle.py` - 增强语义预言机
- [ ] `src/agents/enhanced_test_generator.py` - 增强测试生成器
- [ ] `src/defects/enhanced_deduplicator.py` - 增强去重器
- [ ] `src/dashboard/app.py` - 监控仪表板
- [ ] `src/alerting/alert_manager.py` - 告警管理器

#### 测试交付物

- [ ] `tests/unit/test_collection_pool.py`
- [ ] `tests/unit/test_exceptions.py`
- [ ] `tests/unit/test_coverage_monitor.py`
- [ ] `tests/unit/test_state.py`
- [ ] `tests/unit/test_enhanced_semantic_oracle.py`
- [ ] `tests/unit/test_enhanced_test_generator.py`
- [ ] `tests/unit/test_enhanced_deduplicator.py`

#### 文档交付物

- [ ] `docs/collection_pool.md` - 集合池使用指南
- [ ] `docs/exception_handling.md` - 异常处理指南
- [ ] `docs/configuration.md` - 配置指南
- [ ] `docs/dashboard_guide.md` - 仪表板指南
- [ ] `docs/alerting_guide.md` - 告警配置指南

#### 实验交付物

- [ ] 基线对比实验报告
- [ ] 跨数据库实验报告
- [ ] 稳定性测试报告
- [ ] 缺陷清单（含MRE）

---

**计划制定**: Claude Code (Opus 4.6)
**审核状态**: 待审核
**版本**: v1.0
