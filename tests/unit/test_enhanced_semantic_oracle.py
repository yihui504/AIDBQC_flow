"""
Unit Tests for Enhanced Semantic Oracle

Test coverage goals: 85%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.oracles.grading_criteria import (
    TestDiversityGrader,
    DefectNoveltyGrader,
    ContractAdherenceGrader,
    BugRealismGrader,
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
    ContractStatus,
    CriterionType,
)
from src.oracles.evaluator_calibration import (
    EvaluatorCalibrator,
    CalibrationSample,
    CalibrationLabel,
    CalibrationDataset,
)
from src.oracles.enhanced_semantic_oracle import (
    EnhancedSemanticOracle,
    OracleEvaluation,
    EvaluationResult,
)


# ============================================================================
# TestDiversityGrader Tests
# ============================================================================

class TestTestDiversityGrader:
    """Tests for TestDiversityGrader."""

    @pytest.fixture
    def grader(self):
        return TestDiversityGrader(min_similarity_threshold=0.7)

    def test_grade_with_no_history(self, grader):
        """Test grading when no history available."""
        test_case = {"case_id": "test-1", "vector": [0.1] * 128}

        result = asyncio.run(grader.grade(test_case, []))

        assert result.score == 1.0
        assert "no history" in result.reasoning.lower()

    def test_grade_diverse_test(self, grader):
        """Test grading a diverse test."""
        # Use orthogonal vectors (different dimensions)
        test_case = {"case_id": "test-1", "vector": [1.0, 0.0, 0.0] + [0.0] * 125}
        history = [[0.0, 1.0, 0.0] + [0.0] * 125]  # Orthogonal

        result = asyncio.run(grader.grade(test_case, history))

        assert result.score > 0.2  # Should be diverse

    def test_grade_similar_test(self, grader):
        """Test grading a test similar to history."""
        test_case = {"case_id": "test-1", "vector": [0.5] * 128}
        history = [[0.5] * 128, [0.51] * 128]  # Very similar

        result = asyncio.run(grader.grade(test_case, history))

        assert result.score < 0.5  # Should lack diversity

    def test_cosine_similarity_calculation(self, grader):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]

        sim_same = grader._cosine_similarity(vec1, vec2)
        sim_diff = grader._cosine_similarity(vec1, vec3)

        assert sim_same == pytest.approx(1.0)
        assert sim_diff == pytest.approx(0.0)


# ============================================================================
# DefectNoveltyGrader Tests
# ============================================================================

class TestDefectNoveltyGrader:
    """Tests for DefectNoveltyGrader."""

    @pytest.fixture
    def grader(self):
        return DefectNoveltyGrader(novelty_threshold=0.8)

    def test_grade_with_no_known_defects(self, grader):
        """Test grading when no known defects."""
        defect = {
            "bug_type": "Type-1",
            "root_cause_analysis": "Database returns wrong results"
        }

        result = asyncio.run(grader.grade(defect, []))

        assert result.score == 1.0
        assert "no known defects" in result.reasoning.lower()

    def test_grade_novel_defect(self, grader):
        """Test grading a novel defect."""
        defect = {
            "bug_type": "Type-1",
            "root_cause_analysis": "Unique issue with vector indexing"
        }
        known = [
            {"root_cause_analysis": "Connection timeout issue"}
        ]

        result = asyncio.run(grader.grade(defect, known))

        assert result.score > 0.5  # Should be novel

    def test_grade_duplicate_defect(self, grader):
        """Test grading a duplicate defect."""
        defect = {
            "bug_type": "Type-1",
            "root_cause_analysis": "Database returns wrong results for filter queries"
        }
        known = [
            {"root_cause_analysis": "Database returns wrong results for filter queries"}
        ]

        result = asyncio.run(grader.grade(defect, known))

        assert result.score < 0.5  # Should not be novel


# ============================================================================
# ContractAdherenceGrader Tests
# ============================================================================

class TestContractAdherenceGrader:
    """Tests for ContractAdherenceGrader."""

    @pytest.fixture
    def grader(self):
        return ContractAdherenceGrader()

    def test_grade_with_no_contracts(self, grader):
        """Test grading when no contracts defined."""
        test_case = {"case_id": "test-1", "dimension": 128}

        result = asyncio.run(grader.grade(test_case, {}))

        assert result.score == 1.0
        assert "no contracts" in result.reasoning.lower()

    def test_grade_passing_l1_contract(self, grader):
        """Test grading a test that passes L1 contract."""
        test_case = {"case_id": "test-1", "dimension": 128, "metric_type": "L2"}
        contracts = {
            "l1_api": {"max_dimension": 2048, "allowed_metrics": ["L2", "IP"]}
        }
        exec_result = {"l1_passed": True}

        result = asyncio.run(grader.grade(test_case, contracts, exec_result))

        assert result.score >= 0.95

    def test_grade_failing_l1_contract(self, grader):
        """Test grading a test that fails L1 contract."""
        test_case = {"case_id": "test-1", "dimension": 4096}  # Too large
        contracts = {
            "l1_api": {"max_dimension": 2048}
        }

        result = asyncio.run(grader.grade(test_case, contracts))

        assert result.score < 1.0
        assert "Dimension" in result.details["violations"][0]


# ============================================================================
# BugRealismGrader Tests
# ============================================================================

class TestBugRealismGrader:
    """Tests for BugRealismGrader."""

    @pytest.fixture
    def grader(self):
        return BugRealismGrader()

    def test_grade_type_1_bug(self, grader):
        """Test grading a Type-1 bug (most realistic)."""
        defect = {
            "bug_type": "Type-1",
            "root_cause_analysis": "Clear API violation: dimension parameter accepts negative value causing index out of bounds",
            "evidence_level": "L1"
        }

        result = asyncio.run(grader.grade(defect))

        assert result.score >= 0.90
        assert result.details["bug_type"] == "Type-1"

    def test_grade_type_2_bug(self, grader):
        """Test grading a Type-2 bug."""
        defect = {
            "bug_type": "Type-2",
            "root_cause_analysis": "Semantic drift in search results",
            "evidence_level": "L2"
        }

        result = asyncio.run(grader.grade(defect))

        assert result.score >= 0.70

    def test_grade_type_4_bug(self, grader):
        """Test grading a Type-4 bug (false positive)."""
        defect = {
            "bug_type": "Type-4",
            "root_cause_analysis": "Expected behavior, not a bug",
            "evidence_level": "L1"
        }

        result = asyncio.run(grader.grade(defect))

        assert result.score <= 0.40

    def test_grade_with_brief_analysis(self, grader):
        """Test grading with too brief analysis."""
        defect = {
            "bug_type": "Type-1",
            "root_cause_analysis": "Bug",  # Too brief
        }

        result = asyncio.run(grader.grade(defect))

        assert result.score < 0.95  # Should be penalized


# ============================================================================
# GradingCriteria Tests
# ============================================================================

class TestGradingCriteria:
    """Tests for GradingCriteria orchestrator."""

    @pytest.fixture
    def criteria(self):
        return GradingCriteria()

    @pytest.fixture
    def sample_test_case(self):
        return {
            "case_id": "test-001",
            "dimension": 128,
            "metric_type": "L2",
            "vector": [0.5] * 128,
        }

    def test_grade_complete_test_case(self, criteria, sample_test_case):
        """Test grading a complete test case with defect."""
        defect_report = {
            "bug_type": "Type-1",
            "root_cause_analysis": "API violation in insert operation",
            "evidence_level": "L1"
        }
        contracts = {
            "l1_api": {"max_dimension": 2048, "allowed_metrics": ["L2"]}
        }

        result = asyncio.run(criteria.grade_test_case(
            test_case=sample_test_case,
            history_vectors=[[0.1] * 128],
            contracts=contracts,
            defect_report=defect_report,
            known_defects=[],
        ))

        assert isinstance(result, OverallGrade)
        assert result.test_case_id == "test-001"
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0

    def test_grade_test_case_without_defect(self, criteria, sample_test_case):
        """Test grading a test case with no defect."""
        contracts = {
            "l1_api": {"max_dimension": 2048, "allowed_metrics": ["L2"]}
        }

        result = asyncio.run(criteria.grade_test_case(
            test_case=sample_test_case,
            history_vectors=[[0.1] * 128],
            contracts=contracts,
        ))

        # Should have default grades when no defect
        assert result.defect_novelty.score == 1.0
        assert result.bug_realism.score == 1.0
        assert result.bug_type is None

    def test_recommendations_for_poor_diversity(self, criteria, sample_test_case):
        """Test recommendations when test lacks diversity."""
        contracts = {"l1_api": {"max_dimension": 2048}}

        result = asyncio.run(criteria.grade_test_case(
            test_case=sample_test_case,
            history_vectors=[[0.5] * 128] * 10,  # Very similar
            contracts=contracts,
        ))

        assert any("diversity" in r.lower() for r in result.recommendations)


# ============================================================================
# SprintContract Tests
# ============================================================================

class TestSprintContract:
    """Tests for SprintContract."""

    def test_contract_creation(self):
        """Test creating a Sprint contract."""
        contract = SprintContract(
            contract_id="contract-001",
            status=ContractStatus.ACCEPTED,
            generator_agent="agent2",
            evaluator_agent="agent4",
        )

        assert contract.contract_id == "contract-001"
        assert contract.status == ContractStatus.ACCEPTED

    def test_contract_with_success_criteria(self):
        """Test contract with success criteria."""
        criteria = [
            {
                "criterion_type": "test_diversity",
                "threshold": 0.7,
                "weight": 1.0,
            }
        ]

        contract = SprintContract(
            contract_id="contract-001",
            success_criteria=criteria,
        )

        assert len(contract.success_criteria) == 1


class TestSprintContractManager:
    """Tests for SprintContractManager."""

    @pytest.fixture
    def manager(self):
        return SprintContractManager()

    def test_create_initial_proposal(self, manager):
        """Test creating initial contract proposal."""
        proposal = manager.create_initial_proposal(
            generator_id="agent2",
            evaluator_id="agent4",
            test_scope={"dimension": 128, "count": 10},
        )

        assert proposal.proposer == "agent2"
        assert proposal.counterparty == "agent4"
        assert len(proposal.success_criteria) > 0
        assert len(proposal.verification_methods) > 0

    @pytest.mark.asyncio
    async def test_negotiate_contract_accepted(self, manager):
        """Test negotiation when evaluator accepts."""

        async def accept_proposal(proposal):
            # Evaluator accepts with minor change
            return ContractProposal(
                proposal_id=proposal.proposal_id + "_resp",
                proposer=proposal.counterparty,
                counterparty=proposal.proposer,
                test_scope=proposal.test_scope.copy(),
                success_criteria=proposal.success_criteria.copy(),
                verification_methods=proposal.verification_methods.copy(),
                oracle_constraints=proposal.oracle_constraints.copy(),
                message="I accept these terms",
            )

        initial = manager.create_initial_proposal(
            generator_id="agent2",
            evaluator_id="agent4",
            test_scope={"dimension": 128},
        )

        contract = await manager.negotiate_contract(initial, accept_proposal)

        assert contract.status == ContractStatus.ACCEPTED
        assert contract.generator_agent == "agent2"

    @pytest.mark.asyncio
    async def test_negotiate_contract_with_counter_proposal(self, manager):
        """Test negotiation with counter-proposal."""

        async def evaluator_response(proposal):
            # Evaluator requests higher threshold
            new_criteria = [
                SuccessCriterion(
                    criterion_type=CriterionType.TEST_DIVERSITY,
                    threshold=0.8,  # Increased from 0.7
                    weight=1.0,
                )
            ]
            return ContractProposal(
                proposal_id=proposal.proposal_id + "_eval",
                proposer=proposal.counterparty,
                counterparty=proposal.proposer,
                test_scope=proposal.test_scope.copy(),
                success_criteria=new_criteria,
                verification_methods=proposal.verification_methods.copy(),
                oracle_constraints=proposal.oracle_constraints.copy(),
                message="Please increase diversity threshold to 0.8",
            )

        async def generator_response(proposal):
            # Generator accepts
            proposal.message = "I accept your changes"
            return proposal

        initial = manager.create_initial_proposal(
            generator_id="agent2",
            evaluator_id="agent4",
            test_scope={"dimension": 128},
        )

        contract = await manager.negotiate_contract(
            initial,
            evaluator_response,
            generator_response
        )

        assert contract.status == ContractStatus.ACCEPTED
        # Check that threshold was increased
        diversity_criterion = next(
            (c for c in contract.success_criteria if c["criterion_type"] == "test_diversity"),
            None
        )
        assert diversity_criterion is not None
        assert diversity_criterion["threshold"] == 0.8


# ============================================================================
# EvaluatorCalibrator Tests
# ============================================================================

class TestCalibrationDataset:
    """Tests for CalibrationDataset."""

    @pytest.fixture
    def dataset(self):
        return CalibrationDataset()

    def test_add_sample(self, dataset):
        """Test adding a calibration sample."""
        sample = CalibrationSample(
            sample_id="sample-001",
            test_case={"dimension": 128},
            execution_result={"success": True},
            ground_truth=CalibrationLabel.IS_BUG,
            human_confidence=0.95,
        )

        dataset.add_sample(sample)

        assert dataset.total_samples == 1
        assert "is_bug" in dataset.bug_distribution

    def test_get_samples_by_label(self, dataset):
        """Test filtering samples by label."""
        sample1 = CalibrationSample(
            sample_id="sample-001",
            test_case={},
            execution_result={},
            ground_truth=CalibrationLabel.IS_BUG,
            human_confidence=0.9,
        )
        sample2 = CalibrationSample(
            sample_id="sample-002",
            test_case={},
            execution_result={},
            ground_truth=CalibrationLabel.NOT_BUG,
            human_confidence=0.9,
        )

        dataset.add_sample(sample1)
        dataset.add_sample(sample2)

        bug_samples = dataset.get_samples_by_label(CalibrationLabel.IS_BUG)
        assert len(bug_samples) == 1


class TestEvaluatorCalibrator:
    """Tests for EvaluatorCalibrator."""

    @pytest.fixture
    def calibrator(self):
        return EvaluatorCalibrator(max_rounds=3)

    def test_initialization(self, calibrator):
        """Test calibrator initialization."""
        assert calibrator.target_precision == 0.90
        assert calibrator.target_recall == 0.85
        assert calibrator.max_rounds == 3

    def test_default_prompt_template(self, calibrator):
        """Test default prompt template."""
        prompt = calibrator.current_prompt

        assert "test_case" in prompt.lower()
        assert "execution_result" in prompt.lower()
        assert "json" in prompt.lower()

    @pytest.mark.asyncio
    async def test_run_calibration_round_with_empty_dataset(self, calibrator):
        """Test calibration round with no samples."""
        # Mock LLM client
        class MockLLM:
            async def generate(self, prompt):
                return '{"is_bug": false, "confidence": 0.5}'

        llm = MockLLM()

        # Should handle empty dataset gracefully
        round_result = await calibrator.run_calibration_round(1, llm)

        assert round_result.samples_evaluated == 0


# ============================================================================
# EnhancedSemanticOracle Tests
# ============================================================================

class TestEnhancedSemanticOracle:
    """Tests for EnhancedSemanticOracle."""

    @pytest.fixture
    def oracle(self):
        return EnhancedSemanticOracle(
            enable_calibration=False,
            enable_contracts=False
        )

    def test_initialization(self, oracle):
        """Test oracle initialization."""
        assert oracle.grading_criteria is not None
        assert oracle.contract_manager is not None
        assert oracle.calibrator is not None

    @pytest.mark.asyncio
    async def test_evaluate_test_case(self, oracle):
        """Test evaluating a single test case."""
        test_case = {
            "case_id": "test-001",
            "dimension": 128,
            "metric_type": "L2",
        }
        contracts = {"l1_api": {"max_dimension": 2048}}

        evaluation = await oracle.evaluate_test_case(
            test_case=test_case,
            history_vectors=[[0.1] * 128],
            contracts=contracts,
        )

        assert evaluation.test_case_id == "test-001"
        assert isinstance(evaluation.passed, bool)
        assert 0.0 <= evaluation.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_batch(self, oracle):
        """Test evaluating a batch of test cases."""
        test_cases = [
            {"case_id": "test-001", "dimension": 128},
            {"case_id": "test-002", "dimension": 256},
        ]
        contracts = {"l1_api": {"max_dimension": 2048}}

        result = await oracle.evaluate_batch(
            test_cases=test_cases,
            history_vectors=[[0.1] * 128],
            contracts=contracts,
        )

        assert len(result.evaluations) == 2
        assert result.total_tests == 2
        assert 0.0 <= result.average_diversity <= 1.0

    def test_get_calibration_status_when_uncalibrated(self, oracle):
        """Test calibration status before calibration."""
        status = oracle.get_calibration_status()

        assert status["is_calibrated"] is False

    def test_get_contract_status_when_no_contract(self, oracle):
        """Test contract status when no active contract."""
        status = oracle.get_contract_status()

        assert status["has_contract"] is False


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
