"""
Experiments Module for AI-DB-QC

This module implements baseline comparison experiments to validate
system improvements in defect discovery capability.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

from src.experiments.baseline_comparison import (
    BaselineComparison,
    ExperimentResult,
    ExperimentType,
    DefectRecord,
    BugType,
    generate_reproduction_script,
    run_baseline_comparison,
)
from src.experiments.cross_database_validation import (
    CrossDatabaseValidator,
    CrossDatabaseValidationResult,
    DatabaseTestResult,
    DatabaseType,
    run_cross_database_validation,
)
from src.experiments.stability_testing import (
    StabilityTester,
    StabilityTestResult,
    StabilityStatus,
    StabilityMetrics,
    MemorySnapshot,
    mock_test_iteration,
    run_stability_test,
)

__all__ = [
    # Baseline comparison
    "BaselineComparison",
    "ExperimentResult",
    "ExperimentType",
    "DefectRecord",
    "BugType",
    "generate_reproduction_script",
    "run_baseline_comparison",
    # Cross-database validation
    "CrossDatabaseValidator",
    "CrossDatabaseValidationResult",
    "DatabaseTestResult",
    "DatabaseType",
    "run_cross_database_validation",
    # Stability testing
    "StabilityTester",
    "StabilityTestResult",
    "StabilityStatus",
    "StabilityMetrics",
    "MemorySnapshot",
    "mock_test_iteration",
    "run_stability_test",
]
