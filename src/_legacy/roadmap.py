"""
AI-DB-QC 实施路线图硬编码

本模块定义了项目的实施计划和验收标准，用于：
1. 跟踪任务完成状态
2. 自动验证验收标准
3. 生成进度报告
4. 支持增量交付

版本: v1.0
日期: 2026-03-30
"""

from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class Priority(Enum):
    """优先级"""
    P0 = "critical"  # Critical - 必须完成
    P1 = "high"      # High - 重要但不阻塞
    P2 = "medium"    # Medium - 可以延后


class Phase(Enum):
    """Project Phases"""
    PHASE_1_RELIABILITY = "Phase 1: Engineering Reliability"
    PHASE_2_TESTING = "Phase 2: Testing Capability Enhancement"
    PHASE_3_OBSERVABILITY = "Phase 3: Observability Upgrade"
    PHASE_4_VALIDATION = "Phase 4: Defect Discovery Experiments"


@dataclass
class AcceptanceCriteria:
    """
    验收标准

    Attributes:
        metric: 指标名称
        target_value: 目标值
        current_value: 当前值
        unit: 单位
        measurement_method: 检测方法
    """
    metric: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    measurement_method: str = ""

    @property
    def is_met(self) -> bool:
        """检查是否达标"""
        if self.current_value == 0:
            return False
        if "percent" in self.unit.lower() or "率" in self.metric:
            return self.current_value >= self.target_value
        return self.current_value >= self.target_value

    @property
    def progress_percentage(self) -> float:
        """计算完成百分比"""
        if self.target_value == 0:
            return 0.0
        return min(100.0, (self.current_value / self.target_value) * 100.0)


@dataclass
class Task:
    """
    任务定义

    Attributes:
        id: 任务ID (格式: TASK-X.Y)
        title: 任务标题
        description: 任务描述
        phase: 所属阶段
        priority: 优先级
        estimated_hours: 预估工时（小时）
        status: 任务状态
        deliverables: 交付物列表
        acceptance_criteria: 验收标准列表
        dependencies: 依赖任务ID列表
        assignee: 负责人
        start_date: 开始日期
        due_date: 截止日期
        completed_date: 完成日期
        notes: 备注
    """
    id: str
    title: str
    description: str
    phase: Phase
    priority: Priority
    estimated_hours: float
    status: TaskStatus = TaskStatus.PENDING
    deliverables: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    assignee: str = ""
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    notes: str = ""

    @property
    def is_ready_to_start(self) -> bool:
        """检查是否可以开始（所有依赖已完成）"""
        return all(
            Roadmap.get_instance().get_task(dep).status == TaskStatus.COMPLETED
            for dep in self.dependencies
            if Roadmap.get_instance().get_task(dep) is not None
        )

    @property
    def completion_percentage(self) -> float:
        """计算任务完成百分比"""
        if not self.acceptance_criteria:
            return 100.0 if self.status == TaskStatus.COMPLETED else 0.0

        if self.status == TaskStatus.COMPLETED:
            return 100.0

        total_progress = sum(c.progress_percentage for c in self.acceptance_criteria)
        return total_progress / len(self.acceptance_criteria)

    @property
    def acceptance_criteria_met(self) -> bool:
        """检查所有验收标准是否满足"""
        return all(c.is_met for c in self.acceptance_criteria)


class Roadmap:
    """
    实施路线图

    单例模式，全局访问
    """

    _instance: Optional['Roadmap'] = None

    def __init__(self):
        if Roadmap._instance is not None:
            raise RuntimeError("Use Roadmap.get_instance() to get the singleton")
        self.tasks: Dict[str, Task] = {}
        self._initialize_tasks()

    @classmethod
    def get_instance(cls) -> 'Roadmap':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_tasks(self):
        """初始化所有任务"""

        # ====================================================================
        # Phase 1: 工程可靠性加固 (Week 1-2)
        # ====================================================================

        # TASK-1.1: PersistentCollectionPool 实现
        self.tasks["TASK-1.1"] = Task(
            id="TASK-1.1",
            title="PersistentCollectionPool 实现",
            description="预创建集合池，逻辑删除，消除Type-2环境噪声",
            phase=Phase.PHASE_1_RELIABILITY,
            priority=Priority.P0,
            estimated_hours=24,  # 3天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/pools/collection_pool.py",
                "tests/unit/test_collection_pool.py",
                "docs/collection_pool.md",
                "性能测试报告"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="集合池初始化成功率",
                    target_value=95.0,
                    unit="%",
                    measurement_method="运行测试"
                ),
                AcceptanceCriteria(
                    metric="集合复用延迟",
                    target_value=100.0,
                    unit="ms (P99)",
                    measurement_method="性能测试"
                ),
                AcceptanceCriteria(
                    metric="数据清理成功率",
                    target_value=99.0,
                    unit="%",
                    measurement_method="功能测试"
                ),
                AcceptanceCriteria(
                    metric="并发安全性",
                    target_value=100.0,
                    unit="% (无竞态条件)",
                    measurement_method="并发测试"
                ),
                AcceptanceCriteria(
                    metric="测试覆盖率",
                    target_value=90.0,
                    unit="%",
                    measurement_method="pytest-cov"
                )
            ]
        )

        # TASK-1.2: 异常处理标准化
        self.tasks["TASK-1.2"] = Task(
            id="TASK-1.2",
            title="异常处理标准化",
            description="建立异常层次结构，所有异常携带证据",
            phase=Phase.PHASE_1_RELIABILITY,
            priority=Priority.P0,
            estimated_hours=16,  # 2天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/exceptions.py",
                "tests/unit/test_exceptions.py",
                "docs/exception_handling.md",
                "错误码清单"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="异常完整性",
                    target_value=100.0,
                    unit="%",
                    measurement_method="代码审查"
                ),
                AcceptanceCriteria(
                    metric="错误码唯一性",
                    target_value=100.0,
                    unit="%",
                    measurement_method="自动化测试"
                ),
                AcceptanceCriteria(
                    metric="证据携带率",
                    target_value=100.0,
                    unit="%",
                    measurement_method="代码审查"
                ),
                AcceptanceCriteria(
                    metric="文档覆盖率",
                    target_value=100.0,
                    unit="%",
                    measurement_method="pydocstyle"
                )
            ],
            dependencies=["TASK-1.1"]
        )

        # TASK-1.3: 单元测试补充
        self.tasks["TASK-1.3"] = Task(
            id="TASK-1.3",
            title="单元测试补充",
            description="补充核心模块单元测试，覆盖率达标",
            phase=Phase.PHASE_1_RELIABILITY,
            priority=Priority.P0,
            estimated_hours=24,  # 3天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "tests/unit/test_coverage_monitor.py",
                "tests/unit/test_state.py",
                "tests/unit/test_telemetry.py",
                "tests/unit/test_graph.py",
                "覆盖率报告 (HTML)"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="coverage_monitor 覆盖率",
                    target_value=90.0,
                    unit="%",
                    measurement_method="pytest-cov"
                ),
                AcceptanceCriteria(
                    metric="state 覆盖率",
                    target_value=90.0,
                    unit="%",
                    measurement_method="pytest-cov"
                ),
                AcceptanceCriteria(
                    metric="telemetry 覆盖率",
                    target_value=85.0,
                    unit="%",
                    measurement_method="pytest-cov"
                ),
                AcceptanceCriteria(
                    metric="graph 覆盖率",
                    target_value=80.0,
                    unit="%",
                    measurement_method="pytest-cov"
                ),
                AcceptanceCriteria(
                    metric="测试通过率",
                    target_value=100.0,
                    unit="%",
                    measurement_method="pytest"
                )
            ]
        )

        # TASK-1.4: 配置中心化
        self.tasks["TASK-1.4"] = Task(
            id="TASK-1.4",
            title="配置中心化",
            description="统一配置管理，支持环境变量和配置文件",
            phase=Phase.PHASE_1_RELIABILITY,
            priority=Priority.P1,
            estimated_hours=8,  # 1天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/config.py",
                ".env.example",
                "config.yaml.example",
                "docs/configuration.md"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="配置完整性",
                    target_value=100.0,
                    unit="%",
                    measurement_method="代码审查"
                ),
                AcceptanceCriteria(
                    metric="配置验证",
                    target_value=100.0,
                    unit="%",
                    measurement_method="测试"
                )
            ]
        )

        # TASK-1.5: Context Reset Strategy (基于 Anthropic 最佳实践)
        self.tasks["TASK-1.5"] = Task(
            id="TASK-1.5",
            title="Context Reset Strategy 实现",
            description="实现上下文重置策略，解决context anxiety问题。基于Anthropic研究：每N次测试后重置，使用WorkflowState作为结构化交接物",
            phase=Phase.PHASE_1_RELIABILITY,
            priority=Priority.P1,
            estimated_hours=12,  # 1.5天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/context/reset_manager.py",
                "src/context/handoff.py",
                "tests/unit/test_context_reset.py",
                "docs/context_reset_strategy.md"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="Reset成功恢复率",
                    target_value=95.0,
                    unit="%",
                    measurement_method="集成测试"
                ),
                AcceptanceCriteria(
                    metric="状态完整性",
                    target_value=100.0,
                    unit="%",
                    measurement_method="状态验证测试"
                ),
                AcceptanceCriteria(
                    metric="Token效率提升",
                    target_value=20.0,
                    unit="%",
                    measurement_method="Token使用对比"
                ),
                AcceptanceCriteria(
                    metric="上下文焦虑消除",
                    target_value=100.0,
                    unit="%",
                    measurement_method="长运行测试观察"
                )
            ],
            dependencies=["TASK-1.3"]
        )

        # ====================================================================
        # Phase 2: 测试能力增强 (Week 3-5)
        # ====================================================================

        # TASK-2.1: EnhancedSemanticOracle 实现 (基于 Anthropic 评估器校准方法)
        self.tasks["TASK-2.1"] = Task(
            id="TASK-2.1",
            title="EnhancedSemanticOracle + Evaluator Calibration Loop",
            description="增强语义预言机 + 评估器校准循环。基于Anthropic研究: (1) 校准循环: 在已知bug集上运行，对比评估器判断与人工评估，迭代调整prompt直到对齐 (2) Sprint契约: Agent2与Agent4在测试生成前协商成功标准 (3) 明确评分标准: Test Diversity, Defect Novelty, Contract Adherence, Bug Realism (4) Few-shot示例带详细分数分解",
            phase=Phase.PHASE_2_TESTING,
            priority=Priority.P0,
            estimated_hours=48,  # 6天 (增加8h用于校准循环)
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/oracles/enhanced_semantic_oracle.py",
                "src/oracles/evaluator_calibration.py",
                "src/contracts/sprint_contract.py",
                "src/harness/grading_criteria.py",
                "tests/unit/test_enhanced_semantic_oracle.py",
                "tests/unit/test_evaluator_calibration.py",
                "验证集 (100+ 已知bug样本)",
                "Few-shot示例库 (20+ 带评分的样本)",
                "校准报告 (对齐度曲线)"
            ],
            acceptance_criteria=[
                # 评估器精度 (基于Anthropic标准)
                AcceptanceCriteria(
                    metric="评估器精确率",
                    target_value=90.0,
                    unit="%",
                    measurement_method="验证集评估"
                ),
                AcceptanceCriteria(
                    metric="误报率",
                    target_value=10.0,
                    unit="%",
                    measurement_method="验证集评估"
                ),
                # Sprint契约协商
                AcceptanceCriteria(
                    metric="契约协商成功率",
                    target_value=95.0,
                    unit="%",
                    measurement_method="集成测试"
                ),
                AcceptanceCriteria(
                    metric="平均协商轮数",
                    target_value=3.0,
                    unit="轮",
                    measurement_method="统计"
                ),
                # 评分标准
                AcceptanceCriteria(
                    metric="Test Diversity阈值",
                    target_value=0.7,
                    unit="余弦相似度",
                    measurement_method="多样性算法"
                ),
                AcceptanceCriteria(
                    metric="Defect Novelty阈值",
                    target_value=0.8,
                    unit="语义相似度",
                    measurement_method="去重算法"
                ),
                AcceptanceCriteria(
                    metric="Contract Adherence",
                    target_value=100.0,
                    unit="%",
                    measurement_method="L1/L2验证"
                ),
                AcceptanceCriteria(
                    metric="Bug Realism加权分数",
                    target_value=0.75,
                    unit="分数",
                    measurement_method="Type-1/2/3/4分类"
                ),
                # 性能
                AcceptanceCriteria(
                    metric="评估延迟",
                    target_value=2.0,
                    unit="秒/case (P99)",
                    measurement_method="性能测试"
                ),
                AcceptanceCriteria(
                    metric="测试覆盖率",
                    target_value=85.0,
                    unit="%",
                    measurement_method="pytest-cov"
                )
            ],
            dependencies=["TASK-1.2", "TASK-1.4", "TASK-1.5"]
        )

        # TASK-2.2: EnhancedTestGenerator 实现 (集成Sprint契约)
        self.tasks["TASK-2.2"] = Task(
            id="TASK-2.2",
            title="EnhancedTestGenerator + Sprint Contract Integration",
            description="增强测试生成器 + Sprint契约集成。基于Anthropic研究: (1) 在测试生成前与评估器(Agent4)协商契约 (2) 契约定义: test_scope, success_criteria, verification_methods, oracle_constraints (3) 迭代直到双方同意 (4) 生成后自评再交给QA",
            phase=Phase.PHASE_2_TESTING,
            priority=Priority.P0,
            estimated_hours=32,  # 4天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/agents/enhanced_test_generator.py",
                "src/contracts/contract_negotiation.py",
                "tests/unit/test_enhanced_test_generator.py",
                "tests/unit/test_contract_negotiation.py",
                "多样性评估报告",
                "契约协商示例日志"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="语义多样性",
                    target_value=0.7,
                    unit="分数",
                    measurement_method="多样性算法测试"
                ),
                AcceptanceCriteria(
                    metric="边界覆盖率",
                    target_value=60.0,
                    unit="%",
                    measurement_method="边界检测测试"
                ),
                AcceptanceCriteria(
                    metric="对抗检出率",
                    target_value=20.0,
                    unit="%",
                    measurement_method="对抗测试"
                ),
                AcceptanceCriteria(
                    metric="契约合规率",
                    target_value=95.0,
                    unit="%",
                    measurement_method="契约验证"
                ),
                AcceptanceCriteria(
                    metric="测试覆盖率",
                    target_value=80.0,
                    unit="%",
                    measurement_method="pytest-cov"
                )
            ],
            dependencies=["TASK-2.1"]
        )

        # TASK-2.3: EnhancedDefectDeduplicator 实现
        self.tasks["TASK-2.3"] = Task(
            id="TASK-2.3",
            title="EnhancedDefectDeduplicator 实现",
            description="增强缺陷去重器，多维度相似度，层次聚类",
            phase=Phase.PHASE_2_TESTING,
            priority=Priority.P1,
            estimated_hours=24,  # 3天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/defects/enhanced_deduplicator.py",
                "tests/unit/test_enhanced_deduplicator.py",
                "去重评估报告"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="去重准确率",
                    target_value=90.0,
                    unit="%",
                    measurement_method="标注集测试"
                ),
                AcceptanceCriteria(
                    metric="召回率",
                    target_value=95.0,
                    unit="%",
                    measurement_method="标注集测试"
                ),
                AcceptanceCriteria(
                    metric="延迟",
                    target_value=1.0,
                    unit="秒/100缺陷",
                    measurement_method="性能测试"
                )
            ],
            dependencies=["TASK-2.1"]
        )

        # ====================================================================
        # Phase 3: 可观测性升级 (Week 6-7)
        # ====================================================================

        # TASK-3.1: Streamlit实时监控仪表板
        self.tasks["TASK-3.1"] = Task(
            id="TASK-3.1",
            title="Streamlit实时监控仪表板",
            description="实时监控仪表板，关键指标可视化",
            phase=Phase.PHASE_3_OBSERVABILITY,
            priority=Priority.P1,
            estimated_hours=24,  # 3天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/dashboard/app.py",
                "requirements-dashboard.txt",
                "docs/dashboard_guide.md"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="更新延迟",
                    target_value=5.0,
                    unit="秒",
                    measurement_method="性能测试"
                ),
                AcceptanceCriteria(
                    metric="多run支持",
                    target_value=3.0,
                    unit="个",
                    measurement_method="功能测试"
                ),
                AcceptanceCriteria(
                    metric="响应时间",
                    target_value=500.0,
                    unit="ms",
                    measurement_method="性能测试"
                )
            ],
            dependencies=["TASK-1.3", "TASK-1.4"]
        )

        # TASK-3.2: AlertManager告警系统
        self.tasks["TASK-3.2"] = Task(
            id="TASK-3.2",
            title="AlertManager告警系统",
            description="告警管理系统，多渠道通知",
            phase=Phase.PHASE_3_OBSERVABILITY,
            priority=Priority.P1,
            estimated_hours=16,  # 2天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "src/alerting/alert_manager.py",
                "src/alerting/handlers.py",
                "docs/alerting_guide.md"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="告警覆盖率",
                    target_value=100.0,
                    unit="%",
                    measurement_method="测试"
                ),
                AcceptanceCriteria(
                    metric="延迟",
                    target_value=1.0,
                    unit="秒",
                    measurement_method="性能测试"
                )
            ],
            dependencies=["TASK-1.4"]
        )

        # ====================================================================
        # Phase 4: 缺陷发现实验 (Week 8)
        # ====================================================================

        # TASK-4.1: 基线对比实验
        self.tasks["TASK-4.1"] = Task(
            id="TASK-4.1",
            title="基线对比实验",
            description="对比增强前后系统的缺陷发现能力",
            phase=Phase.PHASE_4_VALIDATION,
            priority=Priority.P0,
            estimated_hours=16,  # 2天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "基线对比实验报告",
                "缺陷清单",
                "可复现脚本"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="缺陷发现数提升",
                    target_value=300.0,
                    unit="%",
                    measurement_method="统计分析"
                ),
                AcceptanceCriteria(
                    metric="Type-4检出率",
                    target_value=30.0,
                    unit="%",
                    measurement_method="分类统计"
                ),
                AcceptanceCriteria(
                    metric="误报率降低",
                    target_value=80.0,
                    unit="%",
                    measurement_method="对比分析"
                )
            ],
            dependencies=["TASK-2.1", "TASK-2.2", "TASK-2.3"]
        )

        # TASK-4.2: 跨数据库验证
        self.tasks["TASK-4.2"] = Task(
            id="TASK-4.2",
            title="跨数据库验证",
            description="在Milvus/Qdrant/Weaviate上验证",
            phase=Phase.PHASE_4_VALIDATION,
            priority=Priority.P1,
            estimated_hours=16,  # 2天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "跨数据库实验报告",
                "各数据库缺陷清单"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="跨数据库一致性",
                    target_value=80.0,
                    unit="%",
                    measurement_method="统计分析"
                ),
                AcceptanceCriteria(
                    metric="缺陷发现总数",
                    target_value=15.0,
                    unit="个",
                    measurement_method="统计"
                )
            ],
            dependencies=["TASK-4.1"]
        )

        # TASK-4.3: 长期稳定性测试
        self.tasks["TASK-4.3"] = Task(
            id="TASK-4.3",
            title="长期稳定性测试",
            description="24小时连续运行测试",
            phase=Phase.PHASE_4_VALIDATION,
            priority=Priority.P1,
            estimated_hours=8,  # 1天
            status=TaskStatus.COMPLETED,
            deliverables=[
                "稳定性测试报告",
                "监控数据"
            ],
            acceptance_criteria=[
                AcceptanceCriteria(
                    metric="运行稳定性",
                    target_value=24.0,
                    unit="小时无崩溃",
                    measurement_method="监控"
                ),
                AcceptanceCriteria(
                    metric="内存稳定",
                    target_value=10.0,
                    unit="%/h (增长)",
                    measurement_method="监控"
                )
            ],
            dependencies=["TASK-3.1", "TASK-3.2"]
        )

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_tasks_by_phase(self, phase: Phase) -> List[Task]:
        """获取阶段的所有任务"""
        return [t for t in self.tasks.values() if t.phase == phase]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """获取优先级的所有任务"""
        return [t for t in self.tasks.values() if t.priority == priority]

    def get_pending_tasks(self) -> List[Task]:
        """获取待开始的任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING and t.is_ready_to_start]

    def get_in_progress_tasks(self) -> List[Task]:
        """获取进行中的任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS]

    def get_blocked_tasks(self) -> List[Task]:
        """获取阻塞的任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]

    def update_task_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            if status == TaskStatus.COMPLETED:
                task.completed_date = datetime.now()

    def update_criteria_value(self, task_id: str, criteria_index: int, value: float):
        """更新验收标准当前值"""
        task = self.get_task(task_id)
        if task and 0 <= criteria_index < len(task.acceptance_criteria):
            task.acceptance_criteria[criteria_index].current_value = value

    def get_progress_report(self) -> Dict:
        """获取进度报告"""
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        in_progress_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)

        total_hours = sum(t.estimated_hours for t in self.tasks.values())
        completed_hours = sum(
            t.estimated_hours for t in self.tasks.values()
            if t.status == TaskStatus.COMPLETED
        )

        phase_progress = {}
        for phase in Phase:
            phase_tasks = self.get_tasks_by_phase(phase)
            total = len(phase_tasks)
            completed = sum(1 for t in phase_tasks if t.status == TaskStatus.COMPLETED)
            phase_progress[phase.value] = {
                "total": total,
                "completed": completed,
                "percentage": (completed / total * 100) if total > 0 else 0
            }

        return {
            "summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "total_estimated_hours": total_hours,
                "completed_hours": completed_hours
            },
            "by_phase": phase_progress,
            "pending_tasks": len(self.get_pending_tasks()),
            "blocked_tasks": len(self.get_blocked_tasks())
        }

    def export_to_json(self, filepath: str):
        """导出为JSON"""
        data = {
            "tasks": [],
            "progress_report": self.get_progress_report(),
            "export_date": datetime.now().isoformat()
        }

        for task in self.tasks.values():
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "phase": task.phase.value,
                "priority": task.priority.value,
                "estimated_hours": task.estimated_hours,
                "status": task.status.value,
                "deliverables": task.deliverables,
                "acceptance_criteria": [
                    {
                        "metric": c.metric,
                        "target_value": c.target_value,
                        "current_value": c.current_value,
                        "unit": c.unit,
                        "measurement_method": c.measurement_method,
                        "is_met": c.is_met,
                        "progress_percentage": c.progress_percentage
                    }
                    for c in task.acceptance_criteria
                ],
                "dependencies": task.dependencies,
                "assignee": task.assignee,
                "completion_percentage": task.completion_percentage,
                "is_ready_to_start": task.is_ready_to_start,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "completed_date": task.completed_date.isoformat() if task.completed_date else None,
                "notes": task.notes
            }
            data["tasks"].append(task_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def print_roadmap_summary():
    """Print roadmap summary"""
    import sys
    import io
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    roadmap = Roadmap.get_instance()
    report = roadmap.get_progress_report()

    print("\n" + "="*80)
    print("AI-DB-QC Implementation Roadmap")
    print("="*80)

    print("\n[Overall Progress]")
    summary = report["summary"]
    print(f"  Tasks Completed: {summary['completed_tasks']}/{summary['total_tasks']} ({summary['completion_percentage']:.1f}%)")
    print(f"  In Progress: {summary['in_progress_tasks']}")
    print(f"  Pending: {report['pending_tasks']}")
    print(f"  Blocked: {report['blocked_tasks']}")
    print(f"  Hours: {summary['completed_hours']:.0f}/{summary['total_estimated_hours']:.0f}h")

    print("\n[Progress by Phase]")
    for phase, progress in report["by_phase"].items():
        print(f"  {phase}:")
        print(f"    {progress['completed']}/{progress['total']} ({progress['percentage']:.1f}%)")

    print("\n[Ready to Start Tasks]")
    pending = roadmap.get_pending_tasks()
    for task in pending[:5]:
        print(f"  - {task.id}: {task.title} ({task.estimated_hours}h, {task.priority.value})")

    if len(pending) > 5:
        print(f"  ... and {len(pending) - 5} more tasks")

    print("\n" + "="*80)


if __name__ == "__main__":
    print_roadmap_summary()
