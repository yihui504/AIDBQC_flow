#!/usr/bin/env python3
"""
Regenerate GitHub Issues for run_5af0cc02 defects using fixed agent6 logic.
This script loads the saved state and generates Issues for each pending defect,
bypassing the 400 Bad Request caused by oversized docs_context (6.6MB).

The fix: _generate_issue_for_defect now uses _get_relevant_docs_for_defect()
to intelligently truncate docs to ~8000 chars per defect, avoiding API overflow.
"""

import sys
import os
import io
import gzip
import json
import time

# Add project root to path (parent of scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding for Chinese/unicode characters in error messages
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Force offline mode for HuggingFace/SentenceTransformer (model cached locally)
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from src.state import WorkflowState, DefectReport, DatabaseConfig, Contract
from src.agents.agent6_verifier import DefectVerifierAgent


def main():
    RUN_ID = "run_5af0cc02"
    STATE_PATH = os.path.join(".trae", "runs", RUN_ID, "state.json.gz")
    RAW_DOCS_PATH = os.path.join(".trae", "runs", RUN_ID, "raw_docs.json")
    OUTPUT_DIR = os.path.join(".trae", "runs", RUN_ID)

    print(f"=== Issue Regeneration for {RUN_ID} ===\n")

    # ============================================================
    # Step 1: Load state from compressed JSON
    # ============================================================
    print("[1/5] Loading state from", STATE_PATH)
    with gzip.open(STATE_PATH, "rt", encoding="utf-8") as f:
        state_data = json.load(f)

    # Reconstruct WorkflowState from dict (Pydantic handles validation)
    state = WorkflowState(**state_data)
    print(f"      Run ID: {state.run_id}")
    print(f"      Iterations: {state.iteration_count}")
    print(f"      DB: {state.db_config.db_name if state.db_config else 'N/A'} "
          f"{state.db_config.version if state.db_config else ''}")

    defects_raw = state_data.get("defect_reports", [])
    print(f"      Found {len(defects_raw)} defects in state\n")

    # ============================================================
    # Step 2: Load full docs context (may be truncated in state)
    # ============================================================
    print("[2/5] Loading documentation context...")
    full_docs_context = ""
    if state.db_config and state.db_config.docs_context:
        full_docs_context = state.db_config.docs_context

    # If docs were truncated, try loading from raw_docs.json snapshot
    if "<TRUNCATED" in full_docs_context or len(full_docs_context) < 1000:
        if os.path.exists(RAW_DOCS_PATH):
            try:
                with open(RAW_DOCS_PATH, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)
                full_docs_context = doc_data.get("full_docs", full_docs_context)
                print(f"      Loaded full docs from raw_docs.json ({len(full_docs_context):,} chars)")
            except Exception as e:
                print(f"      Warning: Failed to load raw_docs.json: {e}")
        else:
            print("      Warning: raw_docs.json not found, using state docs")

    print(f"      Docs context size: {len(full_docs_context):,} chars\n")

    # ============================================================
    # Step 3: Initialize DefectVerifierAgent
    # ============================================================
    print("[3/5] Initializing DefectVerifierAgent...")
    agent = DefectVerifierAgent()

    # Parse full docs into URL->content map and store on agent instance
    # This is what execute() does at line 728-729 of agent6_verifier.py
    docs_map = agent._parse_docs_context(full_docs_context)
    agent._docs_map = docs_map
    print(f"      Agent initialized successfully")
    print(f"      Docs map entries: {len(docs_map)}\n")

    # Build environment context (same format as execute() line 720-724)
    env_context = {
        "db_version": f"{state.db_config.db_name} {state.db_config.version}" if state.db_config else "Unknown",
        "docs_context": "(see target_doc and validated_refs for evidence)",
        "vector_config": str(state.contracts.l1_api) if state.contracts else "Unknown",
    }

    # ============================================================
    # Step 4: Generate issues for each defect
    # ============================================================
    print("[4/5] Generating GitHub Issues for each defect...")
    results = {"success": [], "failed": [], "errors": []}
    total_tokens = 0

    for i, defect_dict in enumerate(defects_raw):
        case_id = defect_dict.get("case_id", f"unknown_{i}")
        bug_type = defect_dict.get("bug_type", "Unknown")
        print(f"\n      [{i+1}/{len(defects_raw)}] {case_id} ({bug_type})", end="", flush=True)

        try:
            # Reconstruct DefectReport Pydantic model from dict
            defect = DefectReport(**defect_dict)

            # Determine target_doc from source_url (same logic as execute() line 767)
            target_doc = None
            if defect.source_url and docs_map:
                target_doc = docs_map.get(defect.source_url)
                if target_doc:
                    print(f"\n            Target doc: {defect.source_url[:60]}...", end="", flush=True)

            print(f"\n            Generating...", end=" ", flush=True)
            start_time = time.time()

            # Call the core issue generation method
            # Signature: _generate_issue_for_defect(self, defect, env_context, target_doc) -> Tuple[GitHubIssue|None, int]
            issue, tokens_used = agent._generate_issue_for_defect(
                defect=defect,
                env_context=env_context,
                target_doc=target_doc,
            )

            elapsed = time.time() - start_time
            total_tokens += tokens_used

            if issue is None:
                raise ValueError("LLM returned None for this defect")

            # Inject real vectors into the generated issue content (fix: MRE was using placeholder vectors)
            if hasattr(agent, '_inject_real_vectors') and hasattr(agent, '_extract_mre_code'):
                try:
                    mre = agent._extract_mre_code(issue.body_markdown)
                    if mre:
                        original_len = len(mre)
                        mre_injected = agent._inject_real_vectors(mre, defect)
                        if len(mre_injected) != original_len or '0.' not in str([x for x in mre_injected.split('\n') if 'search_vector' in x or 'query_vector' in x][:1]):
                            # Replace MRE in issue_content (simple string replacement of ```python...``` block)
                            import re
                            python_block_pattern = re.compile(r'```python\n(.*?)\n```', re.DOTALL)
                            match = python_block_pattern.search(issue.body_markdown)
                            if match:
                                issue.body_markdown = issue.body_markdown[:match.start(1)] + mre_injected + issue.body_markdown[match.end(1):]
                                print(f"\n            Vector injection applied ({original_len} -> {len(mre_injected)} chars)", end="", flush=True)
                except Exception as e:
                    print(f"\n            Vector injection skipped: {e}", end="", flush=True)

            # Write Issue markdown file (same format as execute() line 789-793)
            output_path = os.path.join(OUTPUT_DIR, f"GitHub_Issue_{case_id}.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {issue.title}\n\n")
                f.write(issue.body_markdown)

            results["success"].append({
                "case_id": case_id,
                "bug_type": bug_type,
                "output_file": output_path,
                "title": issue.title,
                "size_bytes": len(issue.body_markdown),
                "tokens_used": tokens_used,
                "elapsed_sec": round(elapsed, 1),
            })
            print(f"OK ({len(issue.body_markdown):,} chars, {tokens_used} tokens, {elapsed:.1f}s)")

        except Exception as e:
            # Classify error type for clearer reporting
            error_type = type(e).__name__
            error_detail = str(e)[:300]

            # Detect specific API errors
            is_rate_limit = "429" in error_detail or "RateLimitError" in error_type
            is_balance_error = any(kw in error_detail for kw in ["余额", "balance", "充值", "top.up", "resource.pack"])
            is_api_error = "openai" in str(type(e).__module__).lower() or "API" in error_type

            if is_rate_limit and is_balance_error:
                error_msg = f"API_RATE_LIMIT (429): ZhipuAI account balance insufficient. Please recharge at https://open.bigmodel.cn/"
            elif is_rate_limit:
                error_msg = f"API_RATE_LIMIT (429): {error_detail[:200]}"
            elif is_api_error:
                error_msg = f"API_ERROR ({error_type}): {error_detail[:200]}"
            else:
                error_msg = f"{error_type}: {error_detail}"

            results["failed"].append({"case_id": case_id, "error": error_msg})
            results["errors"].append(error_msg)
            print(f"\n            FAIL: {error_msg}")

            # If it's a balance/rate limit error, no point continuing - all subsequent calls will fail too
            if is_rate_limit and is_balance_error:
                print(f"\n\n!!! STOPPING: API account balance exhausted. Cannot generate more issues.")
                print(f"!!! Please recharge your ZhipuAI account and re-run this script.")
                break

        # Small delay between LLM requests to avoid rate limiting
        if i < len(defects_raw) - 1:
            time.sleep(2)

    # ============================================================
    # Step 5: Summary
    # ============================================================
    print(f"\n\n[5/5] === SUMMARY ===")
    print(f"  Total defects processed: {len(defects_raw)}")
    print(f"  Success: {len(results['success'])}/{len(defects_raw)}")
    print(f"  Failed:  {len(results['failed'])}/{len(defects_raw)}")
    print(f"  Total tokens used: {total_tokens:,}")

    if results["success"]:
        total_size = sum(r["size_bytes"] for r in results["success"])
        avg_size = total_size // len(results["success"]) if results["success"] else 0
        total_elapsed = sum(r["elapsed_sec"] for r in results["success"])
        print(f"  Total output: {total_size:,} bytes ({total_size // 1024} KB)")
        print(f"  Avg size per issue: {avg_size:,} bytes ({avg_size // 1024} KB)")
        print(f"  Total generation time: {total_elapsed:.1f}s")
        print(f"\n  Generated files:")
        for r in results["success"]:
            print(f"    [OK] {r['output_file']}")
            print(f"         Title: {r['title'][:80]}")
            print(f"         Size: {r['size_bytes']} bytes | Tokens: {r['tokens_used']} | Time: {r['elapsed_sec']}s")

    if results["errors"]:
        print(f"\n  Errors:")
        for err in results["errors"]:
            print(f"    - {err}")

    # Return results for potential programmatic use
    return results


if __name__ == "__main__":
    main()
