"""
Unit Tests for Enhanced Test Generator

Test coverage goals: 85%+

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.agents.enhanced_test_generator import (
    EnhancedTestGenerator,
    GenerationRequest,
    GenerationResult,
    SelfEvaluation,
    GenerationMode,
    TestGeneratorStrategy,
    StandardGenerationStrategy,
    BoundaryStrategy,
    AdversarialStrategy,
)
from src.oracles.sprint_contract import (
    SprintContract,
    SprintContractManager,
    ContractProposal,
    SuccessCriterion,
    ContractStatus,
    CriterionType,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_contracts():
    """Sample contracts for testing."""
    return {
        "l1_api": {
            "max_dimension": 2048,
            "allowed_metrics": ["L2", "IP", "COSINE"]
        },
        "l2_semantic": {
            "min_recall": 0.8,
            "max_top_k": 100
        }
    }


@pytest.fixture
def sample_request(sample_contracts):
    """Sample generation request."""
    return GenerationRequest(
        request_id="test-request-001",
        mode=GenerationMode.STANDARD,
        target_db="milvus",
        contracts=sample_contracts,
        num_tests=5,
        diversity_threshold=0.7,
        target_dimensions=[128, 256, 512],
    )


@pytest.fixture
def generator():
    """Create test generator instance."""
    return EnhancedTestGenerator()


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = Mock()
    llm.generate = AsyncMock(return_value="Generated test response")
    return llm


# ============================================================================
# GenerationRequest Tests
# ============================================================================

class TestGenerationRequest:
    """Tests for GenerationRequest."""

    def test_request_creation(self, sample_contracts):
        """Test creating a generation request."""
        request = GenerationRequest(
            request_id="req-001",
            mode=GenerationMode.BOUNDARY,
            target_db="qdrant",
            contracts=sample_contracts,
            num_tests=10,
        )

        assert request.request_id == "req-001"
        assert request.mode == GenerationMode.BOUNDARY
        assert request.target_db == "qdrant"
        assert request.num_tests == 10
        assert request.sprint_contract is None

    def test_request_with_contract(self, sample_contracts):
        """Test request with attached Sprint contract."""
        contract = SprintContract(
            contract_id="contract-001",
            status=ContractStatus.ACCEPTED,
        )

        request = GenerationRequest(
            request_id="req-001",
            mode=GenerationMode.STANDARD,
            target_db="milvus",
            contracts=sample_contracts,
            sprint_contract=contract,
        )

        assert request.sprint_contract == contract


# ============================================================================
# StandardGenerationStrategy Tests
# ============================================================================

class TestStandardGenerationStrategy:
    """Tests for StandardGenerationStrategy."""

    @pytest.fixture
    def strategy(self):
        return StandardGenerationStrategy()

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        llm = Mock()
        llm.generate = AsyncMock(return_value="Generated test response")
        return llm

    @pytest.mark.asyncio
    async def test_generate_standard_tests(self, strategy, sample_request, mock_llm):
        """Test generating standard diverse tests."""
        tests = await strategy.generate(sample_request, mock_llm)

        assert len(tests) > 0
        for test in tests:
            assert "case_id" in test
            assert "dimension" in test
            assert "metric_type" in test
            assert test["is_adversarial"] is False
            assert test["expected_l1_legal"] is True

    def test_get_target_dimensions_from_request(self, strategy, sample_request):
        """Test getting target dimensions from request."""
        dims = strategy._get_target_dimensions(sample_request)

        assert 128 in dims
        assert 256 in dims
        assert 512 in dims

    def test_get_target_dimensions_default(self, strategy):
        """Test getting default target dimensions."""
        request = GenerationRequest(
            request_id="req-001",
            mode=GenerationMode.STANDARD,
            target_db="milvus",
            contracts={"l1_api": {"max_dimension": 512}},
        )

        dims = strategy._get_target_dimensions(request)

        assert 64 in dims
        assert 128 in dims
        assert 256 in dims
        assert 512 in dims
        assert 1024 not in dims  # Over max_dimension

    def test_generate_query_text(self, strategy):
        """Test query text generation."""
        text = strategy._generate_query_text(128, "L2")

        assert "128" in text
        assert "L2" in text


# ============================================================================
# BoundaryStrategy Tests
# ============================================================================

class TestBoundaryStrategy:
    """Tests for BoundaryStrategy."""

    @pytest.fixture
    def strategy(self):
        return BoundaryStrategy()

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        llm = Mock()
        llm.generate = AsyncMock(return_value="Generated test response")
        return llm

    @pytest.mark.asyncio
    async def test_generate_boundary_tests(self, strategy, sample_request, mock_llm):
        """Test generating boundary value tests."""
        tests = await strategy.generate(sample_request, mock_llm)

        assert len(tests) > 0

        # Check for minimum dimension
        min_dim_test = next((t for t in tests if t["dimension"] == 1), None)
        assert min_dim_test is not None

        # Check for maximum dimension
        max_dim_test = next((t for t in tests if t["dimension"] == 2048), None)
        assert max_dim_test is not None

    @pytest.mark.asyncio
    async def test_boundary_test_over_max(self, strategy, sample_request, mock_llm):
        """Test boundary test over maximum dimension."""
        tests = await strategy.generate(sample_request, mock_llm)

        # Should have test over max dimension
        over_max = next((t for t in tests if t["dimension"] > 2048), None)
        assert over_max is not None
        assert over_max["expected_l1_legal"] is False
        assert over_max["is_adversarial"] is True


# ============================================================================
# AdversarialStrategy Tests
# ============================================================================

class TestAdversarialStrategy:
    """Tests for AdversarialStrategy."""

    @pytest.fixture
    def strategy(self):
        return AdversarialStrategy()

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        llm = Mock()
        llm.generate = AsyncMock(return_value="Generated test response")
        return llm

    @pytest.mark.asyncio
    async def test_generate_adversarial_tests(self, strategy, sample_request, mock_llm):
        """Test generating adversarial tests."""
        tests = await strategy.generate(sample_request, mock_llm)

        assert len(tests) > 0

        for test in tests:
            assert test["is_adversarial"] is True
            assert test["expected_l1_legal"] is False
            assert "adversarial_type" in test

    @pytest.mark.asyncio
    async def test_adversarial_pattern_coverage(self, strategy, sample_request, mock_llm):
        """Test coverage of adversarial patterns."""
        tests = await strategy.generate(sample_request, mock_llm)

        adversarial_types = [t.get("adversarial_type") for t in tests]

        # Check for common patterns
        expected_patterns = [
            "negative_dimension",
            "zero_vector",
            "infinite_values",
            "extreme_values"
        ]

        for pattern in expected_patterns:
            assert any(pattern in str(t) for t in adversarial_types)


# ============================================================================
# EnhancedTestGenerator Tests
# ============================================================================

class TestEnhancedTestGenerator:
    """Tests for EnhancedTestGenerator."""

    @pytest.fixture
    def generator(self):
        return EnhancedTestGenerator()

    @pytest.fixture
    def sample_contracts(self):
        return {
            "l1_api": {"max_dimension": 2048, "allowed_metrics": ["L2"]},
            "l2_semantic": {"min_recall": 0.8}
        }

    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator.contract_manager is not None
        assert generator.grading_criteria is not None
        assert len(generator.strategies) == 3
        assert GenerationMode.STANDARD in generator.strategies
        assert GenerationMode.BOUNDARY in generator.strategies
        assert GenerationMode.ADVERSARIAL in generator.strategies

    def test_statistics(self, generator):
        """Test generation statistics."""
        stats = generator.get_statistics()

        assert "total_generations" in stats
        assert "contracts_negotiated" in stats
        assert "available_strategies" in stats

    @pytest.mark.asyncio
    async def test_negotiate_contract_accepted(self, generator, sample_request):
        """Test contract negotiation when evaluator accepts."""

        async def accept_proposal(proposal):
            # Evaluator accepts
            proposal.message = "I accept these terms"
            return proposal

        contract = await generator.negotiate_contract(
            sample_request,
            accept_proposal,
        )

        assert contract.status == ContractStatus.ACCEPTED
        assert sample_request.sprint_contract == contract
        assert generator.contracts_negotiated == 1

    @pytest.mark.asyncio
    async def test_negotiate_contract_with_changes(self, generator, sample_request):
        """Test contract negotiation with counter-proposal."""

        async def evaluator_response(proposal):
            # Evaluator requests higher threshold
            new_criteria = [
                SuccessCriterion(
                    criterion_type=CriterionType.TEST_DIVERSITY,
                    threshold=0.85,  # Increased from 0.7
                    weight=1.0,
                )
            ]
            proposal.success_criteria = new_criteria
            proposal.message = "Please increase diversity threshold"
            return proposal

        async def generator_response(proposal):
            # Generator accepts
            proposal.message = "I accept your changes"
            return proposal

        contract = await generator.negotiate_contract(
            sample_request,
            evaluator_response,
            generator_response
        )

        assert contract.status == ContractStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_generate_tests_standard_mode(self, generator, sample_request, mock_llm):
        """Test generating tests in standard mode."""
        sample_request.mode = GenerationMode.STANDARD

        result = await generator.generate_tests(sample_request, mock_llm)

        assert isinstance(result, GenerationResult)
        assert result.request_id == "test-request-001"
        assert len(result.generated_tests) > 0
        assert len(result.self_evaluations) == len(result.generated_tests)
        assert result.generation_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_generate_tests_boundary_mode(self, generator, sample_request, mock_llm):
        """Test generating tests in boundary mode."""
        sample_request.mode = GenerationMode.BOUNDARY

        result = await generator.generate_tests(sample_request, mock_llm)

        assert result.boundary_coverage > 0
        # Boundary mode should have high boundary coverage
        assert result.boundary_coverage >= 50

    @pytest.mark.asyncio
    async def test_generate_tests_adversarial_mode(self, generator, sample_request, mock_llm):
        """Test generating tests in adversarial mode."""
        sample_request.mode = GenerationMode.ADVERSARIAL

        result = await generator.generate_tests(sample_request, mock_llm)

        assert result.adversarial_ratio == 100  # All adversarial

    @pytest.mark.asyncio
    async def test_self_evaluation(self, generator, sample_request, mock_llm):
        """Test self-evaluation of generated tests."""
        sample_request.mode = GenerationMode.STANDARD

        result = await generator.generate_tests(sample_request, mock_llm)

        for evaluation in result.self_evaluations:
            assert evaluation.test_case_id in [t["case_id"] for t in result.generated_tests]
            assert 0.0 <= evaluation.test_diversity_score <= 1.0
            assert 0.0 <= evaluation.confidence <= 1.0
            assert isinstance(evaluation.passes_own_criteria, bool)
            assert isinstance(evaluation.ready_for_qa, bool)

    @pytest.mark.asyncio
    async def test_diversity_score_calculation(self, generator, sample_request, mock_llm):
        """Test diversity score calculation."""
        sample_request.mode = GenerationMode.STANDARD
        sample_request.history_vectors = [[0.1] * 128, [0.2] * 128]

        result = await generator.generate_tests(sample_request, mock_llm)

        assert 0.0 <= result.diversity_score <= 1.0

    @pytest.mark.asyncio
    async def test_contract_compliance_check(self, generator, sample_request, mock_llm):
        """Test contract compliance checking."""
        # Create a contract
        contract = SprintContract(
            contract_id="contract-001",
            status=ContractStatus.ACCEPTED,
            success_criteria=[
                {
                    "criterion_type": "test_diversity",
                    "threshold": 0.5,
                    "weight": 1.0,
                }
            ]
        )
        sample_request.sprint_contract = contract

        result = await generator.generate_tests(sample_request, mock_llm)

        # Should check compliance
        assert isinstance(result.contract_compliant, bool)

    @pytest.mark.asyncio
    async def test_generation_statistics_tracking(self, generator, sample_request, mock_llm):
        """Test that generation tracks statistics."""
        initial_count = generator.generation_count

        await generator.generate_tests(sample_request, mock_llm)

        assert generator.generation_count > initial_count


# ============================================================================
# SelfEvaluation Tests
# ============================================================================

class TestSelfEvaluation:
    """Tests for SelfEvaluation dataclass."""

    def test_self_evaluation_creation(self):
        """Test creating a self-evaluation."""
        evaluation = SelfEvaluation(
            test_case_id="test-001",
            test_diversity_score=0.85,
            expected_adversarial=False,
            contract_compliant=True,
            reasoning="Good diversity",
            confidence=0.9,
            passes_own_criteria=True,
            ready_for_qa=True,
        )

        assert evaluation.test_case_id == "test-001"
        assert evaluation.test_diversity_score == 0.85
        assert evaluation.passes_own_criteria is True


# ============================================================================
# GenerationResult Tests
# ============================================================================

class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_generation_result_creation(self):
        """Test creating a generation result."""
        result = GenerationResult(
            request_id="req-001",
            generated_tests=[{"case_id": "test-1"}],
            self_evaluations=[],
            generation_time_seconds=1.5,
            diversity_score=0.8,
            boundary_coverage=50.0,
            adversarial_ratio=10.0,
            contract_compliant=True,
        )

        assert result.request_id == "req-001"
        assert len(result.generated_tests) == 1
        assert result.generation_time_seconds == 1.5
        assert isinstance(result.timestamp, datetime)


# ============================================================================
# Integration Tests
# ============================================================================

class TestGeneratorIntegration:
    """Integration tests for test generator."""

    @pytest.fixture
    def generator(self):
        return EnhancedTestGenerator()

    @pytest.fixture
    def sample_contracts(self):
        return {
            "l1_api": {"max_dimension": 2048, "allowed_metrics": ["L2"]},
        }

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self, generator, sample_contracts, mock_llm):
        """Test complete workflow: negotiate -> generate -> evaluate."""
        request = GenerationRequest(
            request_id="integration-test-001",
            mode=GenerationMode.STANDARD,
            target_db="milvus",
            contracts=sample_contracts,
            num_tests=3,
        )

        # Step 1: Negotiate contract
        async def accept_proposal(proposal):
            proposal.message = "Accept"
            return proposal

        contract = await generator.negotiate_contract(request, accept_proposal)
        assert contract.status == ContractStatus.ACCEPTED

        # Step 2: Generate tests
        result = await generator.generate_tests(request, mock_llm)

        # Step 3: Verify results
        assert len(result.generated_tests) > 0
        assert len(result.self_evaluations) > 0
        assert result.contract_compliant is True

    @pytest.mark.asyncio
    async def test_multi_mode_generation(self, generator, sample_contracts, mock_llm):
        """Test generating tests in multiple modes."""
        modes = [
            GenerationMode.STANDARD,
            GenerationMode.BOUNDARY,
            GenerationMode.ADVERSARIAL,
        ]

        results = []
        for mode in modes:
            request = GenerationRequest(
                request_id=f"multi-{mode.value}",
                mode=mode,
                target_db="milvus",
                contracts=sample_contracts,
                num_tests=2,
            )

            result = await generator.generate_tests(request, mock_llm)
            results.append(result)

        # Each mode should produce different characteristics
        standard_result = next(r for r in results if "standard" in r.request_id)
        boundary_result = next(r for r in results if "boundary" in r.request_id)
        adversarial_result = next(r for r in results if "adversarial" in r.request_id)

        # Boundary mode should have highest boundary coverage
        assert boundary_result.boundary_coverage > standard_result.boundary_coverage

        # Adversarial mode should have 100% adversarial ratio
        assert adversarial_result.adversarial_ratio == 100.0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
