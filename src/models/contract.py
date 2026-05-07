from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContractLevel(str, Enum):
    L1_API = "L1_API"
    L2_SEMANTIC = "L2_SEMANTIC"
    L3_APPLICATION = "L3_APPLICATION"


class ContractSource(str, Enum):
    DOCUMENTATION = "documentation"
    SOURCE_CODE = "source_code"
    BEHAVIOR = "behavior"
    LOGICAL_INFERENCE = "logical_inference"


class ContractRule(BaseModel):
    rule_id: str
    level: ContractLevel
    content: str
    constraint: str
    api_name: str | None = None
    parameter: str | None = None
    expected_behavior: str | None = None
    source_url: str | None = None


class ContractWithConfidence(BaseModel):
    rule: ContractRule
    confidence_score: float = Field(ge=0.0, le=1.0)
    sources: list[ContractSource] = Field(default_factory=list)
    refinement_history: list[str] = Field(default_factory=list)
    validated: bool = False

    def update_confidence(self, new_source: ContractSource, evidence: str, positive: bool = True) -> None:
        is_new_source = new_source not in self.sources
        if is_new_source:
            self.sources.append(new_source)
        self.refinement_history.append(f"+{new_source.value}: {evidence[:100]}")
        if not is_new_source:
            return
        source_count = len(set(self.sources))
        if positive:
            if source_count >= 3:
                self.confidence_score = min(0.95, self.confidence_score + 0.15)
            elif source_count >= 2:
                self.confidence_score = min(0.85, self.confidence_score + 0.1)
            else:
                self.confidence_score = min(0.7, self.confidence_score + 0.05)
        else:
            self.confidence_score = max(0.0, self.confidence_score - 0.1)
        if self.confidence_score >= 0.7 and source_count >= 2:
            self.validated = True


class ContractSet(BaseModel):
    l1_rules: list[ContractWithConfidence] = Field(default_factory=list)
    l2_rules: list[ContractWithConfidence] = Field(default_factory=list)
    l3_rules: list[ContractWithConfidence] = Field(default_factory=list)

    def all_rules(self) -> list[ContractWithConfidence]:
        return self.l1_rules + self.l2_rules + self.l3_rules

    def validated_rules(self) -> list[ContractWithConfidence]:
        return [r for r in self.all_rules() if r.validated]
