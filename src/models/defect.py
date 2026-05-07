from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DefectType(str, Enum):
    ILLEGAL_SUCCESS = "Type-1: Illegal Success"
    INSUFFICIENT_DIAGNOSTICS = "Type-2: Insufficient Diagnostics"
    PRECONDITION_FAILURE = "Type-2.PF: Precondition Failure"
    TRADITIONAL_ORACLE = "Type-3: Traditional Oracle"
    SEMANTIC_VIOLATION = "Type-4: Semantic Violation"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceChain(BaseModel):
    doc_references: list[str] = Field(default_factory=list)
    execution_log: list[str] = Field(default_factory=list)
    docker_logs: str | None = None
    mre_code: str | None = None
    source_code_refs: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)

    def completeness_score(self) -> float:
        score = 0.0
        if self.doc_references:
            score += 0.25
        if self.execution_log:
            score += 0.2
        if self.docker_logs:
            score += 0.2
        if self.mre_code and len(self.mre_code.strip()) > 20:
            score += 0.2
        if self.source_code_refs:
            score += 0.15
        return score


class DefectReport(BaseModel):
    defect_id: str
    defect_type: DefectType
    severity: Severity
    title: str
    description: str
    evidence_chain: EvidenceChain = Field(default_factory=EvidenceChain)
    source_url: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    round_discovered: int = 0
