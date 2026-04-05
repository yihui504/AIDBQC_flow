"""
Sprint Contract for AI-DB-QC

Implements Anthropic-style Sprint contract negotiation between:
- Agent 2 (Test Generator) and Agent 4 (Evaluator/QA)

The contract defines agreed-upon success criteria before test generation.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


class ContractStatus(str, Enum):
    """Status of a Sprint contract."""

    DRAFT = "draft"  # Initial proposal
    PROPOSED = "proposed"  # Sent to counterparty
    NEGOTIATING = "negotiating"  # Under discussion
    ACCEPTED = "accepted"  # Both parties agreed
    REJECTED = "rejected"  # Contract rejected
    FULFILLED = "fulfilled"  # Tests completed per contract
    BREACHED = "breached"  # Contract violated


class CriterionType(str, Enum):
    """Types of success criteria."""

    TEST_DIVERSITY = "test_diversity"
    DEFECT_NOVELTY = "defect_novelty"
    CONTRACT_ADHERENCE = "contract_adherence"
    BUG_REALISM = "bug_realism"
    MIN_BUGS = "min_bugs"
    MAX_FALSE_POSITIVES = "max_false_positives"


@dataclass
class SuccessCriterion:
    """A single success criterion in the contract."""

    criterion_type: CriterionType
    threshold: float
    weight: float = 1.0
    description: str = ""
    measurement_method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "criterion_type": self.criterion_type.value,
            "threshold": self.threshold,
            "weight": self.weight,
            "description": self.description,
            "measurement_method": self.measurement_method,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuccessCriterion":
        """Create from dictionary."""
        return cls(
            criterion_type=CriterionType(data["criterion_type"]),
            threshold=data["threshold"],
            weight=data.get("weight", 1.0),
            description=data.get("description", ""),
            measurement_method=data.get("measurement_method", ""),
        )


@dataclass
class ContractProposal:
    """A proposal for a Sprint contract."""

    proposal_id: str
    proposer: str  # "agent2_generator" or "agent4_evaluator"
    counterparty: str
    test_scope: Dict[str, Any]  # What tests will be generated
    success_criteria: List[SuccessCriterion]
    verification_methods: List[str]
    oracle_constraints: List[str]
    message: str = ""  # Message explaining the proposal
    proposed_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    revision: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "proposer": self.proposer,
            "counterparty": self.counterparty,
            "test_scope": self.test_scope,
            "success_criteria": [c.to_dict() for c in self.success_criteria],
            "verification_methods": self.verification_methods,
            "oracle_constraints": self.oracle_constraints,
            "proposed_at": self.proposed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revision": self.revision,
        }


@dataclass
class NegotiationRound:
    """A single round of contract negotiation."""

    round_id: str
    proposal_id: str
    from_agent: str
    to_agent: str
    message: str
    changes: Dict[str, Any]  # Proposed changes
    timestamp: datetime = field(default_factory=datetime.now)


class SprintContract(BaseModel):
    """
    A Sprint contract between test generator and evaluator.

    Defines agreed-upon success criteria before test generation begins.
    """

    contract_id: str = Field(description="Unique contract identifier")
    status: ContractStatus = Field(default=ContractStatus.DRAFT)

    # Parties
    generator_agent: str = Field(default="agent2_generator")
    evaluator_agent: str = Field(default="agent4_evaluator")

    # Contract content
    test_scope: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scope of tests to be generated"
    )
    success_criteria: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Agreed success criteria"
    )
    verification_methods: List[str] = Field(
        default_factory=list,
        description="How success will be verified"
    )
    oracle_constraints: List[str] = Field(
        default_factory=list,
        description="Constraints on oracle behavior"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    revision: int = Field(default=1)

    # Negotiation history
    negotiation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of negotiation rounds"
    )

    class Config:
        use_enum_values = True


class SprintContractManager:
    """
    Manages Sprint contract negotiation lifecycle.

    Based on Anthropic's research on agent coordination through
    explicit contracts before task execution.
    """

    def __init__(
        self,
        max_negotiation_rounds: int = 5,
        negotiation_timeout_seconds: int = 300,
        default_criteria: Optional[List[SuccessCriterion]] = None
    ):
        self.max_negotiation_rounds = max_negotiation_rounds
        self.negotiation_timeout_seconds = negotiation_timeout_seconds
        self.default_criteria = default_criteria or self._get_default_criteria()
        self.contracts: Dict[str, SprintContract] = {}
        self.proposals: Dict[str, ContractProposal] = {}

    def _get_default_criteria(self) -> List[SuccessCriterion]:
        """Get default success criteria."""
        return [
            SuccessCriterion(
                criterion_type=CriterionType.TEST_DIVERSITY,
                threshold=0.7,
                weight=1.0,
                description="Tests should be semantically diverse",
                measurement_method="cosine_similarity"
            ),
            SuccessCriterion(
                criterion_type=CriterionType.CONTRACT_ADHERENCE,
                threshold=0.95,
                weight=1.5,
                description="Tests must follow L1/L2/L3 contracts",
                measurement_method="validation"
            ),
            SuccessCriterion(
                criterion_type=CriterionType.BUG_REALISM,
                threshold=0.75,
                weight=1.2,
                description="Reported bugs should be realistic",
                measurement_method="manual_review"
            ),
        ]

    def create_initial_proposal(
        self,
        generator_id: str,
        evaluator_id: str,
        test_scope: Dict[str, Any],
        custom_criteria: Optional[List[SuccessCriterion]] = None
    ) -> ContractProposal:
        """
        Create initial contract proposal from generator.

        Args:
            generator_id: ID of generator agent
            evaluator_id: ID of evaluator agent
            test_scope: Scope of planned tests
            custom_criteria: Optional custom success criteria

        Returns:
            Initial ContractProposal
        """
        proposal_id = f"proposal_{generator_id}_{evaluator_id}_{datetime.now().timestamp()}"

        criteria = custom_criteria or self.default_criteria

        proposal = ContractProposal(
            proposal_id=proposal_id,
            proposer=generator_id,
            counterparty=evaluator_id,
            test_scope=test_scope,
            success_criteria=criteria,
            verification_methods=[
                "Automated grading",
                "Manual review for Type-2/3 bugs",
                "Regression testing"
            ],
            oracle_constraints=[
                "Oracle must provide detailed reasoning",
                "False positives must be justified",
                "L1 violations require minimal reproducible example"
            ]
        )

        self.proposals[proposal_id] = proposal
        return proposal

    async def negotiate_contract(
        self,
        initial_proposal: ContractProposal,
        evaluator_response: Callable[[ContractProposal], ContractProposal],
        generator_response: Optional[Callable[[ContractProposal], ContractProposal]] = None
    ) -> SprintContract:
        """
        Negotiate a contract between generator and evaluator.

        Args:
            initial_proposal: Initial proposal from generator
            evaluator_response: Async function that evaluates and responds
            generator_response: Optional async function for generator counter-response

        Returns:
            Agreed SprintContract
        """
        current_proposal = initial_proposal
        rounds = 0

        while rounds < self.max_negotiation_rounds:
            rounds += 1

            # Evaluator reviews proposal
            evaluator_proposal = await self._safe_async_call(
                evaluator_response(current_proposal)
            )

            # Record negotiation round
            self._add_negotiation_round(
                initial_proposal.proposal_id,
                current_proposal.proposer,
                evaluator_proposal.counterparty,
                f"Round {rounds}: Evaluator response",
                evaluator_proposal,
            )

            # Check if evaluator accepted
            if self._is_accepted(evaluator_proposal):
                # Create accepted contract
                contract = SprintContract(
                    contract_id=f"contract_{datetime.now().timestamp()}",
                    status=ContractStatus.ACCEPTED,
                    generator_agent=initial_proposal.proposer,
                    evaluator_agent=initial_proposal.counterparty,
                    test_scope=current_proposal.test_scope,
                    success_criteria=[c.to_dict() for c in evaluator_proposal.success_criteria],
                    verification_methods=evaluator_proposal.verification_methods,
                    oracle_constraints=evaluator_proposal.oracle_constraints,
                    accepted_at=datetime.now(),
                    negotiation_history=[]
                )

                self.contracts[contract.contract_id] = contract
                return contract

            # Check if evaluator rejected
            if self._is_rejected(evaluator_proposal):
                # Create rejected contract
                contract = SprintContract(
                    contract_id=f"contract_{datetime.now().timestamp()}",
                    status=ContractStatus.REJECTED,
                    generator_agent=initial_proposal.proposer,
                    evaluator_agent=initial_proposal.counterparty,
                    test_scope=current_proposal.test_scope,
                    negotiation_history=[]
                )

                self.contracts[contract.contract_id] = contract
                raise ValueError(f"Contract rejected by evaluator: {evaluator_proposal.success_criteria}")

            # Evaluator wants changes - give generator chance to respond
            if generator_response and rounds < self.max_negotiation_rounds:
                generator_proposal = await self._safe_async_call(
                    generator_response(evaluator_proposal)
                )

                # Record negotiation round
                self._add_negotiation_round(
                    initial_proposal.proposal_id,
                    generator_proposal.proposer,
                    generator_proposal.counterparty,
                    f"Round {rounds}: Generator counter-response",
                    generator_proposal,
                )

                # Check if generator accepted evaluator's terms
                if self._is_accepted(generator_proposal):
                    # Create accepted contract
                    contract = SprintContract(
                        contract_id=f"contract_{datetime.now().timestamp()}",
                        status=ContractStatus.ACCEPTED,
                        generator_agent=initial_proposal.proposer,
                        evaluator_agent=initial_proposal.counterparty,
                        test_scope=generator_proposal.test_scope,
                        success_criteria=[c.to_dict() for c in generator_proposal.success_criteria],
                        verification_methods=generator_proposal.verification_methods,
                        oracle_constraints=generator_proposal.oracle_constraints,
                        accepted_at=datetime.now(),
                        negotiation_history=[]
                    )

                    self.contracts[contract.contract_id] = contract
                    return contract

                current_proposal = generator_proposal

        # Max rounds reached - use last proposal
        contract = SprintContract(
            contract_id=f"contract_{datetime.now().timestamp()}",
            status=ContractStatus.ACCEPTED,  # Accept by default after max rounds
            generator_agent=initial_proposal.proposer,
            evaluator_agent=initial_proposal.counterparty,
            test_scope=current_proposal.test_scope,
            success_criteria=[c.to_dict() for c in current_proposal.success_criteria],
            verification_methods=current_proposal.verification_methods,
            oracle_constraints=current_proposal.oracle_constraints,
            accepted_at=datetime.now(),
            negotiation_history=[]
        )

        self.contracts[contract.contract_id] = contract
        return contract

    async def _safe_async_call(self, coro):
        """Safely execute async call."""
        try:
            return await asyncio.wait_for(coro, timeout=self.negotiation_timeout_seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Negotiation timeout after {self.negotiation_timeout_seconds}s")

    def _is_accepted(self, proposal: ContractProposal) -> bool:
        """Check if proposal indicates acceptance."""
        # Acceptance indicated by "accept" in message or no changes from previous
        return "accept" in proposal.message.lower() or "agreed" in proposal.message.lower()

    def _is_rejected(self, proposal: ContractProposal) -> bool:
        """Check if proposal indicates rejection."""
        return "reject" in proposal.message.lower() or "unable" in proposal.message.lower()

    def _add_negotiation_round(
        self,
        proposal_id: str,
        from_agent: str,
        to_agent: str,
        message: str,
        proposal: ContractProposal
    ):
        """Add a negotiation round to history."""
        if proposal_id not in self.proposals:
            return

        # Store proposal as part of history
        round_data = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "proposal": proposal.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

        # Store in proposal (in production, use separate storage)
        if not hasattr(self.proposals[proposal_id], 'history'):
            self.proposals[proposal_id].history = []
        self.proposals[proposal_id].history.append(round_data)

    def evaluate_contract_fulfillment(
        self,
        contract: SprintContract,
        test_results: List[Dict[str, Any]],
        grades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate if contract was fulfilled.

        Args:
            contract: The Sprint contract to evaluate
            test_results: Results of generated tests
            grades: Grades for each test

        Returns:
            Evaluation result with pass/fail per criterion
        """
        results = {
            "contract_id": contract.contract_id,
            "fulfilled": True,
            "criterion_results": [],
            "overall_score": 0.0,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for criterion_dict in contract.success_criteria:
            criterion_type = criterion_dict["criterion_type"]
            threshold = criterion_dict["threshold"]
            weight = criterion_dict.get("weight", 1.0)

            # Find corresponding grade
            criterion_result = self._evaluate_criterion(
                criterion_type,
                threshold,
                grades,
                test_results
            )

            passed = criterion_result["score"] >= threshold
            if not passed:
                results["fulfilled"] = False

            results["criterion_results"].append({
                "criterion_type": criterion_type,
                "threshold": threshold,
                "actual_score": criterion_result["score"],
                "passed": passed,
                "weight": weight,
            })

            total_weight += weight
            weighted_sum += criterion_result["score"] * weight

        if total_weight > 0:
            results["overall_score"] = weighted_sum / total_weight

        # Update contract status
        if results["fulfilled"]:
            contract.status = ContractStatus.FULFILLED
            contract.fulfilled_at = datetime.now()
        else:
            contract.status = ContractStatus.BREACHED

        return results

    def _evaluate_criterion(
        self,
        criterion_type: str,
        threshold: float,
        grades: List[Dict[str, Any]],
        test_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate a single criterion against grades."""

        if criterion_type == CriterionType.TEST_DIVERSITY:
            # Average test diversity across all tests
            diversity_scores = [
                g.get("grades", {}).get("test_diversity", {}).get("score", 0.5)
                for g in grades
            ]
            score = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.5

        elif criterion_type == CriterionType.DEFECT_NOVELTY:
            # Average defect novelty
            novelty_scores = [
                g.get("grades", {}).get("defect_novelty", {}).get("score", 0.5)
                for g in grades
            ]
            score = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.5

        elif criterion_type == CriterionType.CONTRACT_ADHERENCE:
            # Average contract adherence
            adherence_scores = [
                g.get("grades", {}).get("contract_adherence", {}).get("score", 0.5)
                for g in grades
            ]
            score = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.5

        elif criterion_type == CriterionType.BUG_REALISM:
            # Average bug realism
            realism_scores = [
                g.get("grades", {}).get("bug_realism", {}).get("score", 0.5)
                for g in grades
            ]
            score = sum(realism_scores) / len(realism_scores) if realism_scores else 0.5

        elif criterion_type == CriterionType.MIN_BUGS:
            # Count of bugs found vs threshold
            bug_count = sum(
                1 for r in test_results
                if r.get("is_bug", False)
            )
            score = min(1.0, bug_count / threshold) if threshold > 0 else 1.0

        elif criterion_type == CriterionType.MAX_FALSE_POSITIVES:
            # False positive count (lower is better)
            fp_count = sum(
                1 for r in test_results
                if r.get("is_bug", False) and r.get("bug_type") == "Type-4"
            )
            # Score = 1 if within limit, 0 if exceeded
            score = 1.0 if fp_count <= threshold else 0.0

        else:
            score = 0.5  # Default for unknown criteria

        return {"score": score}

    def get_contract(self, contract_id: str) -> Optional[SprintContract]:
        """Get a contract by ID."""
        return self.contracts.get(contract_id)

    def get_proposal(self, proposal_id: str) -> Optional[ContractProposal]:
        """Get a proposal by ID."""
        return self.proposals.get(proposal_id)
