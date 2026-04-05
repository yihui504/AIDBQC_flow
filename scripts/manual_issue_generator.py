"""
手动生成 GitHub Issue 的简化脚本

基于已知缺陷信息直接生成 GitHub Issue
"""

import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.agent_factory import get_llm
from src.rate_limiter import global_llm_rate_limiter


def generate_issue_for_case(case_id: str, bug_type: str, source_url: str, rca: str, llm) -> dict:
    """为特定测试用例生成 GitHub Issue"""
    
    print(f"\n{'='*60}")
    print(f"正在生成 Issue: {case_id}")
    print(f"Bug 类型: {bug_type}")
    print(f"{'='*60}")
    
    print("[RateLimiter] 等待速率限制器...")
    global_llm_rate_limiter.acquire()
    print("[RateLimiter] 已获得许可，开始生成...")
    
    try:
        system_prompt = """You are an AI Database Quality Assurance Oracle acting as a GitHub Issue Generator for Vector Database Bug Reports.

Generate a GitHub issue following STRICT format below.

### Output Format
Return ONLY this JSON object (no markdown, no code fences):

{
  "title": "Brief bug title (max 80 chars)",
  "body": "Full issue body with sections",
  "labels": ["bug", "vector-database"]
}

### Issue Body Sections (IN ORDER):
1. **Environment** - Version, Deployment mode, OS, SDK
2. **Steps To Reproduce** - Minimal Python MRE code
3. **Expected Behavior** - What should happen
4. **Actual Behavior** - What actually happened
5. **Evidence & Documentation** - Quotes from official docs
6. **Additional Context** - Any extra info

### MRE Requirements:
- Complete, runnable Python code
- All necessary imports included
- Shows exact operations that trigger the bug
- Self-contained (only SDK as external dep)

### Documentation References:
- Use EXACT quotes from: {source_url}
- Include source URL in each quote
- If no direct reference found, state "No direct documentation reference found"
"""

        user_prompt = f"""Generate a GitHub issue for:

Case ID: {case_id}
Bug Type: {bug_type}
Source Documentation: {source_url}
Root Cause Analysis: {rca}

Create a complete GitHub issue with a working Python MRE. Focus on the bug type and how it violates Milvus behavior or documentation."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        import re
        import json
        
        try:
            res_dict = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                try:
                    res_dict = json.loads(json_match.group(0))
                except:
                    json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                    if json_match:
                        res_dict = json.loads(json_match.group(1).strip())
            else:
                raise ValueError(f"No JSON found: {content[:200]}...")
        
        print(f"\n[SUCCESS] Issue 生成成功!")
        print(f"Title: {res_dict.get('title', 'N/A')}")
        print(f"Body 长度: {len(res_dict.get('body', ''))} 字符")
        
        return {
            "case_id": case_id,
            "success": True,
            "issue": res_dict,
        }
        
    except Exception as e:
        print(f"\n[ERROR] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "case_id": case_id,
            "success": False,
            "issue": None,
            "error": str(e),
        }


def main():
    """主函数"""
    
    print(f"\n{'='*60}")
    print("手动 GitHub Issue 生成工具")
    print(f"{'='*60}")
    
    failed_cases = [
        {
            "case_id": "TC-003-L2-CHAOTIC-SEARCH-BEFORE-LOAD",
            "bug_type": "Type-1 (Illegal Success)",
            "source_url": "https://milvus.io/docs/zh/glossary.md",
            "rca": "Illegal request was executed successfully (Bypassed L1 contract validation). The search operation was performed before the collection was loaded, which violates the operational_sequences constraint that requires 'load' before 'search'."
        },
        {
            "case_id": "TC-004-L2-SEMANTIC-ADVERSARIAL",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh/glossary.md",
            "rca": "Test for semantic oracle failure. The query 'Luxury watches' returned completely irrelevant results (noise, general, domain categories) instead of luxury watch-related content, indicating a failure in semantic retrieval."
        },
        {
            "case_id": "TC-005-L1-MIN-DIMENSION",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "The test case TC-005-L1-MIN-DIMENSION is testing similarity search at minimum dimension boundary. Expected behavior was not observed, indicating that the minimum dimension constraint may not be properly enforced or handled."
        },
        {
            "case_id": "TC-006-L3-HYBRID-FILTER-SEARCH",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh/glossary.md",
            "rca": "Hybrid filter search test failed. The filter operation should strictly reduce result sets according to metadata fields, but returned irrelevant results instead."
        },
        {
            "case_id": "TC-103-L1-MAX-DIM-SEMANTIC-SHOES",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Max dimension semantic boundary test variant failed. The system did not properly handle the maximum dimension constraint or return semantically relevant results."
        },
        {
            "case_id": "TC-104-L1-MAX-TOPK-BOUNDARY",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Max top_k boundary test failed. The system returned incorrect results or did not properly enforce the top_k limit."
        },
        {
            "case_id": "TC-105-L3-IMPOSSIBLE-FILTER",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Impossible filter test failed. The filter condition should have resulted in an empty result set, but returned results instead."
        },
        {
            "case_id": "TC-201-L1-MAX-DIM-RETRY",
            "bug_type": "Type-1 (Illegal Success)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Max dimension retry test bypassed L1 contract validation. The request exceeded the maximum dimension limit but was executed successfully instead of being rejected."
        },
        {
            "case_id": "TC-202-L1-MAX-TOPK-INTENT",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Max top_k intent test failed. The system did not correctly interpret the intent or return results that match the expected behavior for max top_k queries."
        },
        {
            "case_id": "TC-203-L2-CHAOTIC-SEARCH-NO-LOAD",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh/glossary.md",
            "rca": "Chaotic search sequence test failed. The search was performed without loading the collection, violating the operational_sequences constraint."
        },
        {
            "case_id": "TC-204-L1-INVALID-DIM-OVERFLOW",
            "bug_type": "Type-1 (Illegal Success)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Invalid dimension overflow test bypassed L1 contract validation. The request used an invalid dimension value (overflow) but was executed successfully instead of being rejected."
        },
        {
            "case_id": "TC-205-L3-IMPOSSIBLE-PRICE-FILTER",
            "bug_type": "Type-4 (Semantic Oracle)",
            "source_url": "https://milvus.io/docs/zh",
            "rca": "Impossible price filter test failed. The filter condition (impossible price range) should have resulted in an empty result set, but returned results instead."
        },
    ]
    
    print(f"\n[INFO] 准备生成 {len(failed_cases)} 个 GitHub Issue\n")
    
    llm = get_llm()
    
    success_count = 0
    failed_count = 0
    
    for i, case_info in enumerate(failed_cases, 1):
        print(f"\n进度: [{i}/{len(failed_cases)}]")
        
        result = generate_issue_for_case(
            case_info['case_id'],
            case_info['bug_type'],
            case_info['source_url'],
            case_info['rca'],
            llm
        )
        
        if result['success']:
            success_count += 1
            
            issue = result['issue']
            output_file = f".trae/runs/run_b2d70730/issue_{case_info['case_id']}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {issue['title']}\n\n")
                f.write(issue['body'])
            
            print(f"[SAVE] Issue 已保存到: {output_file}")
        else:
            failed_count += 1
            print(f"[ERROR] 失败: {result.get('error', 'Unknown')}")
        
        if i < len(failed_cases):
            print(f"\n[DELAY] 等待 15 秒以避免速率限制...")
            time.sleep(15)
    
    print(f"\n{'='*60}")
    print("生成完成报告")
    print(f"{'='*60}")
    print(f"\n总计: {len(failed_cases)} 个 Issue")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"成功率: {success_count/len(failed_cases)*100:.1f}%")
    

if __name__ == "__main__":
    main()
