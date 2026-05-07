"""
Oracles Module for AI-DB-QC

This module implements enhanced semantic oracle capabilities with:
- Evaluator calibration loop
- Sprint contract negotiation
- Grading criteria for test quality
- Few-shot learning examples

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

from src.oracles.enhanced_semantic_oracle import (
    EnhancedSemanticOracle,
    OracleEvaluation,
    EvaluationResult,
)
from src.oracles.evaluator_calibration import (
    EvaluatorCalibrator,
    CalibrationResult,
    CalibrationSample,
)
from src.oracles.sprint_contract import (
    SprintContract,
    ContractProposal,
    ContractStatus,
)
from src.oracles.grading_criteria import (
    GradingCriteria,
    TestDiversityGrader,
    DefectNoveltyGrader,
    ContractAdherenceGrader,
    BugRealismGrader,
    OverallGrade,
)

__all__ = [
    "EnhancedSemanticOracle",
    "OracleEvaluation",
    "EvaluationResult",
    "EvaluatorCalibrator",
    "CalibrationResult",
    "CalibrationSample",
    "SprintContract",
    "ContractProposal",
    "ContractStatus",
    "GradingCriteria",
    "TestDiversityGrader",
    "DefectNoveltyGrader",
    "ContractAdherenceGrader",
    "BugRealismGrader",
    "OverallGrade",
]
