from __future__ import annotations

import json

from pydantic_ai import RunContext

from src.models.state import FocusMode, UnifiedState, tool_meta
from src.models.defect import DefectReport, DefectType, Severity, EvidenceChain
from src.models.issue import BugIssue, VerificationStatus
from src.config import DB_SDK_MAP
from src.tools.event_bus_holder import get_event_bus
from src.events import TestEventType, TestEvent


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING, FocusMode.GENERATION, FocusMode.EXECUTION, FocusMode.VERIFICATION, FocusMode.REPORTING], permission="read", compress="minimal")
async def update_focus(
    ctx: RunContext[UnifiedState],
    focus: str,
) -> str:
    try:
        new_focus = FocusMode(focus)
    except ValueError:
        return json.dumps({"success": False, "error": f"Invalid focus: {focus}. Valid: {[f.value for f in FocusMode]}"})
    old_focus = ctx.deps.current_focus
    ctx.deps.switch_focus(new_focus, reason="tool_call")
    return json.dumps({"success": True, "from": old_focus.value, "to": new_focus.value})


@tool_meta(focus_modes=[FocusMode.VERIFICATION, FocusMode.REPORTING], permission="write", compress="summary")
async def record_defect(
    ctx: RunContext[UnifiedState],
    defect_type: str,
    severity: str,
    title: str,
    description: str,
    mre_code: str,
    expected_behavior: str,
    actual_behavior: str,
    doc_reference_url: str = "",
) -> str:
    state = ctx.deps
    dt = None
    try:
        dt = DefectType(defect_type)
    except ValueError:
        for member in DefectType:
            if defect_type.lower().replace(" ", "") in member.value.lower().replace(" ", "") or member.value.lower().replace(" ", "") in defect_type.lower().replace(" ", ""):
                dt = member
                break
    if dt is None:
        dt = DefectType.TRADITIONAL_ORACLE
    sev = None
    try:
        sev = Severity(severity.lower())
    except ValueError:
        sev = Severity.MEDIUM

    state.defect_counter += 1
    defect_id = f"D-{state.defect_counter:03d}"
    defect = DefectReport(
        defect_id=defect_id,
        defect_type=dt,
        severity=sev,
        title=title,
        description=description,
        evidence_chain=EvidenceChain(mre_code=mre_code),
        source_url=doc_reference_url or None,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
    )
    state.defects.append(defect)

    bus = get_event_bus()
    if bus is not None:
        bus.emit(TestEvent(
            event_type=TestEventType.DEFECT_DISCOVERED,
            session_id=state.run_id,
            round_id=f"R{state.round_number:03d}",
            data={"defect_id": defect_id, "severity": severity, "title": title},
        ))

    issue_id = f"I-{state.defect_counter:03d}"
    existing = next((i for i in state.issues if i.issue_id == issue_id), None)
    if existing is None:
        issue = BugIssue(
            issue_id=issue_id,
            title=title,
            defect_type=dt,
            severity=sev,
            mre_code=mre_code,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            evidence_chain=defect.evidence_chain,
            doc_reference_url=doc_reference_url or None,
            verification_status=VerificationStatus.PENDING,
            db_version=state.target_version,
            target_db=state.target_db,
            sdk=DB_SDK_MAP.get(state.target_db, ""),
        )
        state.issues.append(issue)

    return json.dumps({
        "success": True,
        "defect_id": defect_id,
        "issue_id": issue.issue_id,
        "total_defects": len(state.defects),
        "total_issues": len(state.issues),
    })


@tool_meta(focus_modes=[FocusMode.REPORTING], permission="read", compress="summary")
async def generate_feedback(
    ctx: RunContext[UnifiedState],
) -> str:
    state = ctx.deps
    weak_points = []
    mutation_strategies = []
    coverage_gaps = []

    defect_types = [d.defect_type.value for d in state.defects]
    type_counts = {}
    for dt in defect_types:
        type_counts[dt] = type_counts.get(dt, 0) + 1
    for dt, count in type_counts.items():
        if count >= 2:
            weak_points.append(f"Repeated {dt} defects ({count}x)")

    if not any(d.defect_type == DefectType.ILLEGAL_SUCCESS for d in state.defects):
        coverage_gaps.append("No Type-1 (Illegal Success) defects found - try invalid inputs")
    if not any(d.defect_type == DefectType.SEMANTIC_VIOLATION for d in state.defects):
        coverage_gaps.append("No Type-4 (Semantic Violation) defects found - verify documented contracts")
    if not any(d.severity == Severity.CRITICAL for d in state.defects):
        mutation_strategies.append("Try boundary values and extreme inputs for higher severity defects")

    if state.current_focus == FocusMode.EXECUTION and len(state.defects) == 0:
        mutation_strategies.append("No defects found yet - try error handling and edge cases")
        weak_points.append("Zero defects may indicate insufficient test coverage")

    feedback = state.feedback
    feedback.weak_points = weak_points
    feedback.mutation_strategies = mutation_strategies
    feedback.coverage_gaps = coverage_gaps
    feedback.round_number = state.round_number

    state.feedback_history.append(feedback.model_copy())

    return json.dumps({
        "success": True,
        "weak_points": weak_points,
        "mutation_strategies": mutation_strategies,
        "coverage_gaps": coverage_gaps,
        "total_defects": len(state.defects),
    })
