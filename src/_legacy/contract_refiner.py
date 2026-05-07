from __future__ import annotations

import logging
from typing import Optional
from dataclasses import dataclass

from src.models.contract import ContractRule, ContractWithConfidence, ContractLevel, ContractSource

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool = False
    confidence: float = 0.0
    sources_agree: list[str] = None
    sources_disagree: list[str] = None
    notes: str = ""

    def __post_init__(self):
        if self.sources_agree is None:
            self.sources_agree = []
        if self.sources_disagree is None:
            self.sources_disagree = []


class ContractRefiner:
    def __init__(self, config=None):
        self.config = config

    def validate_contract_with_source(self, contract: ContractWithConfidence,
                                       source_analysis: dict) -> ValidationResult:
        contract_text = contract.rule.content.lower()
        source_functions = source_analysis.get("key_functions", [])
        source_types = source_analysis.get("key_types", [])
        error_patterns = source_analysis.get("error_handling_patterns", [])

        agree_sources = []
        disagree_sources = []
        notes_parts = []

        for func in source_functions:
            func_lower = func.lower()
            keywords = contract_text.split()[:5]
            if any(kw in func_lower for kw in keywords if len(kw) > 3):
                agree_sources.append(f"function:{func[:80]}")

        for pattern in error_patterns:
            if "error" in contract_text.lower() or "fail" in contract_text.lower():
                agree_sources.append(f"error_pattern:{pattern[:60]}")

        if not agree_sources and not disagree_sources:
            notes_parts.append("No direct source evidence found for this contract")

        confidence = contract.confidence_score
        if agree_sources:
            confidence = min(1.0, confidence + 0.15)
        if disagree_sources:
            confidence = max(0.0, confidence - 0.3)
        if not agree_sources and not disagree_sources:
            confidence = max(0.0, confidence - 0.1)

        return ValidationResult(
            valid=len(disagree_sources) == 0,
            confidence=confidence,
            sources_agree=agree_sources[:5],
            sources_disagree=disagree_sources[:5],
            notes="; ".join(notes_parts) if notes_parts else "Source validation complete",
        )

    def validate_contract_with_behavior(self, contract: ContractWithConfidence,
                                         test_result: dict) -> ValidationResult:
        success = test_result.get("success", False)
        actual = test_result.get("actual_behavior", "")
        expected = test_result.get("expected_behavior", "")

        agree_sources = []
        disagree_sources = []

        if success:
            if actual and expected and actual.lower().strip() == expected.lower().strip():
                agree_sources.append("behavior_matches_expected")
            else:
                disagree_sources.append("behavior_differs_from_expected")
        else:
            if "error" in contract.rule.content.lower():
                agree_sources.append("expected_error_occurred")
            else:
                disagree_sources.append("unexpected_failure")

        confidence = contract.confidence_score
        if agree_sources:
            confidence = min(1.0, confidence + 0.2)
        if disagree_sources:
            confidence = max(0.0, confidence - 0.25)

        return ValidationResult(
            valid=len(disagree_sources) == 0,
            confidence=confidence,
            sources_agree=agree_sources,
            sources_disagree=disagree_sources,
            notes=f"Behavior validation: success={success}",
        )

    def compute_confidence(self, contract: ContractWithConfidence,
                           sources: list[str]) -> float:
        base = contract.confidence_score
        source_weights = {
            "doc": 0.2,
            "source": 0.25,
            "behavior": 0.3,
            "logical": 0.1,
        }

        for source in sources:
            source_lower = source.lower()
            for key, weight in source_weights.items():
                if key in source_lower:
                    base += weight

        return min(1.0, max(0.0, base))

    def refine_contract(self, contract: ContractWithConfidence,
                         evidence: dict) -> ContractWithConfidence:
        new_confidence = contract.confidence_score
        new_sources = list(contract.sources)

        validation = evidence.get("validation_result")
        if validation and isinstance(validation, ValidationResult):
            new_confidence = validation.confidence

        behavior_result = evidence.get("behavior_result")
        if behavior_result and isinstance(behavior_result, dict):
            if behavior_result.get("success"):
                new_confidence = min(1.0, new_confidence + 0.1)
                if ContractSource.BEHAVIOR not in new_sources:
                    new_sources.append(ContractSource.BEHAVIOR)

        source_result = evidence.get("source_result")
        if source_result and isinstance(source_result, dict):
            if source_result.get("key_functions"):
                new_confidence = min(1.0, new_confidence + 0.05)
                if ContractSource.SOURCE_CODE not in new_sources:
                    new_sources.append(ContractSource.SOURCE_CODE)

        return ContractWithConfidence(
            rule=contract.rule,
            confidence_score=round(new_confidence, 3),
            sources=new_sources,
            refinement_history=contract.refinement_history + [
                f"Refined: confidence {contract.confidence_score:.3f} -> {new_confidence:.3f}"
            ],
        )

    def tri_source_validate(self, doc_contract: ContractWithConfidence,
                             source_analysis: dict,
                             behavior_result: dict) -> ValidationResult:
        doc_valid = doc_contract.confidence_score >= 0.5
        source_validation = self.validate_contract_with_source(doc_contract, source_analysis)
        behavior_validation = self.validate_contract_with_behavior(doc_contract, behavior_result)

        agree = []
        disagree = []

        if doc_valid:
            agree.append("documentation")
        else:
            disagree.append("documentation_low_confidence")

        if source_validation.valid:
            agree.append("source_code")
        else:
            disagree.append("source_code_disagreement")

        if behavior_validation.valid:
            agree.append("behavior")
        else:
            disagree.append("behavior_disagreement")

        if len(agree) == 3:
            confidence = 0.9
        elif len(agree) == 2:
            confidence = 0.7
        elif len(agree) == 1 and doc_valid:
            confidence = 0.5
        else:
            confidence = 0.3

        return ValidationResult(
            valid=len(agree) >= 2,
            confidence=confidence,
            sources_agree=agree,
            sources_disagree=disagree,
            notes=f"Tri-source: doc={doc_valid}, source={source_validation.valid}, behavior={behavior_validation.valid}",
        )
