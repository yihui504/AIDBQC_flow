"""
重新生成失败的 GitHub Issue

主要功能：
1. 读取 state.json 或 state.json.gz 中的失败缺陷
2. 逐个重新生成 GitHub Issue
3. 添加延迟机制避免 API 速率限制
4. 处理 Prompt 长度过长的问题
"""

import json
import gzip
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.agent_factory import get_llm
from src.state import DefectReport, WorkflowState
from src.validators.reference_validator import ReferenceValidator
from src.rate_limiter import global_llm_rate_limiter


def load_state(state_file: str) -> dict:
    """加载状态文件（支持普通 JSON 和 gzipped JSON）"""
    try:
        if state_file.endswith('.gz'):
            with gzip.open(state_file, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load state: {e}")
        return {}


def get_failed_defects(state: dict) -> list:
    defects = state.get('defects', [])
    failed_defects = []
    
    for defect in defects:
        if defect.get('verification_status') == 'failed':
            failed_defects.append(defect)
    
    return failed_defects


def simplify_rca_text(rca_text: str, max_length: int = 2000) -> str:
    if len(rca_text) <= max_length:
        return rca_text
    
    if '[Confidence:' in rca_text:
        confidence_start = rca_text.find('[Confidence:')
        confidence_end = rca_text.find(']', confidence_start)
        if confidence_end > confidence_start:
            confidence = rca_text[confidence_start:confidence_end+1]
            
            if 'The test case' in rca_text:
                main_part = rca_text[:rca_text.find('[Confidence:')]
                return f"{main_part}\n\n{confidence} [Simplified for length limit]"
    
    return rca_text[:max_length-100] + "\n\n[... RCA truncated due to length limit ...]"


def generate_single_issue(defect: dict, llm, reference_validator) -> dict:
    from src.agents.agent6_verifier import GitHubIssue
    
    print(f"\n{'='*60}")
    print(f"正在生成 Issue: {defect.get('case_id', 'Unknown')}")
    print(f"Bug 类型: {defect.get('bug_type', 'Unknown')}")
    print(f"{'='*60}")
    
    print("[RateLimiter] 等待速率限制器...")
    global_llm_rate_limiter.acquire()
    print("[RateLimiter] 已获得许可，开始生成...")
    
    try:
        env_context = {
            "database": defect.get('database', 'Unknown'),
            "operation": defect.get('operation', 'Unknown'),
            "error_message": defect.get('error_message', ''),
        }
        
        target_doc = defect.get('source_url', '')
        
        v_refs = defect.get('validated_references', [])
        if not v_refs and target_doc:
            print(f"[ReferenceValidator] 尝试验证文档: {target_doc}")
            validated_refs = reference_validator.validate_url(target_doc)
            if validated_refs:
                v_refs = validated_refs
                print(f"[ReferenceValidator] 验证成功: {len(validated_refs)} 个引用")
            else:
                print(f"[ReferenceValidator] 验证失败: {target_doc}")
        
        rca = defect.get('root_cause_analysis', '')
        if len(rca) > 2000:
            print(f"[RCA] 原始长度: {len(rca)} 字符，正在简化...")
            rca = simplify_rca_text(rca)
            print(f"[RCA] 简化后长度: {len(rca)} 字符")
        
        input_data = {
            "case_id": defect.get('case_id', ''),
            "bug_type": defect.get('bug_type', ''),
            "evidence_level": defect.get('evidence_level', ''),
            "root_cause_analysis": rca,
            "source_url": target_doc,
            "title": f"{defect.get('bug_type', '')} in {defect.get('case_id', '')}",
            "operation": defect.get('operation', ''),
            "error_message": defect.get('error_message', ''),
            "database": defect.get('database', ''),
            "validated_references": v_refs,
        }
        
        system_prompt = """You are an AI Database Quality Assurance Oracle acting as a GitHub Issue Generator for Vector Database Bug Reports.

Your task is to generate a GitHub issue in the standard format below.

### Output Format
STRICT OUTPUT FORMAT:
- Return ONLY the JSON object below
- Do NOT include any markdown code fences (like ```json or ```)
- Do NOT include any additional text, explanations, or headings
- The response must be a single JSON object exactly as shown below

{
  "title": "Brief bug title (max 80 chars)",
  "body": "Full issue body with sections",
  "labels": ["bug", "vector-database"],
  "milestone": null
}

### Issue Body Structure
The body MUST include these sections in order:
1. **Environment** - Version, Deployment mode, OS, SDK, Configurations
2. **Steps To Reproduce** - A minimal reproducible example (MRE) in Python code
3. **Expected Behavior** - What should happen according to documentation
4. **Actual Behavior** - What actually happened
5. **Evidence & Documentation** - Explicit quotes and URLs from official docs that prove this is a bug
6. **Additional Context** - Any relevant additional information

### MRE Code Requirements
- Must be complete, runnable Python code
- Must include all necessary imports
- Must show the exact operations that trigger the bug
- Must be self-contained (no external dependencies other than SDK)

### Documentation References
- Use EXACT quotes from the provided validated references
- Include the source URLs for each quote
- If no references available, state "No direct documentation reference found" """

        user_prompt = f"""Generate a GitHub issue for this bug report:

Case ID: {input_data['case_id']}
Bug Type: {input_data['bug_type']}
Evidence Level: {input_data['evidence_level']}
Root Cause Analysis: {input_data['root_cause_analysis']}
Operation: {input_data['operation']}
Error Message: {input_data['error_message']}
Database: {input_data['database']}
Source URL: {input_data['source_url']}

Validated References (Source of Truth):
{input_data['validated_references']}

Generate a complete GitHub issue following the standard format. Ensure the MRE code is complete and runnable."""

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
            json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                try:
                    res_dict = json.loads(json_match.group(1).strip())
                except:
                    raise ValueError(f"Found JSON block but failed to parse: {content[:200]}...")
            else:
                raise ValueError(f"No valid JSON found in response: {content[:200]}...")
        
        issue = GitHubIssue(**res_dict)
        
        print(f"\n[SUCCESS] Issue 生成成功!")
        print(f"Title: {issue.title}")
        print(f"Body 长度: {len(issue.body)} 字符")
        
        return {
            "case_id": defect.get('case_id'),
            "success": True,
            "issue": issue,
            "tokens_used": getattr(response, 'total_tokens', 0),
        }
        
    except Exception as e:
        print(f"\n[ERROR] 生成失败: {e}")
        return {
            "case_id": defect.get('case_id'),
            "success": False,
            "issue": None,
            "error": str(e),
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='重新生成失败的 GitHub Issue')
    parser.add_argument('--state', type=str, default='.trae/runs/run_b2d70730/state.json',
                       help='状态文件路径')
    parser.add_argument('--delay', type=float, default=8.0,
                       help='每次生成之间的延迟（秒），默认 8 秒')
    parser.add_argument('--max-length', type=int, default=2000,
                       help='RCA 文本最大长度，默认 2000 字符')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("GitHub Issue 重新生成工具")
    print(f"{'='*60}")
    print(f"\n状态文件: {args.state}")
    print(f"延迟设置: {args.delay} 秒")
    print(f"RCA 最大长度: {args.max_length} 字符\n")
    
    state = load_state(args.state)
    if not state:
        print("[ERROR] 无法加载状态文件")
        return
    
    failed_defects = get_failed_defects(state)
    
    if not failed_defects:
        print("\n[INFO] 没有找到失败的缺陷")
        return
    
    print(f"\n[INFO] 找到 {len(failed_defects)} 个失败的缺陷\n")
    
    print("\n[INIT] 初始化 LLM 和 ReferenceValidator...")
    llm = get_llm()
    reference_validator = ReferenceValidator()
    
    success_count = 0
    failed_count = 0
    total_tokens = 0
    
    for i, defect in enumerate(failed_defects, 1):
        print(f"\n进度: [{i}/{len(failed_defects)}]")
        
        result = generate_single_issue(defect, llm, reference_validator)
        
        if result['success']:
            success_count += 1
            total_tokens += result.get('tokens_used', 0)
            
            issue = result['issue']
            case_id = defect.get('case_id', 'unknown')
            output_file = f".trae/runs/run_b2d70730/issue_{case_id}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {issue.title}\n\n")
                f.write(issue.body)
            
            print(f"[SAVE] Issue 已保存到: {output_file}")
        else:
            failed_count += 1
            print(f"[ERROR] 失败原因: {result.get('error', 'Unknown')}")
        
        if i < len(failed_defects):
            print(f"\n[DELAY] 等待 {args.delay} 秒以避免速率限制...")
            time.sleep(args.delay)
    
    print(f"\n{'='*60}")
    print("生成完成报告")
    print(f"{'='*60}")
    print(f"\n总计: {len(failed_defects)} 个缺陷")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"Token 消耗: {total_tokens}")
    print(f"成功率: {success_count/len(failed_defects)*100:.1f}%")
    

if __name__ == "__main__":
    main()
