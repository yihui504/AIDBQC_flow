"""
AI-DB-QC 实时进度监控面板
显示当前测试运行的实时状态
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_latest_progress():
    """获取最新的运行进度"""
    runs_dir = Path(".trae/runs")

    if not runs_dir.exists():
        return None

    # 获取最新的运行目录
    run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()],
                       key=lambda x: x.stat().st_mtime, reverse=True)

    if not run_dirs:
        return None

    latest_run = run_dirs[0]
    state_file = latest_run / "state.json"

    if not state_file.exists():
        return None

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state
    except:
        return None

def display_progress():
    """显示进度面板"""
    print("\n" + "="*70)
    print(" 🤖 AI-DB-QC 实时测试进度监控 ".center(70))
    print("="*70)

    state = get_latest_progress()

    if not state:
        print("⚠️  未找到运行状态，请确保 main.py 正在运行")
        return

    # 基本信息
    print(f"\n📌 运行信息")
    print(f"   Run ID: {state.get('run_id', 'N/A')}")
    print(f"   目标数据库: {state.get('target_db_input', 'N/A')}")
    print(f"   业务场景: {state.get('business_scenario', 'N/A')[:50]}...")

    # 迭代进度
    max_iter = state.get('max_iterations', 50)
    current_iter = state.get('iteration_count', 0)
    progress_pct = (current_iter / max_iter) * 100

    print(f"\n🔄 迭代进度")
    print(f"   当前迭代: {current_iter} / {max_iter}")
    print(f"   完成度: {progress_pct:.1f}%")

    # 进度条
    bar_length = 40
    filled = int(bar_length * progress_pct / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"   [{bar}]")

    # Token 使用
    max_tokens = state.get('max_token_budget', 100000)
    used_tokens = state.get('total_tokens_used', 0)
    token_pct = (used_tokens / max_tokens) * 100

    print(f"\n💰 Token 使用")
    print(f"   已使用: {used_tokens:,} / {max_tokens:,}")
    print(f"   使用率: {token_pct:.1f}%")

    # 测试结果
    test_cases = state.get('current_test_cases', [])
    execution_results = state.get('execution_results', [])
    oracle_results = state.get('oracle_results', [])
    defect_reports = state.get('defect_reports', [])

    print(f"\n📊 测试统计")
    print(f"   本轮测试用例: {len(test_cases)}")
    print(f"   执行结果: {len(execution_results)}")
    print(f"   预言机验证: {len(oracle_results)}")
    print(f"   发现缺陷: {len(defect_reports)}")

    # 成功率
    if execution_results:
        success_count = sum(1 for r in execution_results if r.get('success', False))
        success_rate = (success_count / len(execution_results)) * 100
        print(f"   测试成功率: {success_rate:.1f}%")

    if oracle_results:
        passed_count = sum(1 for r in oracle_results if r.get('passed', False))
        pass_rate = (passed_count / len(oracle_results)) * 100
        print(f"   预言机通过率: {pass_rate:.1f}%")

    # 缺陷类型分布
    if defect_reports:
        print(f"\n🐛 缺陷分布")
        bug_types = {}
        for d in defect_reports:
            bug_type = d.get('bug_type', 'Unknown')
            bug_types[bug_type] = bug_types.get(bug_type, 0) + 1

        for bug_type, count in sorted(bug_types.items()):
            print(f"   {bug_type}: {count}")

    print("\n" + "="*70)
    print(f"📅 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

def watch_progress(interval_seconds=30):
    """持续监控进度"""
    try:
        while True:
            display_progress()
            print(f"⏰ {interval_seconds}秒后刷新... (Ctrl+C 退出)")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n👋 监控已停止")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        print("启动持续监控模式...")
        watch_progress()
    else:
        display_progress()
