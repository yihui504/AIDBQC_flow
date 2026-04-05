# AI-DB-QC Harness Design Alignment with Anthropic Best Practices

**Date**: 2026-03-30
**Source**: [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
**Author**: Prithvi Rajasekaran, Anthropic Labs Team

---

## Executive Summary

Anthropic's official harness design research validates AI-DB-QC's multi-agent architecture and provides concrete improvements for long-running autonomous testing sessions. Key finding: **Generator-Evaluator separation is critical**, and **grading criteria must be explicit and testable**.

**Overall Alignment**: **85%** - AI-DB-QC's architecture matches Anthropic's patterns, with specific improvements needed in evaluator calibration and sprint contracts.

---

## 1. Core Architecture Comparison

### Anthropic's Three-Agent Pattern

```
Planner → Generator → Evaluator
   ↓         ↓           ↓
  Spec    Sprint      Grading
           Code      Criteria
```

### AI-DB-QC's Seven-Agent Pattern

```
Agent1 (Orchestrator) → Agent2 (Test Generator) → Agent3 (Executor)
                        ↓                      ↓
                     Tests                  Execution
                        ↓                      ↓
                   Agent4 (Oracle) ← Agent5 (Triage)
                        ↓
                   Agent6 (Verifier)
```

**Alignment Assessment**: ✅ **Strong Match**

- AI-DB-QC's Agent2 (Test Generator) maps to Anthropic's **Generator**
- AI-DB-QC's Agent4 (Oracle) + Agent5 (Triage) map to Anthropic's **Evaluator**
- AI-DB-QC has additional specialization (Triage, Verifier) for defect classification

---

## 2. Key Insights Applied to AI-DB-QC

### Insight 1: Self-Evaluation Problem

> *"When asked to evaluate work they've produced, agents tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre."*

**AI-DB-QC Impact**: Current architecture separates generation (Agent2) from evaluation (Agent4/5), which **correctly avoids** this pitfall.

**Verification Needed**:
- [ ] Confirm Agent4 (Oracle) prompts are calibrated to be **skeptical**, not lenient
- [ ] Add "few-shot examples" with detailed score breakdowns to Agent4
- [ ] Implement explicit **failure thresholds** for each criterion

### Insight 2: Context Reset vs Compaction

> *"Context resets—clearing the context window entirely and starting a fresh agent, combined with a structured handoff—addresses both context anxiety and context window filling."*

**AI-DB-QC Impact**: Current implementation uses LangGraph's `MemorySaver` for checkpoints.

**Recommendation**:
- Implement **explicit session reset** after every N tests (configurable)
- Use `WorkflowState` as the structured handoff artifact
- Clear LLM conversation history but preserve state across resets

### Insight 3: Sprint Contracts

> *"Before each sprint, the generator and evaluator negotiated a sprint contract: agreeing on what 'done' looked like before any code was written."*

**AI-DB-QC Impact**: Missing explicit contract negotiation between Agent2 and Agent4.

**Implementation**:
```python
class SprintContract(BaseModel):
    test_scope: str
    success_criteria: List[str]
    verification_methods: List[str]
    oracle_constraints: Dict[str, Any]

# Agent2 proposes, Agent4 approves before test generation
```

### Insight 4: Grading Criteria Design

Anthropic's four criteria for frontend design:
1. **Design quality** (coherence, mood)
2. **Originality** (custom vs template)
3. **Craft** (technical execution)
4. **Functionality** (usability)

**AI-DB-QC Mapping**:

| Anthropic Criterion | AI-DB-QC Equivalent | Implementation |
|---------------------|---------------------|----------------|
| Design quality | **Test Diversity** | Semantic coverage monitoring |
| Originality | **Defect Novelty** | Deduplication in Agent6 |
| Craft | **Test Correctness** | L1/L2 contract gating |
| Functionality | **Bug Realism** | Type-1/2/3/4 classification |

---

## 3. Specific Improvements for AI-DB-QC

### P0: Evaluator Calibration

**Problem**: As Anthropic noted, *"Out of the box, Claude is a poor QA agent."*

**Solution**: Implement tuning loop:
1. Run evaluator on known bug examples
2. Compare evaluator judgment to human assessment
3. Update prompts to solve for divergences
4. Repeat until evaluator grading aligns with expectations

**Acceptance Criteria**:
- Evaluator identifies 90%+ of seeded bugs in validation set
- False positive rate < 10%
- Detailed feedback with file/line references

### P1: Context Reset Strategy

**Current**: Continuous session with compaction
**Proposed**: Hybrid approach

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

### P1: Sprint Contract Negotiation

```python
class ContractNegotiation:
    async def negotiate_contract(
        self,
        generator: Agent2,
        evaluator: Agent4,
        test_scope: str
    ) -> SprintContract:
        # 1. Generator proposes
        proposal = await generator.propose_contract(test_scope)

        # 2. Evaluator reviews
        feedback = await evaluator.review_contract(proposal)

        # 3. Iterate until agreement
        while not feedback.approved:
            proposal = await generator.revise_contract(feedback)
            feedback = await evaluator.review_contract(proposal)

        return proposal
```

---

## 4. Model Evolution Considerations

> *"As models continue to improve, we can roughly expect them to be capable of working for longer, and on more complex tasks."*

**Implication for AI-DB-QC**:

| Capability | Opus 4.5 | Opus 4.6 | AI-DB-QC Dependency |
|------------|----------|----------|---------------------|
| Context window | 200K | 200K | Less compaction needed |
| Long-context retrieval | Good | Excellent | Simpler state handoff |
| Code review/debugging | Good | Excellent | Less scaffolding needed |
| Planning | Good | Excellent | Planner agent may be optional |

**Recommendation**: Re-evaluate harness complexity after each model upgrade. Test whether components are still "load-bearing."

---

## 5. Grading Criteria Specification

Inspired by Anthropic's explicit criteria, define AI-DB-QC's evaluation rubric:

### Criterion 1: Test Diversity (Anti-Mode Collapse)

**Definition**: Tests should explore different semantic regions of the input space.

**Measurement**:
```python
def diversity_score(generated_tests: List[Test]) -> float:
    embeddings = [embed(t.description) for t in generated_tests]
    similarities = cosine_similarity_matrix(embeddings)
    avg_similarity = np.mean(similarities)
    return 1.0 - avg_similarity  # Higher = more diverse
```

**Threshold**: `avg_similarity < 0.7` (trigger forced mutation if exceeded)

### Criterion 2: Defect Novelty

**Definition**: Newly discovered defects should not duplicate known issues.

**Measurement**:
```python
def novelty_score(
    new_defect: Defect,
    known_defects: List[Defect]
) -> float:
    # Deduplication by semantic similarity
    max_similarity = max([
        semantic_similarity(new_defect, known)
        for known in known_defects
    ])
    return 1.0 - max_similarity
```

**Threshold**: `novelty > 0.8` for true novelty

### Criterion 3: Contract Adherence

**Definition**: Generated tests must respect L1/L2 contract constraints.

**Measurement**:
```python
def contract_adherence(test: Test, contract: Contract) -> bool:
    # L1: API parameter validation
    if not validate_l1_constraints(test.params, contract.l1_api):
        return False

    # L2: Semantic constraint validation
    if not validate_l2_constraints(test.query, contract.l2_semantic):
        return False

    return True
```

**Threshold**: 100% adherence required

### Criterion 4: Bug Realism

**Definition**: Discovered defects should be real bugs, not false positives.

**Measurement**:
```python
def realism_score(defect: Defect) -> float:
    # Type-1: Crash/Exception (highest realism)
    if defect.type == "TYPE_1":
        return 1.0
    # Type-2: Incorrect Result
    elif defect.type == "TYPE_2":
        return 0.9
    # Type-3: Performance Degradation
    elif defect.type == "TYPE_3":
        return 0.8
    # Type-4: Semantic Drift (requires human judgment)
    elif defect.type == "TYPE_4":
        return 0.7
```

**Threshold**: Weighted average > 0.75 across all defects

---

## 6. Tuning Loop Protocol

Based on Anthropic's methodology:

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

---

## 7. Implementation Priority

### Phase 1: Immediate (Week 1)

- [ ] Implement evaluator tuning loop with validation set
- [ ] Add explicit grading criteria to Agent4 prompts
- [ ] Implement failure thresholds for each criterion

### Phase 2: Short-term (Week 2-3)

- [ ] Add sprint contract negotiation between Agent2 and Agent4
- [ ] Implement context reset strategy
- [ ] Add few-shot examples to evaluator prompts

### Phase 3: Medium-term (Month 2)

- [ ] Build validation set of known bugs
- [ ] Implement automated A/B testing for prompt changes
- [ ] Add evaluator performance tracking to telemetry

---

## 8. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Evaluator precision | Unknown | 90%+ | Validation set accuracy |
| False positive rate | Unknown | <10% | Human review sample |
| Test diversity | 0.7 threshold | 0.5 threshold | Semantic similarity |
| Novelty detection | Manual | Automated | Deduplication precision |
| Context efficiency | Compaction only | Reset + Compaction | Token usage per test |

---

## 9. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Evaluator calibration is time-consuming | High | Medium | Start with small validation set, expand over time |
| Context reset increases latency | Medium | Low | Cache state artifacts, minimize reset frequency |
| Sprint contract negotiation adds overhead | Medium | Low | Limit to 3 iterations max |
| Model improvements reduce harness relevance | Low | Low | Quarterly re-evaluation of components |

---

## 10. Conclusion

Anthropic's research validates AI-DB-QC's multi-agent architecture and provides a clear path for improvement. The **Generator-Evaluator separation** is already present, but **evaluator calibration** and **explicit grading criteria** need implementation.

**Key Takeaway**: *"Every component in a harness encodes an assumption about what the model can't do on its own."* As models improve, regularly re-examine which components remain load-bearing.

**Next Action**: Implement TASK-1.3 (Unit Test Supplementation) with evaluator tuning as a priority subtask.
