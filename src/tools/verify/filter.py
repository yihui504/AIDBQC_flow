from __future__ import annotations

import re
from dataclasses import dataclass

from src.models.issue import BugIssue


@dataclass
class FilterResult:
    passed: bool
    mre_reproducible: bool
    mre_verified: bool
    evidence_score: float
    is_ann_expected: bool
    false_positive_risk: float
    reasoning: str


class FalsePositiveFilter:
    def __init__(self, sandbox=None, ann_checker=None):
        self._sandbox = sandbox
        self._ann_checker = ann_checker

    async def filter(self, issue: BugIssue) -> FilterResult:
        mre_ok, mre_verified = await self._check_mre(issue)
        evidence_score = self._score_evidence(issue)
        ann_expected = self._check_ann(issue)
        dev_review = self._developer_review(issue)

        if ann_expected:
            fp_risk = min(1.0, dev_review + 0.3)
        else:
            fp_risk = dev_review

        if mre_verified:
            passed = fp_risk < 0.3 and evidence_score > 0.5 and mre_ok
        else:
            passed = fp_risk < 0.3 and evidence_score > 0.5

        reasoning_parts = []
        if mre_verified and not mre_ok:
            reasoning_parts.append("MRE not reproducible")
        if not mre_verified:
            reasoning_parts.append("MRE not verified (sandbox unavailable)")
        if evidence_score < 0.5:
            reasoning_parts.append("Evidence chain incomplete")
        if ann_expected:
            reasoning_parts.append("May be expected ANN approximation behavior")
        if fp_risk >= 0.3:
            reasoning_parts.append(f"High false positive risk ({fp_risk:.2f})")

        return FilterResult(
            passed=passed,
            mre_reproducible=mre_ok,
            mre_verified=mre_verified,
            evidence_score=evidence_score,
            is_ann_expected=ann_expected,
            false_positive_risk=fp_risk,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "All checks passed",
        )

    async def _check_mre(self, issue: BugIssue) -> tuple[bool, bool]:
        if not issue.mre_code or len(issue.mre_code.strip()) < 20:
            return False, True
        if self._sandbox is None:
            return False, False
        try:
            result = await self._sandbox.execute(issue.mre_code)
            return result.exit_code == 0, True
        except Exception:
            return False, True

    def _score_evidence(self, issue: BugIssue) -> float:
        score = 0.0
        evidence = issue.evidence_chain
        if evidence:
            if evidence.doc_references:
                score += 0.3
            if evidence.execution_log:
                score += 0.3
            if issue.mre_code and len(issue.mre_code.strip()) > 20:
                score += 0.2
            if evidence.source_code_refs:
                score += 0.2
        if issue.doc_reference_url:
            score += 0.1
        return min(1.0, score)

    def _check_ann(self, issue: BugIssue) -> bool:
        if self._ann_checker is None:
            return False
        if not issue.actual_behavior:
            return False
        act_lower = issue.actual_behavior.lower()
        is_semantic = issue.defect_type and "semantic" in issue.defect_type.value.lower()
        if not is_semantic:
            return False
        index_type = "HNSW"
        metric_type = "L2"
        for idx in ["hnsw", "ivf_flat", "ivf_sq8", "ivf_pq", "scann"]:
            if idx in act_lower:
                index_type = idx.upper()
                break
        for mt in ["l2", "ip", "cosine", "hamming"]:
            if mt in act_lower:
                metric_type = mt.upper()
                break
        recall_match = re.search(r'recall[:\s]+([0-9.]+)', act_lower)
        observed_recall = float(recall_match.group(1)) if recall_match else 0.95
        result = self._ann_checker.check_recall_claim(index_type=index_type, metric_type=metric_type, observed_recall=observed_recall)
        return result.get("is_ann_related", False) and not result.get("is_potential_bug", True)

    def _developer_review(self, issue: BugIssue) -> float:
        reproducibility = 0.0
        if issue.mre_code and len(issue.mre_code.strip()) > 20:
            reproducibility += 0.4
        evidence = issue.evidence_chain
        if evidence and evidence.execution_log:
            reproducibility += 0.3

        evidence_score = self._score_evidence(issue)

        problem_clarity = 0.0
        if issue.title and len(issue.title.strip()) > 10:
            problem_clarity += 0.3
        if issue.expected_behavior and len(issue.expected_behavior.strip()) > 10:
            problem_clarity += 0.3
        if issue.actual_behavior and len(issue.actual_behavior.strip()) > 10:
            problem_clarity += 0.3

        reference_authenticity = 0.0
        if issue.doc_reference_url:
            reference_authenticity += 0.5
        if evidence and evidence.doc_references:
            reference_authenticity += 0.3

        fp_risk = 1.0 - (reproducibility * 0.3 + evidence_score * 0.3 + problem_clarity * 0.2 + reference_authenticity * 0.2)
        return max(0.0, min(1.0, fp_risk))
