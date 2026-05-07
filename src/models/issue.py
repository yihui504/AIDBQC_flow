from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from src.models.defect import EvidenceChain, DefectType, Severity


class VerificationStatus(str, Enum):
    PENDING = "pending"
    MRE_PASSED = "mre_passed"
    MRE_FAILED = "mre_failed"
    REVIEW_PASSED = "review_passed"
    REVIEW_FAILED = "review_failed"
    FINAL = "final"


class ReviewDimension(str, Enum):
    REPRODUCIBILITY = "reproducibility"
    EVIDENCE_COMPLETENESS = "evidence_completeness"
    PROBLEM_CLARITY = "problem_clarity"
    REFERENCE_VALIDITY = "reference_validity"
    NOT_ACTUALLY_BUG = "not_actually_bug"


class ReviewScore(BaseModel):
    dimension: ReviewDimension
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class IssueReviewResult(BaseModel):
    passed: bool
    scores: list[ReviewScore] = Field(default_factory=list)
    overall_reasoning: str
    reviewer_model: str = "deepseek-chat"
    false_positive_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class BugIssue(BaseModel):
    issue_id: str
    title: str
    defect_type: DefectType
    severity: Severity = Severity.MEDIUM
    mre_code: str
    expected_behavior: str
    actual_behavior: str
    evidence_chain: EvidenceChain
    doc_reference_url: str | None = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    review_result: IssueReviewResult | None = None
    db_version: str = "2.6.12"
    target_db: str = "milvus"
    deployment_mode: str = "Docker Standalone"
    sdk: str = ""
    vector_config: str | None = None

    def to_markdown(self) -> str:
        sections = []
        sections.append("### Is there an existing issue for this?")
        sections.append("- [x] I have searched the existing issues")
        sections.append("")
        sections.append("### Environment")
        sections.append(f"- **{self.target_db.capitalize()} version**: {self.db_version}")
        sections.append(f"- **Deployment mode**: {self.deployment_mode}")
        sections.append(f"- **SDK/Client**: {self.sdk}")
        if self.vector_config:
            sections.append(f"- **Vector config**: {self.vector_config}")
        sections.append("")
        sections.append("### Describe the bug")
        sections.append(self.title)
        sections.append(f"\n**Severity**: {self.severity.value}")
        sections.append(f"**Defect Type**: {self.defect_type.value}")
        sections.append("")
        sections.append("### Steps To Reproduce")
        sections.append("```python")
        sections.append(self.mre_code)
        sections.append("```")
        sections.append("")
        sections.append("### Expected Behavior")
        sections.append(self.expected_behavior)
        sections.append("")
        sections.append("### Actual Behavior")
        sections.append(self.actual_behavior)
        if self.evidence_chain.docker_logs:
            sections.append("")
            sections.append("### Docker Logs")
            sections.append("```")
            sections.append(self.evidence_chain.docker_logs[:3000])
            sections.append("```")
        if self.evidence_chain.execution_log:
            sections.append("")
            sections.append("### Execution Log")
            for step in self.evidence_chain.execution_log:
                sections.append(f"- {step}")
        sections.append("")
        sections.append("### Evidence & Documentation")
        sections.append(f"- **Violated Contract Type**: {self.defect_type.value}")
        if self.doc_reference_url:
            sections.append(f"- **Official Docs Reference**: {self.doc_reference_url}")
        else:
            sections.append("- **Official Docs Reference**: N/A")
        sections.append(f"- **Verification Status**: {self.verification_status.value}")
        sections.append(f"- **Evidence Completeness**: {self.evidence_chain.completeness_score():.0%}")
        if self.evidence_chain.source_code_refs:
            sections.append(f"- **Source Code References**: {', '.join(self.evidence_chain.source_code_refs[:5])}")
        if self.review_result:
            sections.append(f"- **Developer Review**: {'PASSED' if self.review_result.passed else 'FAILED'}")
            sections.append(f"- **False Positive Risk**: {self.review_result.false_positive_risk:.0%}")
            sections.append(f"- **Reviewer Model**: {self.review_result.reviewer_model}")
            for score in self.review_result.scores:
                sections.append(f"  - {score.dimension.value}: {score.score:.2f} — {score.reasoning}")
            sections.append(f"- **Overall Reasoning**: {self.review_result.overall_reasoning}")
        return "\n".join(sections)
