from __future__ import annotations

import json
import logging

from pydantic_ai import RunContext

from src.models.state import FocusMode, UnifiedState, tool_meta
from src.models.issue import BugIssue, VerificationStatus
from src.models.defect import DefectType, Severity
from src.models.contract import ContractSource
from src.tools.verify.filter import FalsePositiveFilter, FilterResult
from src.ann_whitelist import ANNWhitelistChecker
from src.config import DB_SDK_MAP
from src.tools.event_bus_holder import get_event_bus
from src.events import TestEventType, TestEvent

logger = logging.getLogger(__name__)


def _get_sandbox():
    try:
        from src.tools.code import _get_sandbox as _get_code_sandbox
        return _get_code_sandbox()
    except Exception as e:
        logger.warning(f"Sandbox unavailable: {e}")
        return None


@tool_meta(focus_modes=[FocusMode.VERIFICATION], permission="read", compress="summary")
async def contract_validate_source(
    ctx: RunContext[UnifiedState],
    rule_id: str,
    source_code_evidence: str,
) -> str:
    state = ctx.deps
    rule = next((r for r in state.contracts.all_rules() if r.rule.rule_id == rule_id), None)
    if rule is None:
        return json.dumps({"success": False, "rule_id": rule_id, "error": "Rule not found"})
    rule.update_confidence(ContractSource.SOURCE_CODE, source_code_evidence)
    return json.dumps({
        "success": True,
        "rule_id": rule_id,
        "confidence": rule.confidence_score,
        "validated": rule.validated,
        "sources": [s.value for s in rule.sources],
    })


@tool_meta(focus_modes=[FocusMode.VERIFICATION], permission="read", compress="summary")
async def contract_validate_behavior(
    ctx: RunContext[UnifiedState],
    rule_id: str,
    behavior_evidence: str,
    actual_result: str = "",
) -> str:
    state = ctx.deps
    rule = next((r for r in state.contracts.all_rules() if r.rule.rule_id == rule_id), None)
    if rule is None:
        return json.dumps({"success": False, "rule_id": rule_id, "error": "Rule not found"})
    rule.update_confidence(ContractSource.BEHAVIOR, behavior_evidence)
    return json.dumps({
        "success": True,
        "rule_id": rule_id,
        "confidence": rule.confidence_score,
        "validated": rule.validated,
        "sources": [s.value for s in rule.sources],
    })


@tool_meta(focus_modes=[FocusMode.VERIFICATION], permission="read", compress="summary")
async def contract_tri_validate(
    ctx: RunContext[UnifiedState],
    rule_id: str,
    doc_evidence: str,
    source_evidence: str,
    behavior_evidence: str,
) -> str:
    state = ctx.deps
    rule = next((r for r in state.contracts.all_rules() if r.rule.rule_id == rule_id), None)
    if rule is None:
        return json.dumps({"success": False, "rule_id": rule_id, "error": "Rule not found"})
    rule.update_confidence(ContractSource.DOCUMENTATION, doc_evidence)
    rule.update_confidence(ContractSource.SOURCE_CODE, source_evidence)
    rule.update_confidence(ContractSource.BEHAVIOR, behavior_evidence)
    source_values = set(s.value for s in rule.sources)
    tri_validated = {
        ContractSource.DOCUMENTATION.value,
        ContractSource.SOURCE_CODE.value,
        ContractSource.BEHAVIOR.value,
    }.issubset(source_values)
    return json.dumps({
        "success": True,
        "rule_id": rule_id,
        "confidence": rule.confidence_score,
        "validated": rule.validated,
        "sources": [s.value for s in rule.sources],
        "tri_validated": tri_validated,
    })


@tool_meta(focus_modes=[FocusMode.VERIFICATION, FocusMode.REPORTING], permission="read", compress="summary")
async def verify_defect(
    ctx: RunContext[UnifiedState],
    defect_id: str,
    verify_mre: bool = True,
) -> str:
    state = ctx.deps
    defect = next((d for d in state.defects if d.defect_id == defect_id), None)
    if defect is None:
        return json.dumps({"success": False, "defect_id": defect_id, "error": "Defect not found in state"})

    issue_id = defect.defect_id.replace("D-", "I-")
    existing_issue = next((i for i in state.issues if i.issue_id == issue_id), None)

    if existing_issue is None:
        dt = defect.defect_type if isinstance(defect.defect_type, DefectType) else DefectType.TRADITIONAL_ORACLE
        sev = defect.severity if isinstance(defect.severity, Severity) else Severity.MEDIUM
        issue = BugIssue(
            issue_id=issue_id,
            title=defect.title,
            defect_type=dt,
            severity=sev,
            mre_code=defect.evidence_chain.mre_code or "",
            expected_behavior=defect.expected_behavior or defect.description,
            actual_behavior=defect.actual_behavior or defect.description,
            evidence_chain=defect.evidence_chain,
            doc_reference_url=defect.source_url,
            db_version=state.target_version,
            target_db=state.target_db,
            sdk=DB_SDK_MAP.get(state.target_db, ""),
        )
        state.issues.append(issue)
    else:
        issue = existing_issue

    sandbox = _get_sandbox() if verify_mre else None
    ann_checker = ANNWhitelistChecker()
    fp_filter = FalsePositiveFilter(sandbox=sandbox, ann_checker=ann_checker)
    result: FilterResult = await fp_filter.filter(issue)

    if result.passed:
        new_status = VerificationStatus.FINAL
    elif not result.mre_reproducible:
        new_status = VerificationStatus.MRE_FAILED
    else:
        new_status = VerificationStatus.REVIEW_FAILED

    issue.verification_status = new_status

    bus = get_event_bus()
    if bus is not None:
        bus.emit(TestEvent(
            event_type=TestEventType.DEFECT_VERIFIED,
            session_id=state.run_id,
            round_id=f"R{state.round_number:03d}",
            data={"defect_id": defect_id, "review_passed": result.passed, "verification_status": new_status.value},
        ))

    return json.dumps({
        "success": result.passed,
        "defect_id": defect_id,
        "mre_reproducible": result.mre_reproducible,
        "mre_verified": result.mre_verified,
        "evidence_score": result.evidence_score,
        "is_ann_expected": result.is_ann_expected,
        "false_positive_risk": result.false_positive_risk,
        "verification_status": new_status.value,
        "reasoning": result.reasoning,
    })
