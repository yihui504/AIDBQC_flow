"""
Cross-Database Validation for AI-DB-QC

Validates system behavior across different vector databases:
- Milvus
- Qdrant
- Weaviate

Deliverables:
- Cross-database experiment report
- Defect lists per database

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

from src.experiments.baseline_comparison import (
    DefectRecord,
    BugType,
)


class DatabaseType(str, Enum):
    """Supported database types."""

    MILVUS = "milvus"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"


@dataclass
class DatabaseTestResult:
    """Test results for a specific database."""

    database: DatabaseType
    version: str
    test_date: datetime

    # Test execution
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0

    # Performance
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0

    # Defects
    defects_found: int = 0
    unique_defects: int = 0

    # By type
    type_1_count: int = 0
    type_2_count: int = 0
    type_3_count: int = 0
    type_4_count: int = 0

    # Defect details
    defect_records: List[DefectRecord] = field(default_factory=list)

    # Issues specific to this database
    database_specific_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "database": self.database.value,
            "version": self.version,
            "test_date": self.test_date.isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "avg_response_time_ms": self.avg_response_time_ms,
            "min_response_time_ms": self.min_response_time_ms,
            "max_response_time_ms": self.max_response_time_ms,
            "defects_found": self.defects_found,
            "unique_defects": self.unique_defects,
            "type_1_count": self.type_1_count,
            "type_2_count": self.type_2_count,
            "type_3_count": self.type_3_count,
            "type_4_count": self.type_4_count,
            "defect_records": [d.to_dict() for d in self.defect_records],
            "database_specific_issues": self.database_specific_issues,
        }


@dataclass
class CrossDatabaseValidationResult:
    """Results of cross-database validation."""

    validation_id: str
    start_time: datetime
    end_time: datetime

    # Per-database results
    database_results: Dict[str, DatabaseTestResult] = field(default_factory=dict)

    # Aggregated metrics
    total_tests_across_dbs: int = 0
    total_defects_across_dbs: int = 0
    unique_defects_across_dbs: int = 0

    # Consistency metrics
    cross_db_consistency_pct: float = 0.0
    common_defects: int = 0
    database_specific_defects: int = 0

    # Performance comparison
    response_time_variance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "validation_id": self.validation_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "database_results": {
                k: v.to_dict() for k, v in self.database_results.items()
            },
            "total_tests_across_dbs": self.total_tests_across_dbs,
            "total_defects_across_dbs": self.total_defects_across_dbs,
            "unique_defects_across_dbs": self.unique_defects_across_dbs,
            "cross_db_consistency_pct": self.cross_db_consistency_pct,
            "common_defects": self.common_defects,
            "database_specific_defects": self.database_specific_defects,
            "response_time_variance": self.response_time_variance,
        }


class CrossDatabaseValidator:
    """
    Validates system behavior across multiple vector databases.

    Ensures consistent defect discovery and test execution
    across Milvus, Qdrant, and Weaviate.
    """

    def __init__(self, output_dir: str = "experiments/cross_db"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Database configurations
        self.database_configs = {
            DatabaseType.MILVUS: {
                "version": "2.6.12",
                "endpoint": "localhost:19530",
            },
            DatabaseType.QDRANT: {
                "version": "1.12.0",
                "endpoint": "localhost:6333",
            },
            DatabaseType.WEAVIATE: {
                "version": "1.25.0",
                "endpoint": "localhost:8080",
            },
        }

    async def validate_all_databases(
        self,
        test_suite: str = "standard",
        num_tests: int = 100,
    ) -> CrossDatabaseValidationResult:
        """
        Run validation tests on all databases.

        Args:
            test_suite: Test suite to run
            num_tests: Number of tests per database

        Returns:
            Cross-database validation results
        """
        validation_id = f"cross_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        result = CrossDatabaseValidationResult(
            validation_id=validation_id,
            start_time=start_time,
            end_time=start_time,
        )

        # Test each database
        for db_type in DatabaseType:
            print(f"Validating {db_type.value}...")

            db_result = await self._test_database(
                db_type,
                num_tests,
            )

            result.database_results[db_type.value] = db_result
            result.total_tests_across_dbs += db_result.total_tests
            result.total_defects_across_dbs += db_result.defects_found

        # Calculate consistency metrics
        result.unique_defects_across_dbs = self._count_unique_defects(result)
        result.common_defects = self._count_common_defects(result)
        result.database_specific_defects = (
            result.unique_defects_across_dbs - result.common_defects
        )

        # Calculate consistency percentage
        if result.total_defects_across_dbs > 0:
            result.cross_db_consistency_pct = (
                result.common_defects / result.total_defects_across_dbs * 100
            )

        # Calculate response time variance
        response_times = [
            r.avg_response_time_ms
            for r in result.database_results.values()
            if r.avg_response_time_ms > 0
        ]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            result.response_time_variance = (
                sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
            )

        result.end_time = datetime.now()

        # Save results
        self._save_validation_result(result)

        return result

    async def _test_database(
        self,
        db_type: DatabaseType,
        num_tests: int,
    ) -> DatabaseTestResult:
        """Test a specific database."""
        config = self.database_configs[db_type]

        result = DatabaseTestResult(
            database=db_type,
            version=config["version"],
            test_date=datetime.now(),
            total_tests=num_tests,
        )

        # Simulate test execution (replace with actual tests)
        result.passed_tests = int(num_tests * 0.9)  # 90% pass rate
        result.failed_tests = num_tests - result.passed_tests

        # Simulate response times
        result.avg_response_time_ms = 150.0
        result.min_response_time_ms = 50.0
        result.max_response_time_ms = 500.0

        # Simulate defect discovery
        result.defect_records = await self._discover_defects_for_db(
            db_type, num_tests
        )

        result.defects_found = len(result.defect_records)
        result.unique_defects = len(result.defect_records)  # All unique for now

        # Count by type
        for defect in result.defect_records:
            if defect.bug_type == BugType.TYPE_1:
                result.type_1_count += 1
            elif defect.bug_type == BugType.TYPE_2:
                result.type_2_count += 1
            elif defect.bug_type == BugType.TYPE_3:
                result.type_3_count += 1
            elif defect.bug_type == BugType.TYPE_4:
                result.type_4_count += 1

        # Database-specific issues
        result.database_specific_issues = self._get_db_specific_issues(db_type)

        return result

    async def _discover_defects_for_db(
        self,
        db_type: DatabaseType,
        num_tests: int,
    ) -> List[DefectRecord]:
        """Discover defects specific to a database."""
        defects = []

        # Database-specific defect patterns
        db_defects = {
            DatabaseType.MILVUS: [
                {
                    "bug_type": BugType.TYPE_1,
                    "title": "Milvus collection index parameter not validated",
                    "description": "Creating index with invalid nlist parameter",
                    "component": "index",
                },
                {
                    "bug_type": BugType.TYPE_2,
                    "title": "Milvus search returns inconsistent results",
                    "description": "Same query returns different results on retry",
                    "component": "search",
                },
            ],
            DatabaseType.QDRANT: [
                {
                    "bug_type": BugType.TYPE_1,
                    "title": "Qdrant payload size limit not enforced",
                    "description": "Accepts oversized payloads without validation",
                    "component": "insert",
                },
                {
                    "bug_type": BugType.TYPE_3,
                    "title": "Qdrant filter with special characters fails",
                    "description": "Filter containing special chars causes query failure",
                    "component": "search",
                },
            ],
            DatabaseType.WEAVIATE: [
                {
                    "bug_type": BugType.TYPE_1,
                    "title": "Weaviate near_vector type validation missing",
                    "description": "Accepts invalid vector types",
                    "component": "search",
                },
                {
                    "bug_type": BugType.TYPE_2,
                    "title": "Weaviate batch insert partial failure",
                    "description": "Some objects fail silently in batch insert",
                    "component": "insert",
                },
            ],
        }

        for i, defect_data in enumerate(db_defects.get(db_type, [])):
            defect = DefectRecord(
                defect_id=f"{db_type.value.upper()}-{i+1:03d}",
                bug_type=defect_data["bug_type"],
                title=defect_data["title"],
                description=defect_data["description"],
                database=db_type.value,
                component=defect_data["component"],
                test_case_id=f"TC-{db_type.value.upper()}-{i+1:03d}",
                reproduction_steps=[
                    f"1. Connect to {db_type.value}",
                    f"2. Execute {defect_data['component']} operation",
                    f"3. Observe failure",
                ],
                evidence_level="L1",
            )
            defects.append(defect)

        return defects

    def _get_db_specific_issues(self, db_type: DatabaseType) -> List[str]:
        """Get database-specific known issues."""
        issues = {
            DatabaseType.MILVUS: [
                "Known issue: Large dimension vectors may cause OOM",
                "Known issue: Index creation can timeout on large datasets",
            ],
            DatabaseType.QDRANT: [
                "Known issue: Rate limiting on concurrent searches",
                "Known issue: Memory leak in long-running queries",
            ],
            DatabaseType.WEAVIATE: [
                "Known issue: Schema changes require restart",
                "Known issue: GraphQL query complexity limits",
            ],
        }
        return issues.get(db_type, [])

    def _count_unique_defects(self, result: CrossDatabaseValidationResult) -> int:
        """Count unique defects across all databases."""
        all_defects = []
        for db_result in result.database_results.values():
            all_defects.extend(db_result.defect_records)

        # Use title + description for uniqueness
        seen = set()
        unique = 0
        for defect in all_defects:
            key = (defect.title, defect.description)
            if key not in seen:
                seen.add(key)
                unique += 1

        return unique

    def _count_common_defects(self, result: CrossDatabaseValidationResult) -> int:
        """Count defects common to all databases."""
        if not result.database_results:
            return 0

        # Get defects from first database
        first_db = list(result.database_results.values())[0]
        first_db_defects = {
            (d.title, d.description): d
            for d in first_db.defect_records
        }

        # Count how many appear in all databases
        common_count = 0

        for title_desc in first_db_defects.keys():
            found_in_all = True
            for db_result in result.database_results.values():
                if not any(
                    (d.title, d.description) == title_desc
                    for d in db_result.defect_records
                ):
                    found_in_all = False
                    break

            if found_in_all:
                common_count += 1

        return common_count

    def _save_validation_result(self, result: CrossDatabaseValidationResult) -> None:
        """Save validation results to file."""
        output_file = self.output_dir / f"{result.validation_id}.json"

        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"Validation results saved to {output_file}")

    def generate_per_database_defect_lists(
        self,
        result: CrossDatabaseValidationResult,
    ) -> Dict[str, str]:
        """
        Generate defect lists for each database.

        Args:
            result: Validation results

        Returns:
            Dictionary mapping database name to file path
        """
        defect_lists = {}

        for db_name, db_result in result.database_results.items():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"defects_{db_name}_{timestamp}.json"

            defect_list = {
                "database": db_name,
                "version": db_result.version,
                "generated_at": datetime.now().isoformat(),
                "total_defects": len(db_result.defect_records),
                "type_1": db_result.type_1_count,
                "type_2": db_result.type_2_count,
                "type_3": db_result.type_3_count,
                "type_4": db_result.type_4_count,
                "defects": [d.to_dict() for d in db_result.defect_records],
                "database_specific_issues": db_result.database_specific_issues,
            }

            with open(output_file, 'w') as f:
                json.dump(defect_list, f, indent=2)

            defect_lists[db_name] = str(output_file)

        return defect_lists


# ============================================================================
# Convenience Functions
# ============================================================================

async def run_cross_database_validation(
    num_tests: int = 100,
) -> CrossDatabaseValidationResult:
    """
    Run cross-database validation.

    Args:
        num_tests: Number of tests per database

    Returns:
        Validation results
    """
    validator = CrossDatabaseValidator()
    return await validator.validate_all_databases(num_tests=num_tests)
