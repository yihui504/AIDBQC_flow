"""
Grading Criteria for AI-DB-QC Test Evaluation

Implements Anthropic-style grading criteria for test quality assessment:
- Test Diversity: Semantic diversity of generated tests
- Defect Novelty: Novelty of discovered defects
- Contract Adherence: Compliance with L1/L2/L3 contracts
- Bug Realism: Realism of potential bugs (Type-1/2/3/4)

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

import numpy as np


class BugType(str, Enum):
    """Classification of bug types."""

    TYPE_1 = "Type-1"  # L1 API contract violation (clear, reproducible)
    TYPE_2 = "Type-2"  # L2 Semantic contract violation (requires interpretation)
    TYPE_3 = "Type-3"  # Real bug that requires environmental understanding
    TYPE_4 = "Type-4"  # False positive / not a real bug


@dataclass
class Grade:
    """Individual grade for a criterion."""

    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "details": self.details,
        }


@dataclass
class OverallGrade:
    """Overall grade for a test case or batch."""

    test_case_id: str
    test_diversity: Grade
    defect_novelty: Grade
    contract_adherence: Grade
    bug_realism: Grade

    # Weighted components
    overall_score: float  # Weighted average
    passed_threshold: bool

    # Detailed breakdown
    bug_type: Optional[BugType] = None
    recommendations: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted overall score."""
        weights = {
            "test_diversity": 0.20,
            "defect_novelty": 0.25,
            "contract_adherence": 0.30,
            "bug_realism": 0.25,
        }

        return (
            self.test_diversity.score * weights["test_diversity"]
            + self.defect_novelty.score * weights["defect_novelty"]
            + self.contract_adherence.score * weights["contract_adherence"]
            + self.bug_realism.score * weights["bug_realism"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_case_id": self.test_case_id,
            "overall_score": self.overall_score,
            "weighted_score": self.weighted_score,
            "passed_threshold": self.passed_threshold,
            "bug_type": self.bug_type.value if self.bug_type else None,
            "recommendations": self.recommendations,
            "grades": {
                "test_diversity": self.test_diversity.to_dict(),
                "defect_novelty": self.defect_novelty.to_dict(),
                "contract_adherence": self.contract_adherence.to_dict(),
                "bug_realism": self.bug_realism.to_dict(),
            },
        }


class TestDiversityGrader:
    """
    Grades the semantic diversity of generated tests.

    Measures how diverse a test is compared to existing tests using
    cosine similarity of test representations.
    """

    def __init__(
        self,
        min_similarity_threshold: float = 0.7,
        confidence_threshold: float = 0.8
    ):
        self.min_similarity_threshold = min_similarity_threshold
        self.confidence_threshold = confidence_threshold

    async def grade(
        self,
        test_case: Dict[str, Any],
        history_vectors: List[List[float]],
        llm_client: Optional[Any] = None
    ) -> Grade:
        """
        Grade test diversity.

        Args:
            test_case: The test case to grade
            history_vectors: Vector representations of previous tests
            llm_client: Optional LLM for semantic analysis

        Returns:
            Grade with score (higher = more diverse)
        """
        # Get test vector (simplified - in production would use actual embedding)
        test_vector = test_case.get("vector", [])

        if not test_vector or not history_vectors:
            # No history means maximum diversity by default
            return Grade(
                score=1.0,
                confidence=0.5,
                reasoning="No history to compare, assuming maximum diversity",
                details={"method": "no_history_default"}
            )

        # Calculate cosine similarity with history
        similarities = []
        for hist_vec in history_vectors:
            if len(hist_vec) == len(test_vector):
                sim = self._cosine_similarity(test_vector, hist_vec)
                similarities.append(sim)

        if not similarities:
            return Grade(
                score=1.0,
                confidence=0.5,
                reasoning="No compatible history vectors",
                details={"method": "no_compatible_vectors"}
            )

        # Diversity = 1 - max_similarity (lower similarity = higher diversity)
        max_similarity = max(similarities)
        diversity_score = max(0.0, 1.0 - max_similarity)

        # Adjust score based on threshold
        if max_similarity < self.min_similarity_threshold:
            # Test is sufficiently diverse
            adjusted_score = diversity_score
            confidence = self.confidence_threshold
            reasoning = f"Test is diverse (max similarity: {max_similarity:.2f} < threshold: {self.min_similarity_threshold})"
        else:
            # Test is too similar to existing tests
            adjusted_score = diversity_score * 0.5  # Penalize
            confidence = self.confidence_threshold
            reasoning = f"Test lacks diversity (max similarity: {max_similarity:.2f} >= threshold: {self.min_similarity_threshold})"

        return Grade(
            score=adjusted_score,
            confidence=confidence,
            reasoning=reasoning,
            details={
                "method": "cosine_similarity",
                "max_similarity": max_similarity,
                "avg_similarity": sum(similarities) / len(similarities),
                "history_size": len(history_vectors),
            }
        )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)

        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class DefectNoveltyGrader:
    """
    Grades the novelty of discovered defects.

    Determines if a defect is novel compared to known issues.
    """

    def __init__(
        self,
        novelty_threshold: float = 0.8,
        confidence_threshold: float = 0.75
    ):
        self.novelty_threshold = novelty_threshold
        self.confidence_threshold = confidence_threshold

    async def grade(
        self,
        defect_report: Dict[str, Any],
        known_defects: List[Dict[str, Any]],
        llm_client: Optional[Any] = None
    ) -> Grade:
        """
        Grade defect novelty.

        Args:
            defect_report: The defect report to evaluate
            known_defects: List of known defects for comparison
            llm_client: Optional LLM for semantic similarity

        Returns:
            Grade with score (higher = more novel)
        """
        defect_description = defect_report.get("root_cause_analysis", "")
        defect_type = defect_report.get("bug_type", "")

        if not defect_description:
            return Grade(
                score=0.0,
                confidence=0.3,
                reasoning="No defect description provided",
            )

        if not known_defects:
            return Grade(
                score=1.0,
                confidence=0.5,
                reasoning="No known defects to compare, assuming novelty",
            )

        # Calculate semantic similarity with known defects
        max_similarity = 0.0
        for known in known_defects:
            known_desc = known.get("root_cause_analysis", "")
            similarity = self._text_similarity(defect_description, known_desc)
            max_similarity = max(max_similarity, similarity)

        # Novelty = 1 - similarity
        novelty_score = max(0.0, 1.0 - max_similarity)

        if max_similarity < self.novelty_threshold:
            confidence = self.confidence_threshold
            reasoning = f"Defect is novel (max similarity: {max_similarity:.2f} < threshold: {self.novelty_threshold})"
        else:
            confidence = self.confidence_threshold
            reasoning = f"Defect may duplicate known issue (similarity: {max_similarity:.2f} >= threshold: {self.novelty_threshold})"

        return Grade(
            score=novelty_score,
            confidence=confidence,
            reasoning=reasoning,
            details={
                "method": "text_similarity",
                "max_similarity": max_similarity,
                "known_defects_count": len(known_defects),
                "defect_type": defect_type,
            }
        )

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (Jaccard on words)."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0


class ContractAdherenceGrader:
    """
    Grades adherence to L1/L2/L3 contracts.

    Validates that tests follow defined contract constraints.
    """

    def __init__(self, confidence_threshold: float = 0.95):
        self.confidence_threshold = confidence_threshold

    async def grade(
        self,
        test_case: Dict[str, Any],
        contracts: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None
    ) -> Grade:
        """
        Grade contract adherence.

        Args:
            test_case: The test case to validate
            contracts: Parsed L1/L2/L3 contracts
            execution_result: Optional execution result for L1 validation

        Returns:
            Grade with score (higher = better adherence)
        """
        violations = []
        total_checks = 0
        passed_checks = 0

        # L1 Contract: API constraints
        if contracts.get("l1_api"):
            total_checks += 1
            l1_result = self._check_l1_contract(test_case, contracts["l1_api"], execution_result)
            if l1_result["passed"]:
                passed_checks += 1
            else:
                violations.append(l1_result["violation"])

        # L2 Contract: Semantic constraints
        if contracts.get("l2_semantic"):
            total_checks += 1
            l2_result = self._check_l2_contract(test_case, contracts["l2_semantic"])
            if l2_result["passed"]:
                passed_checks += 1
            else:
                violations.append(l2_result["violation"])

        # L3 Contract: Application constraints
        if contracts.get("l3_application"):
            total_checks += 1
            l3_result = self._check_l3_contract(test_case, contracts["l3_application"])
            if l3_result["passed"]:
                passed_checks += 1
            else:
                violations.append(l3_result["violation"])

        if total_checks == 0:
            return Grade(
                score=1.0,
                confidence=0.3,
                reasoning="No contracts defined for validation",
            )

        adherence_score = passed_checks / total_checks
        passed = adherence_score >= 0.95  # Allow minor issues

        return Grade(
            score=adherence_score,
            confidence=self.confidence_threshold,
            reasoning=f"Contract adherence: {passed_checks}/{total_checks} checks passed",
            details={
                "violations": violations,
                "checks_passed": passed_checks,
                "total_checks": total_checks,
            }
        )

    def _check_l1_contract(
        self,
        test_case: Dict[str, Any],
        l1_contract: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check L1 API contract compliance."""
        # Dimension check
        dimension = test_case.get("dimension", 0)
        max_dim = l1_contract.get("max_dimension", 2048)

        if dimension > max_dim:
            return {
                "passed": False,
                "violation": f"Dimension {dimension} exceeds max {max_dim}"
            }

        # Metric type check
        allowed_metrics = l1_contract.get("allowed_metrics", ["L2"])
        metric = test_case.get("metric_type", "L2")

        if metric not in allowed_metrics:
            return {
                "passed": False,
                "violation": f"Metric {metric} not in allowed {allowed_metrics}"
            }

        # If execution result provided, check L1 pass
        if execution_result:
            if not execution_result.get("l1_passed", True):
                return {
                    "passed": False,
                    "violation": "L1 API check failed"
                }

        return {"passed": True}

    def _check_l2_contract(
        self,
        test_case: Dict[str, Any],
        l2_contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check L2 semantic contract compliance."""
        # Semantic intent should be meaningful
        intent = test_case.get("semantic_intent", "")

        if len(intent) < 10:
            return {
                "passed": False,
                "violation": "Semantic intent too brief"
            }

        # Should not be adversarial if contract forbids it
        if not l2_contract.get("allow_adversarial", True):
            if test_case.get("is_adversarial", False):
                return {
                    "passed": False,
                    "violation": "Adversarial test not allowed by contract"
                }

        return {"passed": True}

    def _check_l3_contract(
        self,
        test_case: Dict[str, Any],
        l3_contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check L3 application contract compliance."""
        # Check for required fields
        required_fields = l3_contract.get("required_fields", [])

        for field in required_fields:
            if field not in test_case or not test_case[field]:
                return {
                    "passed": False,
                    "violation": f"Required field '{field}' missing"
                }

        return {"passed": True}


class BugRealismGrader:
    """
    Grades the realism of potential bugs.

    Determines if a reported issue is likely to be a real bug (Type-1/2/3/4).
    """

    def __init__(
        self,
        realism_threshold: float = 0.75,
        confidence_threshold: float = 0.7
    ):
        self.realism_threshold = realism_threshold
        self.confidence_threshold = confidence_threshold

        # Realism indicators by bug type
        self.type_indicators = {
            BugType.TYPE_1: {
                "reproducible": True,
                "clear_violation": True,
                "minimal_example": True,
            },
            BugType.TYPE_2: {
                "semantic_drift": True,
                "interpretation_required": True,
            },
            BugType.TYPE_3: {
                "environment_specific": True,
                "edge_case": True,
            },
            BugType.TYPE_4: {
                "false_positive": True,
                "expected_behavior": True,
            },
        }

    async def grade(
        self,
        defect_report: Dict[str, Any],
        llm_client: Optional[Any] = None
    ) -> Grade:
        """
        Grade bug realism.

        Args:
            defect_report: The defect report to evaluate
            llm_client: Optional LLM for enhanced analysis

        Returns:
            Grade with score and bug type classification
        """
        bug_type_str = defect_report.get("bug_type", "Type-2")
        root_cause = defect_report.get("root_cause_analysis", "")
        evidence_level = defect_report.get("evidence_level", "L2")

        # Convert string to enum
        try:
            bug_type = BugType(bug_type_str)
        except ValueError:
            bug_type = BugType.TYPE_2

        # Base realism score by type
        type_realism = {
            BugType.TYPE_1: 0.95,  # Most realistic
            BugType.TYPE_2: 0.80,  # Very realistic
            BugType.TYPE_3: 0.70,  # Moderately realistic
            BugType.TYPE_4: 0.20,  # Less realistic (likely FP)
        }

        base_score = type_realism.get(bug_type, 0.70)

        # Adjust based on quality of evidence
        evidence_bonus = {
            "L1": 0.05,
            "L2": 0.00,
            "L3": -0.05,
        }
        score = base_score + evidence_bonus.get(evidence_level, 0.0)

        # Adjust based on analysis quality
        if len(root_cause) > 100:
            score += 0.05  # Detailed analysis
        elif len(root_cause) < 20:
            score -= 0.10  # Too brief

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        # Determine confidence
        confidence = self.confidence_threshold
        if bug_type in [BugType.TYPE_1, BugType.TYPE_2]:
            confidence = min(1.0, confidence + 0.15)

        reasoning = f"Bug classified as {bug_type.value} with {evidence_level} evidence"

        return Grade(
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            details={
                "bug_type": bug_type.value,
                "evidence_level": evidence_level,
                "analysis_length": len(root_cause),
            }
        )


class GradingCriteria:
    """
    Main grading criteria orchestrator.

    Combines all individual graders to produce an overall grade.
    """

    def __init__(
        self,
        diversity_threshold: float = 0.7,
        novelty_threshold: float = 0.8,
        realism_threshold: float = 0.75,
        overall_threshold: float = 0.70
    ):
        self.diversity_grader = TestDiversityGrader(min_similarity_threshold=diversity_threshold)
        self.novelty_grader = DefectNoveltyGrader(novelty_threshold=novelty_threshold)
        self.adherence_grader = ContractAdherenceGrader()
        self.realism_grader = BugRealismGrader(realism_threshold=realism_threshold)
        self.overall_threshold = overall_threshold

    async def grade_test_case(
        self,
        test_case: Dict[str, Any],
        history_vectors: List[List[float]],
        contracts: Dict[str, Any],
        defect_report: Optional[Dict[str, Any]] = None,
        known_defects: Optional[List[Dict[str, Any]]] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
    ) -> OverallGrade:
        """
        Grade a test case across all criteria.

        Args:
            test_case: The test case to grade
            history_vectors: Historical test vectors for diversity
            contracts: Contract constraints
            defect_report: Optional defect report for novelty/realism
            known_defects: Known defects for novelty comparison
            execution_result: Optional execution result
            llm_client: Optional LLM for enhanced grading

        Returns:
            OverallGrade with all component grades
        """
        # Grade each component
        diversity_grade = await self.diversity_grader.grade(test_case, history_vectors, llm_client)
        adherence_grade = await self.adherence_grader.grade(test_case, contracts, execution_result)

        # Novelty and realism only apply if there's a defect
        if defect_report:
            novelty_grade = await self.novelty_grader.grade(
                defect_report,
                known_defects or [],
                llm_client
            )
            realism_grade = await self.realism_grader.grade(defect_report, llm_client)

            # Determine bug type from realism grader
            bug_type = BugType(realism_grade.details.get("bug_type", "Type-2"))
        else:
            # Default grades when no defect
            novelty_grade = Grade(score=1.0, confidence=0.5, reasoning="No defect to evaluate")
            realism_grade = Grade(score=1.0, confidence=0.5, reasoning="No defect to evaluate")
            bug_type = None

        # Calculate overall score
        overall = OverallGrade(
            test_case_id=test_case.get("case_id", "unknown"),
            test_diversity=diversity_grade,
            defect_novelty=novelty_grade,
            contract_adherence=adherence_grade,
            bug_realism=realism_grade,
            overall_score=0.0,  # Will be calculated by property
            passed_threshold=False,  # Will be calculated
            bug_type=bug_type,
        )

        overall.overall_score = overall.weighted_score
        overall.passed_threshold = overall.overall_score >= self.overall_threshold

        # Generate recommendations
        overall.recommendations = self._generate_recommendations(overall)

        return overall

    def _generate_recommendations(self, grade: OverallGrade) -> List[str]:
        """Generate improvement recommendations based on grades."""
        recommendations = []

        if grade.test_diversity.score < 0.7:
            recommendations.append(
                f"Test lacks diversity (similarity: {1.0 - grade.test_diversity.score:.2f}). "
                "Consider exploring different query patterns or parameters."
            )

        if grade.defect_novelty.score < 0.8:
            recommendations.append(
                f"Defect may duplicate known issues (novelty: {grade.defect_novelty.score:.2f}). "
                "Verify against existing bug reports."
            )

        if grade.contract_adherence.score < 0.95:
            recommendations.append(
                f"Contract violations detected (adherence: {grade.contract_adherence.score:.2f}). "
                "Review L1/L2/L3 contract constraints."
            )

        if grade.bug_realism.score < 0.75:
            recommendations.append(
                f"Bug realism low (score: {grade.bug_realism.score:.2f}). "
                "Provide more detailed analysis or minimal reproducible example."
            )

        if not recommendations:
            recommendations.append("Test case meets all quality criteria.")

        return recommendations
