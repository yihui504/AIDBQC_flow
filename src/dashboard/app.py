"""
AI-DB-QC Real-time Monitoring Dashboard

Streamlit application for monitoring test execution, defect discovery,
and system metrics in real-time.

Features:
- Real-time test execution status
- Defect discovery tracking
- Performance metrics visualization
- Multi-run support and comparison
- Interactive data exploration

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state import StateManager
from src.roadmap import Roadmap, Phase
def load_run_data(runs_dir: str = ".trae/runs") -> List[Dict[str, Any]]:
    """Load run data from .trae/runs directory."""
    runs_path = Path(runs_dir)
    if not runs_path.exists():
        return []
    runs = []
    for run_dir in sorted(runs_path.iterdir()):
        if run_dir.is_dir() and run_dir.name.startswith("run_"):
            state_file = run_dir / "state.json"
            telemetry_file = run_dir / "telemetry.jsonl"
            run_info = {"run_id": run_dir.name, "path": str(run_dir)}
            if state_file.exists():
                try:
                    run_info["state"] = json.loads(state_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            if telemetry_file.exists():
                try:
                    run_info["telemetry_lines"] = sum(1 for _ in telemetry_file.open(encoding="utf-8"))
                except Exception:
                    pass
            runs.append(run_info)
    return runs


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="AI-DB-QC Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# Custom CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .status-running {
        color: #00cc00;
        font-weight: bold;
    }
    .status-completed {
        color: #1f77b4;
        font-weight: bold;
    }
    .status-failed {
        color: #ff4d4d;
        font-weight: bold;
    }
    .phase-completed {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
    .phase-in-progress {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
    .phase-pending {
        background-color: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Session State Initialization
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "runs" not in st.session_state:
        st.session_state.runs = {}
    if "current_run" not in st.session_state:
        st.session_state.current_run = None
    if "selected_run_ids" not in st.session_state:
        st.session_state.selected_run_ids = []
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = True
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 5


init_session_state()


# ============================================================================
# Data Management
# ============================================================================

class DataManager:
    """Manages dashboard data from state files."""

    def __init__(self):
        self.state_manager = StateManager(base_dir=".trae/runs")
        self.roadmap = Roadmap.get_instance()

    def get_run_data(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific run."""
        state = self.state_manager.load_state(run_id)
        if state is None:
            return None
        return state.model_dump()

    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Get all available runs."""
        runs_dir = Path(self.state_manager.base_dir)
        if not runs_dir.exists():
            return []

        runs = []
        for run_id in self.state_manager.list_runs():
            data = self.get_run_data(run_id)
            if data is not None:
                runs.append({
                    "run_id": run_id,
                    **data
                })

        return sorted(runs, key=lambda x: x.get("start_time", ""), reverse=True)

    def get_roadmap_progress(self) -> Dict[str, Any]:
        """Get roadmap progress data."""
        phases = {}
        for phase in Phase:
            phase_name = phase.value
            tasks = self.roadmap.get_tasks_by_phase(phase)

            completed = sum(1 for t in tasks if t.status.value == "completed")
            total = len(tasks)

            phases[phase_name] = {
                "completed": completed,
                "total": total,
                "progress_pct": (completed / total * 100) if total > 0 else 0,
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status.value,
                    }
                    for t in tasks
                ]
            }

        return phases


# ============================================================================
# UI Components
# ============================================================================

def render_header():
    """Render dashboard header."""
    st.markdown('<div class="main-header">🔍 AI-DB-QC 实时监控仪表板</div>', unsafe_allow_html=True)
    st.markdown("---")


def render_sidebar(data_manager: DataManager):
    """Render sidebar with controls."""
    with st.sidebar:
        st.header("⚙️ 控制面板")

        # Auto-refresh
        st.session_state.auto_refresh = st.checkbox(
            "自动刷新",
            value=st.session_state.auto_refresh,
            help="自动刷新数据"
        )

        if st.session_state.auto_refresh:
            st.session_state.refresh_interval = st.slider(
                "刷新间隔 (秒)",
                min_value=1,
                max_value=30,
                value=st.session_state.refresh_interval
            )

        st.markdown("---")

        # Run selection
        st.header("📊 运行选择")

        runs = data_manager.get_all_runs()

        if runs:
            run_ids = [r["run_id"] for r in runs]
            selected = st.multiselect(
                "选择运行 (最多3个)",
                run_ids,
                default=run_ids[:1] if run_ids else [],
                max_selections=3
            )
            st.session_state.selected_run_ids = selected
        else:
            st.info("暂无运行数据")
            st.session_state.selected_run_ids = []

        st.markdown("---")

        # Quick stats
        st.header("📈 快速统计")

        total_runs = len(runs)
        completed_runs = sum(1 for r in runs if r.get("status") == "completed")

        st.metric("总运行数", total_runs)
        st.metric("已完成", completed_runs)


def render_overview_tab(data_manager: DataManager):
    """Render overview tab with key metrics."""
    st.header("📊 系统概览")

    # Get roadmap progress
    phases = data_manager.get_roadmap_progress()

    # Phase progress cards
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Phase 进度")

        for phase_name, phase_data in phases.items():
            status_class = "phase-completed" if phase_data["progress_pct"] == 100 else \
                          "phase-in-progress" if phase_data["progress_pct"] > 0 else "phase-pending"

            st.markdown(f"""
                <div class="{status_class}">
                    <strong>{phase_name}</strong><br/>
                    {phase_data['completed']}/{phase_data['total']} 任务
                    ({phase_data['progress_pct']:.0f}%)
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("当前状态")

        runs = data_manager.get_all_runs()

        if runs:
            latest = runs[0]
            status = latest.get("status", "unknown")
            status_class = f"status-{status}"

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**最新运行**")
                st.markdown(f"<span class='{status_class}'>{status.upper()}</span>",
                          unsafe_allow_html=True)
            with col_b:
                st.markdown("**运行 ID**")
                st.code(latest["run_id"], language="text")

            if "start_time" in latest:
                start_time = datetime.fromisoformat(latest["start_time"])
                elapsed = (datetime.now() - start_time).total_seconds()
                st.metric("运行时长", f"{elapsed/60:.1f} 分钟")
        else:
            st.info("暂无运行数据")


def render_run_comparison_tab(data_manager: DataManager):
    """Render run comparison tab."""
    st.header("🔍 运行对比")

    selected = st.session_state.selected_run_ids

    if not selected:
        st.warning("请选择要对比的运行")
        return

    if len(selected) < 2:
        st.info("选择至少2个运行以进行对比")
        return

    # Get run data
    runs_data = {}
    for run_id in selected:
        data = data_manager.get_run_data(run_id)
        if data:
            runs_data[run_id] = data

    if not runs_data:
        st.error("无法加载运行数据")
        return

    # Comparison metrics
    st.subheader("关键指标对比")

    metrics = []
    for run_id, data in runs_data.items():
        metrics.append({
            "Run ID": run_id,
            "Tests Executed": data.get("tests_executed", 0),
            "Defects Found": data.get("defects_found", 0),
            "Success Rate %": data.get("success_rate", 0) * 100,
            "Duration (min)": data.get("duration_seconds", 0) / 60,
        })

    df = pd.DataFrame(metrics)
    st.dataframe(df, use_container_width=True)

    # Visualization
    st.subheader("可视化对比")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Tests Executed", "Defects Found", "Success Rate", "Duration"),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )

    run_ids = list(runs_data.keys())

    # Tests executed
    fig.add_trace(
        go.Bar(x=run_ids, y=[m["Tests Executed"] for m in metrics], name="Tests"),
        row=1, col=1
    )

    # Defects found
    fig.add_trace(
        go.Bar(x=run_ids, y=[m["Defects Found"] for m in metrics], name="Defects"),
        row=1, col=2
    )

    # Success rate
    fig.add_trace(
        go.Bar(x=run_ids, y=[m["Success Rate %"] for m in metrics], name="Success %"),
        row=2, col=1
    )

    # Duration
    fig.add_trace(
        go.Bar(x=run_ids, y=[m["Duration (min)"] for m in metrics], name="Duration"),
        row=2, col=2
    )

    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_defects_tab(data_manager: DataManager):
    """Render defects analysis tab."""
    st.header("🐛 缺陷分析")

    selected = st.session_state.selected_run_ids

    if not selected:
        st.warning("请选择要分析的运行")
        return

    # Aggregate defects from selected runs
    all_defects = []

    for run_id in selected:
        data = data_manager.get_run_data(run_id)
        if data and "defects" in data:
            for defect in data["defects"]:
                defect["run_id"] = run_id
                all_defects.append(defect)

    if not all_defects:
        st.info("选定运行中未发现缺陷")
        return

    st.metric("总缺陷数", len(all_defects))

    # Defects table
    st.subheader("缺陷列表")

    df = pd.DataFrame(all_defects)

    # Reorder and rename columns
    columns_order = ["defect_id", "bug_type", "title", "database", "run_id"]
    available_columns = [c for c in columns_order if c in df.columns]
    df_display = df[available_columns]

    st.dataframe(df_display, use_container_width=True)

    # Bug type distribution
    if "bug_type" in df.columns:
        st.subheader("Bug 类型分布")

        bug_counts = df["bug_type"].value_counts()

        fig = px.pie(
            values=bug_counts.values,
            names=bug_counts.index,
            title="Bug Type Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)


def render_performance_tab(data_manager: DataManager):
    """Render performance metrics tab."""
    st.header("⚡ 性能指标")

    selected = st.session_state.selected_run_ids

    if not selected:
        st.warning("请选择要分析的运行")
        return

    # Collect performance data
    perf_data = []

    for run_id in selected:
        data = data_manager.get_run_data(run_id)
        if data:
            perf_data.append({
                "Run ID": run_id,
                "Tests/sec": data.get("tests_per_second", 0),
                "Avg Response Time (ms)": data.get("avg_response_time_ms", 0),
                "Memory MB": data.get("memory_mb", 0),
                "CPU %": data.get("cpu_percent", 0),
            })

    if not perf_data:
        st.info("暂无性能数据")
        return

    df = pd.DataFrame(perf_data)

    # Metrics display
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_tps = df["Tests/sec"].mean()
        st.metric("平均 Tests/sec", f"{avg_tps:.2f}")

    with col2:
        avg_resp = df["Avg Response Time (ms)"].mean()
        st.metric("平均响应时间", f"{avg_resp:.1f} ms")

    with col3:
        avg_mem = df["Memory MB"].mean()
        st.metric("平均内存", f"{avg_mem:.1f} MB")

    with col4:
        avg_cpu = df["CPU %"].mean()
        st.metric("平均 CPU", f"{avg_cpu:.1f}%")

    # Performance comparison chart
    st.subheader("性能对比")

    fig = go.Figure()

    for idx, row in df.iterrows():
        fig.add_trace(go.Bar(
            name=row["Run ID"],
            x=["Tests/sec", "Response Time", "Memory", "CPU"],
            y=[row["Tests/sec"], row["Avg Response Time (ms)"],
               row["Memory MB"], row["CPU %"]],
        ))

    fig.update_layout(
        barmode='group',
        height=400,
        xaxis_title="Metric",
        yaxis_title="Value"
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# Main App
# ============================================================================

def main():
    """Main application entry point."""

    # Initialize data manager
    data_manager = DataManager()

    # Render header and sidebar
    render_header()
    render_sidebar(data_manager)

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 概览",
        "🔍 运行对比",
        "🐛 缺陷分析",
        "⚡ 性能指标"
    ])

    with tab1:
        render_overview_tab(data_manager)

    with tab2:
        render_run_comparison_tab(data_manager)

    with tab3:
        render_defects_tab(data_manager)

    with tab4:
        render_performance_tab(data_manager)

    # Auto-refresh
    if st.session_state.auto_refresh:
        time.sleep(st.session_state.refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
