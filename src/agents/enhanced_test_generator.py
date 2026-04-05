"""
Enhanced Test Generator for AI-DB-QC

Implements Anthropic-style test generation with Sprint contract integration:
- Contract negotiation before generation
- Self-evaluation after generation
- Diverse test generation
- Boundary value exploration
- Adversarial test generation

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from src.oracles.sprint_contract import (
    SprintContract,
    SprintContractManager,
    ContractProposal,
    SuccessCriterion,
    CriterionType,
)
from src.oracles.grading_criteria import GradingCriteria, OverallGrade


class GenerationMode(str, Enum):
    """Test generation modes."""

    STANDARD = "standard"  # Standard diverse tests
    BOUNDARY = "boundary"  # Boundary value exploration
    ADVERSARIAL = "adversarial"  # Edge case and stress tests
    REGRESSION = "regression"  # Regression testing for known bugs


@dataclass
class GenerationRequest:
    """Request for test generation."""

    request_id: str
    mode: GenerationMode
    target_db: str
    contracts: Dict[str, Any]  # L1/L2/L3 contracts
    history_vectors: List[List[float]] = field(default_factory=list)
    known_defects: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Sprint contract (if negotiated)
    sprint_contract: Optional[SprintContract] = None

    # Generation parameters
    num_tests: int = 1
    diversity_threshold: float = 0.7
    target_dimensions: List[int] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfEvaluation:
    """Generator's self-evaluation of generated tests."""

    test_case_id: str
    test_diversity_score: float
    expected_adversarial: bool
    contract_compliant: bool
    reasoning: str
    confidence: float

    # Overall assessment
    passes_own_criteria: bool
    ready_for_qa: bool


@dataclass
class GenerationResult:
    """Result of test generation."""

    request_id: str
    generated_tests: List[Dict[str, Any]]
    self_evaluations: List[SelfEvaluation]
    generation_time_seconds: float

    # Statistics
    diversity_score: float
    boundary_coverage: float
    adversarial_ratio: float

    # Contract compliance
    contract_compliant: bool
    contract_violations: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)


class TestGeneratorStrategy:
    """
    Base strategy for test generation.

    Different strategies for different generation modes.
    """

    async def generate(
        self,
        request: GenerationRequest,
        llm_client: Any
    ) -> List[Dict[str, Any]]:
        """Generate tests according to strategy."""
        raise NotImplementedError


class StandardGenerationStrategy(TestGeneratorStrategy):
    """Standard diverse test generation."""

    async def generate(
        self,
        request: GenerationRequest,
        llm_client: Any
    ) -> List[Dict[str, Any]]:
        """Generate standard diverse tests."""
        tests = []

        # Generate based on contract constraints
        for dimension in self._get_target_dimensions(request):
            for metric in request.contracts.get("l1_api", {}).get("allowed_metrics", ["L2"]):
                test = {
                    "case_id": f"{request.request_id}_{len(tests)}",
                    "dimension": dimension,
                    "metric_type": metric,
                    "query_vector": None,  # Will be filled by DB
                    "query_text": self._generate_query_text(dimension, metric),
                    "expected_l1_legal": True,
                    "expected_l2_ready": True,
                    "is_adversarial": False,
                    "semantic_intent": f"Standard {metric} search test at {dimension}D",
                }
                tests.append(test)

        return tests

    def _get_target_dimensions(self, request: GenerationRequest) -> List[int]:
        """Get target dimensions for testing."""
        if request.target_dimensions:
            return request.target_dimensions

        # Default dimensions to test
        default_dims = [64, 128, 256, 512, 1024, 2048]
        max_dim = request.contracts.get("l1_api", {}).get("max_dimension", 2048)
        return [d for d in default_dims if d <= max_dim]

    def _generate_query_text(self, dimension: int, metric: str) -> str:
        """Generate query text description."""
        return f"{metric} similarity search test at {dimension}D"


class BoundaryStrategy(TestGeneratorStrategy):
    """Boundary value exploration strategy."""

    async def generate(
        self,
        request: GenerationRequest,
        llm_client: Any
    ) -> List[Dict[str, Any]]:
        """Generate boundary value tests."""
        tests = []
        max_dim = request.contracts.get("l1_api", {}).get("max_dimension", 2048)

        # Boundary dimensions
        boundary_dims = [
            1,  # Minimum
            max_dim,  # Maximum
            max_dim + 1,  # Over maximum
            128,  # Common middle value
        ]

        for dimension in boundary_dims:
            if dimension > 0:  # Valid dimensions only
                test = {
                    "case_id": f"{request.request_id}_boundary_{len(tests)}",
                    "dimension": dimension,
                    "metric_type": "L2",
                    "query_text": f"Boundary test at {dimension}D",
                    "expected_l1_legal": dimension <= max_dim,
                    "expected_l2_ready": True,
                    "is_adversarial": dimension > max_dim,
                    "semantic_intent": f"Boundary value test: {dimension}D",
                }
                tests.append(test)

        return tests


class AdversarialStrategy(TestGeneratorStrategy):
    """Adversarial test generation strategy."""

    async def generate(
        self,
        request: GenerationRequest,
        llm_client: Any
    ) -> List[Dict[str, Any]]:
        """Generate adversarial tests."""
        tests = []

        # Generate adversarial test patterns
        adversarial_patterns = [
            {"name": "negative_dimension", "desc": "Negative dimension value"},
            {"name": "zero_vector", "desc": "All-zero vector"},
            {"name": "infinite_values", "desc": "Vector with infinity"},
            {"name": "mixed_types", "desc": "Vector with mixed data types"},
            {"name": "extreme_values", "desc": "Very large magnitude values"},
        ]

        max_dim = request.contracts.get("l1_api", {}).get("max_dimension", 2048)

        for pattern in adversarial_patterns:
            test = {
                "case_id": f"{request.request_id}_adv_{len(tests)}",
                "dimension": max_dim,
                "metric_type": "L2",
                "query_text": f"Adversarial: {pattern['desc']}",
                "expected_l1_legal": False,
                "expected_l2_ready": False,
                "is_adversarial": True,
                "semantic_intent": f"Adversarial test - {pattern['name']}",
                "adversarial_type": pattern["name"],
            }
            tests.append(test)

        return tests


class EnhancedTestGenerator:
    """
    Enhanced test generator with Sprint contract integration.

    Based on Anthropic's research:
    1. Negotiate contract with evaluator before generation
    2. Generate tests according to agreed criteria
    3. Self-evaluate before submitting to QA
    4. Maintain diversity and boundary coverage
    """

    def __init__(
        self,
        contract_manager: Optional[SprintContractManager] = None,
        grading_criteria: Optional[GradingCriteria] = None
    ):
        self.contract_manager = contract_manager or SprintContractManager()
        self.grading_criteria = grading_criteria or GradingCriteria()

        # Strategies
        self.strategies = {
            GenerationMode.STANDARD: StandardGenerationStrategy(),
            GenerationMode.BOUNDARY: BoundaryStrategy(),
            GenerationMode.ADVERSARIAL: AdversarialStrategy(),
        }

        # Statistics
        self.generation_count = 0
        self.contracts_negotiated = 0

    async def negotiate_contract(
        self,
        request: GenerationRequest,
        evaluator_response: Callable,
        llm_client: Optional[Any] = None
    ) -> SprintContract:
        """
        Negotiate Sprint contract with evaluator.

        Args:
            request: Generation request with test scope
            evaluator_response: Evaluator's response function
            llm_client: Optional LLM for enhanced negotiation

        Returns:
            Negotiated SprintContract
        """
        # Create initial proposal
        test_scope = {
            "mode": request.mode.value,
            "target_db": request.target_db,
            "num_tests": request.num_tests,
            "constraints": request.constraints,
        }

        initial_proposal = self.contract_manager.create_initial_proposal(
            generator_id="agent2_generator",
            evaluator_id="agent4_evaluator",
            test_scope=test_scope,
        )

        # Negotiate
        contract = await self.contract_manager.negotiate_contract(
            initial_proposal,
            evaluator_response
        )

        # Attach contract to request
        request.sprint_contract = contract
        self.contracts_negotiated += 1

        return contract

    async def generate_tests(
        self,
        request: GenerationRequest,
        llm_client: Any
    ) -> GenerationResult:
        """
        Generate tests according to request and contract.

        Args:
            request: Generation request
            llm_client: LLM client for generation

        Returns:
            GenerationResult with tests and evaluations
        """
        start_time = datetime.now()

        # Get strategy for mode
        strategy = self.strategies.get(request.mode, self.strategies[GenerationMode.STANDARD])

        # Generate tests
        generated_tests = await strategy.generate(request, llm_client)

        # Self-evaluate each test
        self_evaluations = []
        for test in generated_tests:
            eval_result = await self._self_evaluate(test, request, llm_client)
            self_evaluations.append(eval_result)

        # Calculate statistics
        diversity_score = self._calculate_diversity_score(generated_tests, request.history_vectors)
        boundary_coverage = self._calculate_boundary_coverage(generated_tests)
        adversarial_ratio = self._calculate_adversarial_ratio(generated_tests)

        # Check contract compliance
        contract_compliant, violations = await self._check_contract_compliance(
            generated_tests,
            request.sprint_contract,
            diversity_score
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        result = GenerationResult(
            request_id=request.request_id,
            generated_tests=generated_tests,
            self_evaluations=self_evaluations,
            generation_time_seconds=elapsed,
            diversity_score=diversity_score,
            boundary_coverage=boundary_coverage,
            adversarial_ratio=adversarial_ratio,
            contract_compliant=contract_compliant,
            contract_violations=violations,
        )

        self.generation_count += len(generated_tests)

        return result

    async def _self_evaluate(
        self,
        test: Dict[str, Any],
        request: GenerationRequest,
        llm_client: Any
    ) -> SelfEvaluation:
        """Generator's self-evaluation of a test."""

        # Calculate diversity score
        history = request.history_vectors
        test_vector = test.get("vector", [])

        if test_vector and history:
            # Simple cosine similarity
            import numpy as np
            max_sim = 0.0
            for hist_vec in history:
                if len(hist_vec) == len(test_vector):
                    dot = np.dot(test_vector, hist_vec)
                    norm1 = np.linalg.norm(test_vector)
                    norm2 = np.linalg.norm(hist_vec)
                    if norm1 > 0 and norm2 > 0:
                        sim = dot / (norm1 * norm2)
                        max_sim = max(max_sim, sim)

            diversity_score = 1.0 - max_sim
        else:
            diversity_score = 1.0

        # Check contract compliance
        is_compliant = True
        if request.contracts:
            l1_api = request.contracts.get("l1_api", {})
            if test["dimension"] > l1_api.get("max_dimension", 999999):
                is_compliant = False

        evaluation = SelfEvaluation(
            test_case_id=test["case_id"],
            test_diversity_score=diversity_score,
            expected_adversarial=test["is_adversarial"],
            contract_compliant=is_compliant,
            reasoning=f"Diversity: {diversity_score:.2f}, Adversarial: {test['is_adversarial']}",
            confidence=0.8,
            passes_own_criteria=diversity_score >= 0.7,
            ready_for_qa=is_compliant
        )

        return evaluation

    def _calculate_diversity_score(
        self,
        tests: List[Dict[str, Any]],
        history_vectors: List[List[float]]
    ) -> float:
        """Calculate average diversity score for generated tests."""
        if not tests:
            return 1.0

        diversity_scores = []
        for test in tests:
            test_vec = test.get("vector", [])
            if not test_vec or not history_vectors:
                diversity_scores.append(1.0)
                continue

            # Calculate max similarity
            max_sim = 0.0
            for hist_vec in history_vectors:
                if len(hist_vec) == len(test_vec):
                    import numpy as np
                    dot = np.dot(test_vec, hist_vec)
                    norm1 = np.linalg.norm(test_vec)
                    norm2 = np.linalg.norm(hist_vec)
                    if norm1 > 0 and norm2 > 0:
                        sim = dot / (norm1 * norm2)
                        max_sim = max(max_sim, sim)

            diversity_scores.append(1.0 - max_sim)

        return sum(diversity_scores) / len(diversity_scores) if diversity_scores else 1.0

    def _calculate_boundary_coverage(self, tests: List[Dict[str, Any]]) -> float:
        """Calculate boundary coverage percentage."""
        if not tests:
            return 0.0

        boundary_indicators = [
            "boundary",
            "over",
            "under",
            "extreme",
            "edge",
        ]

        boundary_tests = sum(
            1 for t in tests
            if any(ind in t.get("semantic_intent", "").lower() for ind in boundary_indicators)
        )

        return (boundary_tests / len(tests)) * 100

    def _calculate_adversarial_ratio(self, tests: List[Dict[str, Any]]) -> float:
        """Calculate adversarial test ratio."""
        if not tests:
            return 0.0

        adversarial_count = sum(1 for t in tests if t.get("is_adversarial", False))
        return (adversarial_count / len(tests)) * 100

    async def _check_contract_compliance(
        self,
        tests: List[Dict[str, Any]],
        contract: Optional[SprintContract],
        diversity_score: float = 1.0
    ) -> Tuple[bool, List[str]]:
        """Check if grade complies with Sprint contract."""
        if not contract:
            return True, []

        violations = []

        for criterion_dict in contract.success_criteria:
            criterion_type = criterion_dict["criterion_type"]
            threshold = criterion_dict["threshold"]

            if criterion_type == CriterionType.TEST_DIVERSITY:
                if diversity_score < threshold:
                    violations.append(f"Diversity {diversity_score:.2f} < threshold {threshold}")

            elif criterion_type == CriterionType.CONTRACT_ADHERENCE:
                non_compliant = sum(
                    1 for t in tests
                    if t.get("dimension", 999999) > 2048  # Simple check
                )
                if non_compliant > 0:
                    violations.append(f"{non_compliant} tests violate dimension constraints")

        compliant = len(violations) == 0
        return compliant, violations

    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_generations": self.generation_count,
            "contracts_negotiated": self.contracts_negotiated,
            "available_strategies": list(self.strategies.keys()),
        }
