"""
Baseline Comparison Experiments for AI-DB-QC

Implements experiments to compare defect discovery capability
before and after system enhancements.

Deliverables:
- Baseline comparison report
- Defect lists
- Reproducible test scripts

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json

from pydantic import BaseModel, Field


class ExperimentType(str, Enum):
    """Types of baseline experiments."""

    DEFECT_DISCOVERY = "defect_discovery"
    TYPE_4_DETECTION = "type_4_detection"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    COVERAGE = "coverage"


class BugType(str, Enum):
    """Bug classification types."""

    TYPE_1 = "Type-1"  # Clear API/contract violation
    TYPE_2 = "Type-2"  # Semantic drift
    TYPE_3 = "Type-3"  # Edge/corner case
    TYPE_4 = "Type-4"  # False positive (not a bug)


@dataclass
class DefectRecord:
    """A discovered defect record."""

    defect_id: str
    bug_type: BugType
    title: str
    description: str
    database: str
    component: str

    # Evidence
    test_case_id: str
    reproduction_steps: List[str]
    evidence_level: str  # L1/L2/L3

    # Classification
    is_verified: bool = False
    is_duplicate: bool = False
    is_false_positive: bool = False

    # Timestamps
    discovered_at: datetime = field(default_factory=datetime.now)
    verified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "defect_id": self.defect_id,
            "bug_type": self.bug_type.value,
            "title": self.title,
            "description": self.description,
            "database": self.database,
            "component": self.component,
            "test_case_id": self.test_case_id,
            "reproduction_steps": self.reproduction_steps,
            "evidence_level": self.evidence_level,
            "is_verified": self.is_verified,
            "is_duplicate": self.is_duplicate,
            "is_false_positive": self.is_false_positive,
            "discovered_at": self.discovered_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


@dataclass
class ExperimentResult:
    """Result of a baseline experiment."""

    experiment_id: str
    experiment_type: ExperimentType
    start_time: datetime
    end_time: datetime

    # Test execution
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0

    # Defects discovered
    defects_found: int = 0
    unique_defects: int = 0
    verified_defects: int = 0

    # By type
    type_1_count: int = 0
    type_2_count: int = 0
    type_3_count: int = 0
    type_4_count: int = 0

    # Metrics
    false_positive_rate: float = 0.0
    true_positive_rate: float = 0.0
    defect_discovery_rate: float = 0.0

    # Detailed records
    defect_records: List[DefectRecord] = field(default_factory=list)

    # Comparison
    baseline_defects: int = 0
    improvement_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "experiment_type": self.experiment_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "defects_found": self.defects_found,
            "unique_defects": self.unique_defects,
            "verified_defects": self.verified_defects,
            "type_1_count": self.type_1_count,
            "type_2_count": self.type_2_count,
            "type_3_count": self.type_3_count,
            "type_4_count": self.type_4_count,
            "false_positive_rate": self.false_positive_rate,
            "true_positive_rate": self.true_positive_rate,
            "defect_discovery_rate": self.defect_discovery_rate,
            "baseline_defects": self.baseline_defects,
            "improvement_pct": self.improvement_pct,
            "defect_records": [d.to_dict() for d in self.defect_records],
        }


class BaselineComparison:
    """
    Manages baseline comparison experiments.

    Compares system performance before and after enhancements.
    """

    def __init__(self, output_dir: str = "experiments/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Baseline data (from before enhancement)
        self.baseline_defects_count = 10  # Example: original system found 10 bugs
        self.baseline_type_4_rate = 0.05   # 5% false positive rate

    async def run_defect_discovery_experiment(
        self,
        test_runner: Any,
        num_tests: int = 1000,
        databases: List[str] = None,
    ) -> ExperimentResult:
        """
        Run defect discovery experiment.

        Args:
            test_runner: Test runner instance
            num_tests: Number of tests to execute
            databases: List of databases to test

        Returns:
            ExperimentResult with findings
        """
        databases = databases or ["milvus", "qdrant", "weaviate"]

        experiment_id = f"defect_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        result = ExperimentResult(
            experiment_id=experiment_id,
            experiment_type=ExperimentType.DEFECT_DISCOVERY,
            start_time=start_time,
            end_time=start_time,  # Will update at end
        )

        # Run tests on each database
        all_defects = []

        for db in databases:
            print(f"Testing {db}...")

            # Simulate test execution (replace with actual test runner)
            db_defects = await self._discover_defects_for_db(
                db, num_tests // len(databases)
            )

            all_defects.extend(db_defects)

        # Process results
        result.defect_records = all_defects
        result.defects_found = len(all_defects)

        # Count unique defects (by deduplication)
        unique_defects = []
        seen_hashes = set()
        for defect in all_defects:
            defect_hash = hash(defect.title + defect.description)
            if defect_hash not in seen_hashes:
                seen_hashes.add(defect_hash)
                unique_defects.append(defect)

        result.unique_defects = len(unique_defects)

        # Count by type
        for defect in all_defects:
            if defect.bug_type == BugType.TYPE_1:
                result.type_1_count += 1
            elif defect.bug_type == BugType.TYPE_2:
                result.type_2_count += 1
            elif defect.bug_type == BugType.TYPE_3:
                result.type_3_count += 1
            elif defect.bug_type == BugType.TYPE_4:
                result.type_4_count += 1

        # Calculate metrics
        result.false_positive_rate = (
            result.type_4_count / result.defects_found
            if result.defects_found > 0 else 0.0
        )

        result.defect_discovery_rate = (
            result.unique_defects / num_tests
            if num_tests > 0 else 0.0
        )

        # Compare to baseline
        result.baseline_defects = self.baseline_defects_count
        if result.baseline_defects > 0:
            result.improvement_pct = (
                (result.unique_defects - result.baseline_defects) /
                result.baseline_defects * 100
            )

        result.end_time = datetime.now()

        # Save results
        self._save_experiment_result(result)

        return result

    async def _discover_defects_for_db(
        self,
        database: str,
        num_tests: int,
    ) -> List[DefectRecord]:
        """
        Discover defects for a specific database.

        In production, this would run actual tests.
        For now, returns sample data.
        """
        defects = []

        # Sample defects (replace with actual test results)
        sample_defects = [
            {
                "bug_type": BugType.TYPE_1,
                "title": f"{database} API dimension validation missing",
                "description": "API accepts negative dimension values",
                "component": "insert",
            },
            {
                "bug_type": BugType.TYPE_2,
                "title": f"{database} search result drift",
                "description": "Search results differ for identical queries",
                "component": "search",
            },
            {
                "bug_type": BugType.TYPE_3,
                "title": f"{database} edge case failure",
                "description": "System fails with boundary values",
                "component": "index",
            },
        ]

        for i, sample in enumerate(sample_defects):
            defect = DefectRecord(
                defect_id=f"{database.upper()}-{i+1:03d}",
                bug_type=sample["bug_type"],
                title=sample["title"],
                description=sample["description"],
                database=database,
                component=sample["component"],
                test_case_id=f"TC-{database.upper()}-{i+1:03d}",
                reproduction_steps=[
                    f"1. Connect to {database}",
                    f"2. Execute {sample['component']} operation",
                    f"3. Observe failure",
                ],
                evidence_level="L1",
            )
            defects.append(defect)

        return defects

    def _save_experiment_result(self, result: ExperimentResult) -> None:
        """Save experiment result to file."""
        output_file = self.output_dir / f"{result.experiment_id}.json"

        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"Experiment results saved to {output_file}")

    async def generate_comparison_report(
        self,
        before_result: ExperimentResult,
        after_result: ExperimentResult,
    ) -> Dict[str, Any]:
        """
        Generate comparison report between before and after results.

        Args:
            before_result: Results before enhancement
            after_result: Results after enhancement

        Returns:
            Comparison report
        """
        report = {
            "comparison_id": f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),

            # Defect discovery
            "defects_before": before_result.unique_defects,
            "defects_after": after_result.unique_defects,
            "defects_improvement": after_result.unique_defects - before_result.unique_defects,
            "defects_improvement_pct": (
                (after_result.unique_defects - before_result.unique_defects) /
                before_result.unique_defects * 100
                if before_result.unique_defects > 0 else 0
            ),

            # Type-4 detection
            "type_4_before": before_result.type_4_count,
            "type_4_after": after_result.type_4_count,
            "type_4_detection_rate_before": (
                before_result.type_4_count / before_result.defects_found
                if before_result.defects_found > 0 else 0
            ),
            "type_4_detection_rate_after": (
                after_result.type_4_count / after_result.defects_found
                if after_result.defects_found > 0 else 0
            ),

            # False positive rate
            "fp_rate_before": before_result.false_positive_rate,
            "fp_rate_after": after_result.false_positive_rate,
            "fp_rate_reduction_pct": (
                (before_result.false_positive_rate - after_result.false_positive_rate) /
                before_result.false_positive_rate * 100
                if before_result.false_positive_rate > 0 else 0
            ),

            # By bug type
            "bug_type_comparison": {
                "Type-1": {
                    "before": before_result.type_1_count,
                    "after": after_result.type_1_count,
                },
                "Type-2": {
                    "before": before_result.type_2_count,
                    "after": after_result.type_2_count,
                },
                "Type-3": {
                    "before": before_result.type_3_count,
                    "after": after_result.type_3_count,
                },
                "Type-4": {
                    "before": before_result.type_4_count,
                    "after": after_result.type_4_count,
                },
            },
        }

        # Save report
        report_file = self.output_dir / f"{report['comparison_id']}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def generate_defect_list(
        self,
        result: ExperimentResult,
        output_format: str = "json",
    ) -> str:
        """
        Generate defect list from experiment results.

        Args:
            result: Experiment result
            output_format: Output format (json, csv, markdown)

        Returns:
            Path to generated file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_format == "json":
            output_file = self.output_dir / f"defect_list_{timestamp}.json"

            defect_list = {
                "generated_at": datetime.now().isoformat(),
                "experiment_id": result.experiment_id,
                "total_defects": len(result.defect_records),
                "unique_defects": result.unique_defects,
                "defects": [d.to_dict() for d in result.defect_records],
            }

            with open(output_file, 'w') as f:
                json.dump(defect_list, f, indent=2)

        elif output_format == "markdown":
            output_file = self.output_dir / f"defect_list_{timestamp}.md"

            with open(output_file, 'w') as f:
                f.write(f"# Defect List\n\n")
                f.write(f"Experiment: {result.experiment_id}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Defects: {len(result.defect_records)}\n")
                f.write(f"Unique Defects: {result.unique_defects}\n\n")

                f.write("## Summary by Type\n\n")
                f.write(f"- Type-1: {result.type_1_count}\n")
                f.write(f"- Type-2: {result.type_2_count}\n")
                f.write(f"- Type-3: {result.type_3_count}\n")
                f.write(f"- Type-4: {result.type_4_count}\n\n")

                f.write("## Defect Details\n\n")
                for defect in result.defect_records:
                    f.write(f"### {defect.defect_id}: {defect.title}\n")
                    f.write(f"- **Type**: {defect.bug_type.value}\n")
                    f.write(f"- **Database**: {defect.database}\n")
                    f.write(f"- **Component**: {defect.component}\n")
                    f.write(f"- **Description**: {defect.description}\n")
                    f.write(f"- **Test Case**: {defect.test_case_id}\n")
                    f.write(f"- **Evidence**: {defect.evidence_level}\n\n")

        return str(output_file)


# ============================================================================
# Reproducible Test Scripts
# ============================================================================

def generate_reproduction_script(
    defect: DefectRecord,
    output_dir: str = "experiments/scripts",
) -> str:
    """
    Generate a Python script to reproduce a defect.

    Args:
        defect: Defect record
        output_dir: Output directory for scripts

    Returns:
        Path to generated script
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    script_file = output_path / f"reproduce_{defect.defect_id}.py"

    script_content = f'''"""
Reproduction script for {defect.defect_id}

Bug Type: {defect.bug_type.value}
Title: {defect.title}
Description: {defect.description}

Generated: {datetime.now().isoformat()}
"""

import asyncio
from src.adapters import get_adapter

async def reproduce():
    """Reproduce the defect."""
    print(f"Attempting to reproduce {{defect.defect_id}}...")
    print(f"Bug Type: {{defect.bug_type.value}}")
    print(f"Database: {{defect.database}}")
    print()

    # Get adapter for the database
    adapter = get_adapter({defect.database})

    # Steps to reproduce
    steps = {defect.reproduction_steps}

    for i, step in enumerate(steps, 1):
        print(f"Step {{i}}: {{step}}")
        # Implementation would go here
        print()

    print("Defect reproduction completed.")
    print("Expected: System should handle the operation correctly")
    print("Actual: System fails or behaves incorrectly")

if __name__ == "__main__":
    asyncio.run(reproduce())
'''

    with open(script_file, 'w') as f:
        f.write(script_content)

    return str(script_file)


# ============================================================================
# Convenience Functions
# ============================================================================

async def run_baseline_comparison(
    num_tests: int = 1000,
    databases: List[str] = None,
) -> ExperimentResult:
    """
    Run baseline comparison experiment.

    Args:
        num_tests: Number of tests to execute
        databases: Databases to test

    Returns:
        Experiment result
    """
    comparison = BaselineComparison()

    return await comparison.run_defect_discovery_experiment(
        test_runner=None,  # Would use actual test runner
        num_tests=num_tests,
        databases=databases,
    )
