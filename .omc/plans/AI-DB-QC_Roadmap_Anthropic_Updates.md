# AI-DB-QC Roadmap Updates - Anthropic Harness Best Practices

**Date**: 2026-03-30
**Source**: [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
**Version**: v1.1

---

## Summary of Changes

Based on Anthropic's official harness design research, the AI-DB-QC roadmap has been updated to incorporate proven patterns for long-running autonomous agents.

**Updated Metrics**:
- Total Tasks: 12 → **13** (+1 task)
- Total Hours: 248h → **268h** (+20h)

---

## New Tasks Added

### TASK-1.5: Context Reset Strategy (12h)

**Inspired by**: Anthropic's finding that *"Context resets—clearing the context window entirely and starting a fresh agent, combined with a structured handoff—addresses both context anxiety and context window filling."*

**Implementation**:
- `src/context/reset_manager.py` - Manages context reset logic
- `src/context/handoff.py` - Structured handoff artifacts using WorkflowState
- Reset after every N tests (configurable)
- Clear conversation history but preserve state across resets

**Acceptance Criteria**:
- 95% reset recovery success rate
- 100% state integrity
- 20% token efficiency improvement
- 100% context anxiety elimination

---

## Enhanced Tasks

### TASK-2.1: EnhancedSemanticOracle + Evaluator Calibration Loop (40h → 48h)

**Key Addition**: Evaluator Calibration Loop based on Anthropic's tuning methodology:

> *"Out of the box, Claude is a poor QA agent... The tuning loop was to read the evaluator's logs, find examples where its judgment diverged from mine, and update the QA's prompt to solve for those issues."*

**New Components**:
- `src/oracles/evaluator_calibration.py` - Calibration loop implementation
- `src/contracts/sprint_contract.py` - Sprint contract negotiation
- `src/harness/grading_criteria.py` - Explicit grading criteria
- Validation set with 100+ known bug samples
- Few-shot example library with 20+ scored samples

**New Acceptance Criteria**:

| Criterion | Target | Anthropic Alignment |
|-----------|--------|---------------------|
| Evaluator Precision | 90%+ | *"Alignment with human judgment"* |
| False Positive Rate | <10% | *"Leniency correction"* |
| Contract Negotiation Success | 95%+ | *"Sprint contracts before work"* |
| Avg Negotiation Rounds | ≤3 | *"Iterate until agreement"* |

**Explicit Grading Criteria** (mapped from Anthropic's design criteria):

| Anthropic Criterion | AI-DB-QC Equivalent | Threshold |
|---------------------|---------------------|-----------|
| Design quality | Test Diversity | cosine similarity < 0.7 |
| Originality | Defect Novelty | semantic similarity > 0.8 |
| Craft | Contract Adherence | 100% L1/L2 compliance |
| Functionality | Bug Realism | weighted score > 0.75 |

### TASK-2.2: EnhancedTestGenerator + Sprint Contract Integration (32h, unchanged)

**Enhancement Description**: Added sprint contract negotiation with evaluator before test generation.

**New Components**:
- `src/contracts/contract_negotiation.py` - Negotiation orchestration
- Contract defines: test_scope, success_criteria, verification_methods, oracle_constraints

**New Acceptance Criteria**:
- 95% contract compliance rate

---

## Dependency Updates

```
TASK-1.5 (Context Reset) depends on: TASK-1.3 (Unit Tests)
TASK-2.1 (Enhanced Oracle) depends on: TASK-1.2, TASK-1.4, TASK-1.5 (NEW)
```

---

## Implementation Priority

### Week 1-2 (Phase 1: Engineering Reliability)
- [ ] TASK-1.1: PersistentCollectionPool (24h, P0)
- [ ] TASK-1.2: Exception Handling (16h, P0)
- [ ] TASK-1.3: Unit Tests (24h, P0)
- [ ] TASK-1.4: Config Centralization (8h, P1)
- [ ] **TASK-1.5: Context Reset Strategy (12h, P1)** ← NEW

### Week 3-5 (Phase 2: Testing Capability)
- [ ] **TASK-2.1: Enhanced Oracle + Calibration (48h, P0)** ← ENHANCED
- [ ] **TASK-2.2: Enhanced Generator + Contracts (32h, P0)** ← ENHANCED
- [ ] TASK-2.3: Enhanced Deduplicator (24h, P1)

---

## Technical Specifications

### Evaluator Calibration Loop Algorithm

```python
async def evaluator_tuning_loop(
    evaluator: Agent4,
    validation_set: List[BugExample],
    target_accuracy: float = 0.90
) -> Prompt:
    current_prompt = evaluator.system_prompt
    best_prompt = current_prompt
    best_accuracy = 0.0

    for iteration in range(10):  # Max 10 tuning rounds
        # 1. Run evaluator on validation set
        results = await evaluator.evaluate(validation_set)

        # 2. Compare to ground truth
        accuracy = calculate_accuracy(results, validation_set)

        # 3. If improved, save prompt
        if accuracy > best_accuracy:
            best_prompt = current_prompt
            best_accuracy = accuracy

        # 4. Check if target met
        if accuracy >= target_accuracy:
            break

        # 5. Analyze divergences
        divergences = find_divergences(results, validation_set)

        # 6. Update prompt to address divergences
        current_prompt = refine_prompt(current_prompt, divergences)

    return best_prompt
```

### Context Reset Strategy

```python
def should_reset_context(state: WorkflowState) -> bool:
    # Reset after N tests OR token threshold
    return (state.tests_completed % 50 == 0) or \
           (state.total_tokens_used > 80000)

async def context_reset_workflow(state: WorkflowState):
    # 1. Save state to checkpoint
    await save_checkpoint(state)

    # 2. Clear conversation history
    state.conversation_history = []

    # 3. Load fresh agent with state artifact
    fresh_agent = create_agent_with_state(state)

    return fresh_agent
```

### Sprint Contract Negotiation

```python
class SprintContract(BaseModel):
    test_scope: str
    success_criteria: List[str]
    verification_methods: List[str]
    oracle_constraints: Dict[str, Any]

async def negotiate_contract(
    generator: Agent2,
    evaluator: Agent4,
    test_scope: str
) -> SprintContract:
    # 1. Generator proposes
    proposal = await generator.propose_contract(test_scope)

    # 2. Evaluator reviews
    feedback = await evaluator.review_contract(proposal)

    # 3. Iterate until agreement (max 3 rounds)
    while not feedback.approved and iteration < 3:
        proposal = await generator.revise_contract(feedback)
        feedback = await evaluator.review_contract(proposal)

    return proposal
```

---

## Validation Set Requirements

For the evaluator calibration loop, a validation set of known bugs is required:

| Bug Type | Min Samples | Source |
|----------|-------------|--------|
| Type-1: Crash/Exception | 25 | GitHub issues, manual seeding |
| Type-2: Incorrect Result | 30 | Regression tests |
| Type-3: Performance | 25 | Stress tests |
| Type-4: Semantic Drift | 20 | Expert labeling |

**Total**: 100+ samples with:
- Ground truth labels (bug/no-bug)
- Defect type classification
- Severity rating
- Expected fix description

---

## Success Metrics

Based on Anthropic's approach, success is measured by:

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Evaluator Precision | Unknown | 90%+ | Validation set accuracy |
| False Positive Rate | Unknown | <10% | Human review sample |
| Test Diversity | 0.7 threshold | 0.5 threshold | Semantic similarity |
| Token Efficiency | Baseline | +20% | Context reset impact |
| Defect Discovery Rate | Baseline | +300% | Final experiment |

---

## References

1. [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) - Prithvi Rajasekaran, Anthropic Labs
2. [AI-DB-QC Anthropic Harness Mapping](.omc/plans/AI-DB-QC_Anthropic_Harness_Mapping.md) - Detailed analysis
3. [DETAILED_IMPLEMENTATION_PLAN](.omc/plans/DETAILED_IMPLEMENTATION_PLAN.md) - Original 1000-line plan

---

## Next Steps

1. ✅ Review Anthropic article and create mapping document
2. ✅ Update roadmap with new tasks and enhancements
3. ⏳ Begin TASK-1.1 implementation (PersistentCollectionPool)
4. ⏳ Build validation set for evaluator calibration (TASK-2.1 prerequisite)

**Status**: Roadmap updated and ready for implementation.
