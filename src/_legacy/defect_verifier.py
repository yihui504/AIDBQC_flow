from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

from src.ann_whitelist import ANNWhitelistChecker
from src.models.defect import DefectReport, EvidenceChain, Severity
from src.models.issue import BugIssue, VerificationStatus

logger = logging.getLogger(__name__)


@dataclass
class MREVerificationResult:
    success: bool = False
    status: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0


@dataclass
class DeveloperReviewResult:
    passed: bool = False
    reproducibility: float = 0.0
    evidence_completeness: float = 0.0
    problem_clarity: float = 0.0
    reference_authenticity: float = 0.0
    reasoning: str = ""
    false_positive_risk: float = 1.0


class DefectVerifier:
    def __init__(self, config=None, code_runner=None, ann_checker=None):
        self.config = config
        self.code_runner = code_runner
        self.ann_checker = ann_checker or ANNWhitelistChecker()

    def verify_mre_in_clean_env(self, mre_code: str, milvus_host: str = "localhost",
                                 milvus_port: int = 19530,
                                 timeout: int = 60) -> MREVerificationResult:
        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "-c", mre_code],
                capture_output=True, text=True, timeout=timeout,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "MILVUS_HOST": milvus_host,
                    "MILVUS_PORT": str(milvus_port),
                    "PYTHONPATH": "",
                },
            )
            duration = (time.time() - start) * 1000

            stdout = result.stdout[:2000]
            stderr = result.stderr[:1000]

            if result.returncode == 0:
                if "MRE_EXECUTION: SUCCESS" in stdout:
                    status = "SUCCESS"
                elif "MRE_EXECUTION: FAILED" in stdout:
                    status = "EXPECTED_REJECTION"
                else:
                    status = "SUCCESS"
            else:
                if "MRE_EXECUTION: FAILED" in stdout or "MRE_EXECUTION: FAILED" in stderr:
                    status = "EXPECTED_REJECTION"
                else:
                    status = "FAILED"

            return MREVerificationResult(
                success=status in ("SUCCESS", "EXPECTED_REJECTION"),
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=result.returncode,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            return MREVerificationResult(
                success=False, status="TIMEOUT",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return MREVerificationResult(
                success=False, status="ERROR",
                stderr=str(e)[:500],
                duration_ms=(time.time() - start) * 1000,
            )

    def developer_review(self, issue: BugIssue) -> DeveloperReviewResult:
        evidence = issue.evidence_chain
        completeness = evidence.completeness_score() if hasattr(evidence, "completeness_score") else 0.0

        reproducibility = 0.0
        if issue.mre_code and len(issue.mre_code.strip()) > 20:
            reproducibility += 0.4
        if evidence and hasattr(evidence, "execution_log") and evidence.execution_log:
            reproducibility += 0.3

        evidence_score = completeness

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
        if evidence and hasattr(evidence, "doc_references") and evidence.doc_references:
            reference_authenticity += 0.3

        ann_check = {"is_potential_bug": True}
        if issue.defect_type and "semantic" in issue.defect_type.value.lower():
            index_type = "HNSW"
            metric_type = "L2"
            if issue.actual_behavior:
                act_lower = issue.actual_behavior.lower()
                for idx in self.ann_checker.get_all_approximate_indices():
                    if idx.lower() in act_lower:
                        index_type = idx
                        break
                for mt in ["L2", "IP", "COSINE", "HAMMING"]:
                    if mt.lower() in act_lower:
                        metric_type = mt
                        break
            ann_check = self.ann_checker.check_recall_claim(
                index_type=index_type, metric_type=metric_type, observed_recall=0.95
            )

        false_positive_risk = 1.0 - (reproducibility * 0.3 + evidence_score * 0.3 + problem_clarity * 0.2 + reference_authenticity * 0.2)
        if ann_check.get("is_ann_related") and not ann_check.get("is_potential_bug"):
            false_positive_risk = min(1.0, false_positive_risk + 0.3)

        false_positive_risk = max(0.0, min(1.0, false_positive_risk))

        passed = false_positive_risk < 0.3 and completeness > 0.5

        reasoning_parts = []
        if reproducibility < 0.5:
            reasoning_parts.append("MRE code may not be sufficient for reproduction")
        if evidence_score < 0.5:
            reasoning_parts.append("Evidence chain is incomplete")
        if problem_clarity < 0.5:
            reasoning_parts.append("Problem description lacks clarity")
        if reference_authenticity < 0.3:
            reasoning_parts.append("No documentation reference provided")
        if ann_check.get("is_ann_related") and not ann_check.get("is_potential_bug"):
            reasoning_parts.append("This may be expected ANN approximation behavior")

        return DeveloperReviewResult(
            passed=passed,
            reproducibility=reproducibility,
            evidence_completeness=evidence_score,
            problem_clarity=problem_clarity,
            reference_authenticity=reference_authenticity,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "All checks passed",
            false_positive_risk=false_positive_risk,
        )

    def check_evidence_completeness(self, defect: DefectReport) -> dict:
        evidence = defect.evidence_chain
        checks = {
            "has_mre_code": bool(evidence.mre_code and len(evidence.mre_code.strip()) > 10),
            "has_execution_log": bool(evidence.execution_log and len(evidence.execution_log) > 0),
            "has_doc_reference": bool(evidence.doc_references and len(evidence.doc_references) > 0),
            "has_source_url": bool(defect.source_url),
        }

        completeness = sum(1 for v in checks.values() if v) / len(checks)

        if not checks["has_source_url"]:
            return {
                "complete": False,
                "completeness": completeness,
                "checks": checks,
                "downgrade": "Defect without source_url is downgraded to L3 observation",
            }

        return {
            "complete": completeness >= 0.75,
            "completeness": completeness,
            "checks": checks,
        }

    def generate_issue(self, defect: DefectReport,
                        review_result: DeveloperReviewResult) -> Optional[BugIssue]:
        if not review_result.passed:
            logger.info(f"Defect {defect.defect_id} rejected: false_positive_risk={review_result.false_positive_risk:.2f}")
            return None

        if not defect.source_url:
            logger.info(f"Defect {defect.defect_id} downgraded: no source_url")
            return None

        issue = BugIssue(
            issue_id=defect.defect_id.replace("DEF-", "ISS-"),
            title=defect.title,
            defect_type=defect.defect_type,
            severity=defect.severity,
            mre_code=defect.evidence_chain.mre_code,
            expected_behavior="",
            actual_behavior=defect.description,
            evidence_chain=defect.evidence_chain,
            doc_reference_url=defect.source_url,
            verification_status=VerificationStatus.VERIFIED,
            milvus_version="",
        )
        return issue
