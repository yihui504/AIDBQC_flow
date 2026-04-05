"""
Enhanced Semantic Oracle for AI-DB-QC

Integrates calibration, Sprint contracts, and grading criteria
for comprehensive test evaluation.

Based on Anthropic's oracle research:
- Calibrated evaluator for consistent judgments
- Sprint contracts for agreed-upon success criteria
- Grading criteria for multi-dimensional quality assessment

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.oracles.grading_criteria import (
    GradingCriteria,
    OverallGrade,
    Grade,
    BugType,
)
from src.oracles.sprint_contract import (
    SprintContract,
    SprintContractManager,
    ContractProposal,
    SuccessCriterion,
    CriterionType,
)
from src.oracles.evaluator_calibration import (
    EvaluatorCalibrator,
    CalibrationSample,
    EvaluationJudgment,
    CalibrationResult,
)


class OracleEvaluation(BaseModel):
    """A single oracle evaluation result."""

    evaluation_id: str = Field(description="Unique evaluation identifier")
    test_case_id: str = Field(description="ID of evaluated test case")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Overall verdict
    passed: bool = Field(description="Whether test passed oracle evaluation")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    # Grade breakdown
    overall_grade: Optional[OverallGrade] = None

    # Contract compliance
    contract_compliant: bool = Field(default=True)
    contract_violations: List[str] = Field(default_factory=list)

    # Bug classification
    is_bug: bool = Field(default=False)
    bug_type: Optional[str] = None
    bug_severity: Optional[str] = None  # "critical", "high", "medium", "low"

    # Detailed analysis
    reasoning: str = Field(default="")
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    evaluator_version: str = Field(default="1.0.0")
    calibration_status: str = Field(default="uncalibrated")


class EvaluationResult(BaseModel):
    """Aggregated result for multiple test evaluations."""

    batch_id: str
    evaluations: List[OracleEvaluation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    # Summary statistics
    total_tests: int = Field(default=0)
    passed_tests: int = Field(default=0)
    failed_tests: int = Field(default=0)

    # Bug statistics
    bugs_found: int = Field(default=0)
    bug_type_distribution: Dict[str, int] = Field(default_factory=dict)

    # Quality metrics
    average_diversity: float = Field(default=0.0)
    average_novelty: float = Field(default=0.0)
    average_adherence: float = Field(default=0.0)
    average_realism: float = Field(default=0.0)

    # Contract fulfillment
    contract_fulfilled: bool = Field(default=False)
    contract_score: float = Field(default=0.0)

    def calculate_summary(self):
        """Calculate summary statistics from evaluations."""
        self.total_tests = len(self.evaluations)
        self.passed_tests = sum(1 for e in self.evaluations if e.passed)
        self.failed_tests = self.total_tests - self.passed_tests

        self.bugs_found = sum(1 for e in self.evaluations if e.is_bug)

        for e in self.evaluations:
            if e.bug_type:
                self.bug_type_distribution[e.bug_type] = (
                    self.bug_type_distribution.get(e.bug_type, 0) + 1
                )

        # Calculate averages
        if self.evaluations:
            diversity_scores = [
                e.overall_grade.test_diversity.score
                for e in self.evaluations
                if e.overall_grade
            ]
            novelty_scores = [
                e.overall_grade.defect_novelty.score
                for e in self.evaluations
                if e.overall_grade
            ]
            adherence_scores = [
                e.overall_grade.contract_adherence.score
                for e in self.evaluations
                if e.overall_grade
            ]
            realism_scores = [
                e.overall_grade.bug_realism.score
                for e in self.evaluations
                if e.overall_grade
            ]

            self.average_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0
            self.average_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.0
            self.average_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.0
            self.average_realism = sum(realism_scores) / len(realism_scores) if realism_scores else 0.0


class EnhancedSemanticOracle:
    """
    Enhanced semantic oracle with calibration and Sprint contracts.

    Integrates:
    1. Calibrated evaluator for consistent judgments
    2. Sprint contracts for agreed-upon success criteria
    3. Grading criteria for multi-dimensional assessment
    """

    def __init__(
        self,
        calibrator: Optional[EvaluatorCalibrator] = None,
        contract_manager: Optional[SprintContractManager] = None,
        grading_criteria: Optional[GradingCriteria] = None,
        enable_calibration: bool = True,
        enable_contracts: bool = True,
    ):
        self.calibrator = calibrator or EvaluatorCalibrator()
        self.contract_manager = contract_manager or SprintContractManager()
        self.grading_criteria = grading_criteria or GradingCriteria()

        self.enable_calibration = enable_calibration
        self.enable_contracts = enable_contracts

        # Calibration status
        self.is_calibrated = False
        self.calibration_result: Optional[CalibrationResult] = None

        # Active contract
        self.active_contract: Optional[SprintContract] = None

    async def calibrate(
        self,
        llm_client: Any,
        dataset_path: Optional[str] = None,
        prompt_adjuster: Optional[Callable] = None
    ) -> CalibrationResult:
        """
        Run evaluator calibration.

        Args:
            llm_client: LLM client for evaluation
            dataset_path: Optional path to calibration dataset
            prompt_adjuster: Optional prompt adjustment function

        Returns:
            CalibrationResult
        """
        if dataset_path:
            count = self.calibrator.load_dataset_from_file(dataset_path)
            print(f"Loaded {count} calibration samples from {dataset_path}")

        result = await self.calibrator.calibrate(llm_client, prompt_adjuster)

        self.is_calibrated = True
        self.calibration_result = result

        return result

    async def negotiate_sprint_contract(
        self,
        generator_id: str,
        evaluator_id: str,
        test_scope: Dict[str, Any],
        evaluator_response: Callable,
        generator_response: Optional[Callable] = None
    ) -> SprintContract:
        """
        Negotiate a Sprint contract before test generation.

        Args:
            generator_id: Generator agent ID
            evaluator_id: Evaluator agent ID
            test_scope: Planned test scope
            evaluator_response: Evaluator's response function
            generator_response: Optional generator's counter-response function

        Returns:
            Agreed SprintContract
        """
        initial_proposal = self.contract_manager.create_initial_proposal(
            generator_id,
            evaluator_id,
            test_scope
        )

        contract = await self.contract_manager.negotiate_contract(
            initial_proposal,
            evaluator_response,
            generator_response
        )

        self.active_contract = contract
        return contract

    async def evaluate_test_case(
        self,
        test_case: Dict[str, Any],
        history_vectors: List[List[float]],
        contracts: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None,
        defect_report: Optional[Dict[str, Any]] = None,
        known_defects: Optional[List[Dict[str, Any]]] = None,
        llm_client: Optional[Any] = None,
    ) -> OracleEvaluation:
        """
        Evaluate a single test case.

        Args:
            test_case: The test case to evaluate
            history_vectors: Historical test vectors for diversity
            contracts: Contract constraints
            execution_result: Optional execution result
            defect_report: Optional defect report
            known_defects: Known defects for novelty
            llm_client: Optional LLM for enhanced evaluation

        Returns:
            OracleEvaluation
        """
        # Grade the test case
        overall_grade = await self.grading_criteria.grade_test_case(
            test_case=test_case,
            history_vectors=history_vectors,
            contracts=contracts,
            defect_report=defect_report,
            known_defects=known_defects or [],
            execution_result=execution_result,
            llm_client=llm_client,
        )

        # Determine if test passed
        passed = overall_grade.passed_threshold
        confidence = self._calculate_confidence(overall_grade)

        # Check contract compliance
        contract_compliant, violations = self._check_contract_compliance(
            overall_grade, self.active_contract
        )

        # Bug classification
        is_bug, bug_type, severity = self._classify_bug(
            overall_grade, defect_report, execution_result
        )

        evaluation = OracleEvaluation(
            evaluation_id=f"eval_{datetime.now().timestamp()}",
            test_case_id=test_case.get("case_id", "unknown"),
            passed=passed,
            confidence=confidence,
            overall_grade=overall_grade,
            contract_compliant=contract_compliant,
            contract_violations=violations,
            is_bug=is_bug,
            bug_type=bug_type,
            bug_severity=severity,
            reasoning=overall_grade.bug_realism.reasoning,
            recommendations=overall_grade.recommendations,
            calibration_status="calibrated" if self.is_calibrated else "uncalibrated",
        )

        return evaluation

    async def evaluate_batch(
        self,
        test_cases: List[Dict[str, Any]],
        history_vectors: List[List[float]],
        contracts: Dict[str, Any],
        execution_results: Optional[List[Dict[str, Any]]] = None,
        llm_client: Optional[Any] = None,
    ) -> EvaluationResult:
        """
        Evaluate a batch of test cases.

        Args:
            test_cases: List of test cases to evaluate
            history_vectors: Historical test vectors
            contracts: Contract constraints
            execution_results: Optional execution results
            llm_client: Optional LLM for enhanced evaluation

        Returns:
            EvaluationResult with summary
        """
        batch_id = f"batch_{datetime.now().timestamp()}"
        evaluations = []

        for i, test_case in enumerate(test_cases):
            exec_result = execution_results[i] if execution_results and i < len(execution_results) else None

            evaluation = await self.evaluate_test_case(
                test_case=test_case,
                history_vectors=history_vectors,
                contracts=contracts,
                execution_result=exec_result,
                llm_client=llm_client,
            )

            evaluations.append(evaluation)

        result = EvaluationResult(batch_id=batch_id, evaluations=evaluations)
        result.calculate_summary()

        # Check contract fulfillment
        if self.active_contract:
            fulfillment = self.contract_manager.evaluate_contract_fulfillment(
                self.active_contract,
                [e.model_dump() for e in evaluations],
                [e.overall_grade.model_dump() if e.overall_grade else {} for e in evaluations]
            )
            result.contract_fulfilled = fulfillment["fulfilled"]
            result.contract_score = fulfillment["overall_score"]

        return result

    def _calculate_confidence(self, grade: OverallGrade) -> float:
        """Calculate overall confidence from component grades."""
        confidences = [
            grade.test_diversity.confidence,
            grade.defect_novelty.confidence,
            grade.contract_adherence.confidence,
            grade.bug_realism.confidence,
        ]
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _check_contract_compliance(
        self,
        grade: OverallGrade,
        contract: Optional[SprintContract]
    ) -> Tuple[bool, List[str]]:
        """Check if grade complies with Sprint contract."""
        if not contract:
            return True, []

        violations = []

        for criterion_dict in contract.success_criteria:
            criterion_type = criterion_dict["criterion_type"]
            threshold = criterion_dict["threshold"]

            if criterion_type == CriterionType.TEST_DIVERSITY:
                if grade.test_diversity.score < threshold:
                    violations.append(
                        f"Test diversity {grade.test_diversity.score:.2f} < threshold {threshold}"
                    )

            elif criterion_type == CriterionType.DEFECT_NOVELTY:
                if grade.defect_novelty.score < threshold:
                    violations.append(
                        f"Defect novelty {grade.defect_novelty.score:.2f} < threshold {threshold}"
                    )

            elif criterion_type == CriterionType.CONTRACT_ADHERENCE:
                if grade.contract_adherence.score < threshold:
                    violations.append(
                        f"Contract adherence {grade.contract_adherence.score:.2f} < threshold {threshold}"
                    )

            elif criterion_type == CriterionType.BUG_REALISM:
                if grade.bug_realism.score < threshold:
                    violations.append(
                        f"Bug realism {grade.bug_realism.score:.2f} < threshold {threshold}"
                    )

        return len(violations) == 0, violations

    def _classify_bug(
        self,
        grade: OverallGrade,
        defect_report: Optional[Dict[str, Any]],
        execution_result: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Classify if this is a bug and its type/severity."""
        # If there's a defect report with clear classification
        if defect_report:
            bug_type_str = defect_report.get("bug_type", "")
            if bug_type_str and bug_type_str.startswith("Type-"):
                # Type-4 is false positive (not a bug)
                if bug_type_str == "Type-4":
                    return False, None, None
                return True, bug_type_str, self._get_severity(bug_type_str)

        # Use grade to determine
        if grade.bug_realism.score >= 0.75:
            bug_type = grade.bug_realism.details.get("bug_type", "Type-2")
            return True, bug_type, self._get_severity(bug_type)

        return False, None, None

    def _get_severity(self, bug_type: str) -> str:
        """Map bug type to severity."""
        severity_map = {
            "Type-1": "critical",  # Clear API violation
            "Type-2": "high",     # Semantic violation
            "Type-3": "medium",   # Environment-specific
            "Type-4": "low",       # False positive
        }
        return severity_map.get(bug_type, "medium")

    def get_calibration_status(self) -> Dict[str, Any]:
        """Get current calibration status."""
        if not self.is_calibrated:
            return {
                "is_calibrated": False,
                "message": "Evaluator not yet calibrated"
            }

        return {
            "is_calibrated": True,
            "rounds_completed": self.calibration_result.rounds_completed,
            "converged": self.calibration_result.converged,
            "final_precision": self.calibration_result.final_precision,
            "final_recall": self.calibration_result.final_recall,
            "final_f1": self.calibration_result.final_f1,
            "target_precision": self.calibration_result.target_precision,
            "target_recall": self.calibration_result.target_recall,
            "improvement": self.calibration_result.improvement,
        }

    def get_contract_status(self) -> Dict[str, Any]:
        """Get current Sprint contract status."""
        if not self.active_contract:
            return {
                "has_contract": False,
                "message": "No active Sprint contract"
            }

        return {
            "has_contract": True,
            "contract_id": self.active_contract.contract_id,
            "status": self.active_contract.status,
            "generator": self.active_contract.generator_agent,
            "evaluator": self.active_contract.evaluator_agent,
            "success_criteria": self.active_contract.success_criteria,
        }
