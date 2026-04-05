# Open Questions

## AI-DB-QC Documentation Enhancement - 2026-04-01

- [ ] **Token Budget Strategy** - Should we implement aggressive content summarization to stay within the 100K token limit per run, or should we increase the budget? The enhanced crawling will likely extract 50K+ chars of documentation per database.
  - **Impact**: Affects LLM cost and processing time
  - **Options**: (1) Summarize before LLM, (2) Increase token budget to 150K, (3) Implement selective section extraction
  - **Why it matters**: Current budget is 100K tokens, but full documentation could exceed this

- [ ] **Embedding Model Selection** - Should we use domain-specific embedding models (e.g., CodeBERT, specialized technical models) instead of the general-purpose `all-MiniLM-L6-v2`?
  - **Impact**: Affects RAG retrieval precision for technical API documentation
  - **Options**: (1) Start with general-purpose, (2) Use CodeBERT for code/API docs, (3) Fine-tune on vector DB documentation
  - **Why it matters**: Technical terms like "HNSW", "IVF_FLAT" may not be well-represented in general embeddings

- [ ] **Documentation Caching Strategy** - Should we implement persistent caching for crawled documentation to avoid re-crawling the same database versions?
  - **Impact**: Reduces network requests and improves performance for repeated tests
  - **Options**: (1) No caching (always fresh), (2) 24-hour cache, (3) Version-based cache with 7-day TTL
  - **Why it matters**: Balances freshness vs. performance; documentation changes infrequently

- [ ] **Rate Limiting Configuration** - What rate limiting strategy should we implement for documentation sites to avoid being blocked?
  - **Impact**: Prevents IP bans from documentation providers
  - **Options**: (1) 1 request per second, (2) Exponential backoff starting at 2s, (3) Respect robots.txt
  - **Why it matters**: Aggressive crawling could trigger anti-bot protections

- [ ] **Reference Validation Threshold** - Is the proposed 0.65 similarity threshold too strict or too lenient for filtering documentation references?
  - **Impact**: Affects how many references appear in GitHub issues
  - **Options**: (1) Lower to 0.5 (more inclusive), (2) Keep at 0.65, (3) Raise to 0.75 (more exclusive)
  - **Why it matters**: Threshold determines false positive vs. false negative tradeoff

- [ ] **Multi-Database Documentation Handling** - How should we handle documentation that covers multiple database versions or migration guides?
  - **Impact**: Affects version-specific constraint extraction accuracy
  - **Options**: (1) Parse all versions, (2) Filter by version in URL, (3) Use LLM to identify version-specific sections
  - **Why it matters**: Version mismatches are a common source of false constraints

- [ ] **HTML Structure Variations** - How should we handle documentation sites with significantly different HTML structures (e.g., GitBook vs. custom docs)?
  - **Impact**: Affects structured parser's ability to extract constraints
  - **Options**: (1) Generic text extraction, (2) Multiple parser strategies, (3) LLM-based structure inference
  - **Why it matters**: Different doc sites have different layouts; one-size-fits-all may fail

---

## Notes

- All questions should be resolved before implementation begins
- Prioritize questions marked with **HIGH IMPACT**
- Document decisions in the plan's "Open Questions" section
