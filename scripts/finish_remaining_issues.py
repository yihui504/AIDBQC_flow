"""
完成剩余 GitHub Issue 生成 (TC-204 和 TC-205)
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
    print("完成剩余 GitHub Issue 生成")
    print(f"{'='*60}")
    
    remaining_cases = [
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
            "rca": "Impossible price filter test failed. The filter condition (impossible price range) should have resulted in an empty result set, but returned results instead.",
        },
    ]
    
    print(f"\n[INFO] 准备生成 {len(remaining_cases)} 个 GitHub Issue\n")
    
    llm = get_llm()
    
    success_count = 0
    failed_count = 0
    
    for i, case_info in enumerate(remaining_cases, 1):
        print(f"\n进度: [{i}/{len(remaining_cases)}]")
        
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
        
        if i < len(remaining_cases):
            print(f"\n[DELAY] 等待 15 秒以避免速率限制...")
            time.sleep(15)
    
    print(f"\n{'='*60}")
    print("生成完成报告")
    print(f"{'='*60}")
    print(f"\n总计: {len(remaining_cases)} 个 Issue")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"成功率: {success_count/len(remaining_cases)*100:.1f}%")
    

if __name__ == "__main__":
    main()
