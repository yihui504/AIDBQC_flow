from pathlib import Path


def test_dashboard_uses_roadmap_singleton_and_phase_enum():
    app_file = Path(__file__).resolve().parents[2] / "src" / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert "from src.roadmap import Roadmap, Phase" in content
    assert "Roadmap.get_instance()" in content
    assert "for phase in Phase:" in content


def test_dashboard_reads_runs_from_trae_runs():
    app_file = Path(__file__).resolve().parents[2] / "src" / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert 'StateManager(base_dir=".trae/runs")' in content
