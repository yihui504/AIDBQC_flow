# AI-DB-QC Improvement Plans

## Available Plans

### [AI-DB-QC Documentation Enhancement](./ai-db-qc-documentation-enhancement.md)
**Status:** Draft | **Priority:** HIGH | **Effort:** 10-12 days

Addresses critical limitations in documentation crawling, parsing, and RAG retrieval:

- **Problem:** Shallow coverage (2 URLs, 3000 char truncation), unstructured parsing, coarse RAG
- **Solution:** Expand to 5-8 URLs with full content, implement structured HTML parsing, enhance RAG with hybrid search
- **Impact:** 40-60% improvement in contract extraction accuracy, 70% improvement in GitHub Issue relevance

**Key Deliverables:**
1. Enhanced web crawler with URL filtering and full content extraction
2. Structured document parser for API constraint extraction
3. Multi-chunk RAG with hybrid semantic + keyword search
4. Reference relevance validator for GitHub Issues

**File Locations:**
- Plan: `.omc/plans/ai-db-qc-documentation-enhancement.md`
- Key Files to Modify:
  - `src/agents/agent0_env_recon.py` (lines 47, 64-81)
  - `src/agents/agent1_contract_analyst.py` (lines 70-100)
  - `src/knowledge_base.py` (complete rewrite)
  - `src/agents/agent6_verifier.py` (lines 64-72)

**Quick Start:**
```bash
# Review the plan
cat .omc/plans/ai-db-qc-documentation-enhancement.md

# Check open questions
cat .omc/plans/open-questions.md

# When ready to implement (via /oh-my-claudecode:start-work)
/oh-my-claudecode:start-work ai-db-qc-documentation-enhancement
```

---

## Open Questions

See [open-questions.md](./open-questions.md) for unresolved decisions that need user input before implementation.

**Current Questions:**
1. Token budget strategy (100K vs. 150K)
2. Embedding model selection (general vs. domain-specific)
3. Documentation caching strategy
4. Rate limiting configuration
5. Reference validation threshold (0.65)
6. Multi-version documentation handling
7. HTML structure variation handling

---

## Plan Templates

When creating new plans, follow this structure:

1. **Executive Summary** - What and why
2. **Problem Analysis** - Current limitations with file locations
3. **Improvement Objectives** - Goals with success metrics
4. **Implementation Plan** - Phased approach with code snippets
5. **Risk Assessment** - Mitigation strategies
6. **Verification Steps** - Testing and deployment
7. **Open Questions** - Decisions needed

---

## Usage Workflow

1. **Planning Phase** (Planner Agent)
   - Analyze codebase
   - Create detailed plan
   - Document open questions
   - Get user approval

2. **Implementation Phase** (Executor Agent)
   - Execute plan steps
   - Write tests
   - Verify acceptance criteria

3. **Review Phase** (Code Reviewer)
   - Review code changes
   - Validate against requirements
   - Suggest improvements

4. **Deployment Phase**
   - Merge to main branch
   - Monitor metrics
   - Iterate based on feedback

---

## Metrics Dashboard

Track plan effectiveness:

| Plan | Status | Effort | Impact | Risk |
|------|--------|--------|--------|------|
| DOC-ENHANCE-001 | Draft | 10-12d | High | Medium |

---

**Last Updated:** 2026-04-01
