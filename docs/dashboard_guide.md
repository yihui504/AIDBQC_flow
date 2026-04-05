# AI-DB-QC Dashboard Guide

## Overview

The AI-DB-QC Dashboard is a real-time monitoring interface built with Streamlit that provides visibility into test execution, defect discovery, and system performance.

## Features

### Real-time Monitoring
- **Auto-refresh**: Configurable refresh interval (1-30 seconds)
- **Live updates**: Automatic data updates without manual refresh
- **Multi-run support**: Compare up to 3 runs side-by-side

### Key Metrics
- **Test execution status**: Track test progress in real-time
- **Defect discovery**: Monitor bug findings by type
- **Performance metrics**: CPU, memory, response time tracking
- **Roadmap progress**: Visual task completion status

### Visualization
- **Progress bars**: Phase and task completion
- **Comparison charts**: Side-by-side run analysis
- **Bug type distribution**: Pie charts of defect types
- **Performance graphs**: Resource usage over time

## Installation

### Install Requirements

```bash
pip install -r requirements-dashboard.txt
```

### Required Dependencies
- `streamlit>=1.28.0` - Dashboard framework
- `plotly>=5.18.0` - Interactive charts
- `pandas>=2.0.0` - Data manipulation

## Usage

### Start the Dashboard

```bash
streamlit run src/dashboard/app.py
```

The dashboard will open at `http://localhost:8501`

### Navigation

#### Sidebar (Control Panel)
- **Auto-refresh**: Toggle automatic data refresh
- **Refresh interval**: Set refresh frequency (1-30 seconds)
- **Run selection**: Choose runs to analyze (max 3)

#### Tabs

**📊 Overview (概览)**
- System-wide metrics
- Phase progress
- Latest run status

**🔍 Run Comparison (运行对比)**
- Side-by-side run metrics
- Visual comparison charts
- Performance differences

**🐛 Defect Analysis (缺陷分析)**
- Defect list with details
- Bug type distribution
- Database breakdown

**⚡ Performance (性能指标)**
- Tests per second
- Response time
- Memory usage
- CPU utilization

## Data Sources

The dashboard reads from:
- `runs/*/state.json` - Run state files
- `src/roadmap.py` - Task progress data

## Customization

### Modify Refresh Interval
Edit the default in `src/dashboard/app.py`:
```python
st.session_state.refresh_interval = 5  # seconds
```

### Add Custom Metrics
Extend the `DataManager` class:
```python
def get_custom_metric(self, run_id: str) -> float:
    # Your custom metric calculation
    return 0.0
```

### Change Color Scheme
Edit the CSS in the `<style>` block in `app.py`.

## Performance

### Target Metrics
- **Update latency**: < 5 seconds
- **Multi-run support**: 3 concurrent runs
- **Response time**: < 500ms

### Optimization Tips
1. Limit auto-refresh frequency for large datasets
2. Use run filtering to reduce data volume
3. Close unused browser tabs

## Troubleshooting

### Dashboard Not Loading
- Check Streamlit installation: `streamlit --version`
- Verify Python version: `python --version` (requires 3.8+)
- Check port availability: 8501

### No Data Displayed
- Ensure run directories exist: `runs/*/state.json`
- Check file permissions
- Verify state file format

### Slow Performance
- Increase refresh interval
- Reduce number of selected runs
- Close other applications

## Development

### Run in Development Mode
```bash
streamlit run src/dashboard/app.py --logger.level=debug
```

### File Watch Mode
```bash
streamlit run src/dashboard/app.py --server.runOnSave=true
```

### Access from Network
```bash
streamlit run src/dashboard/app.py --server.address=0.0.0.0
```

## Security

### Authentication (Future)
Add to `app.py`:
```python
import streamlit_authenticator as stauth

# Configure authentication
authenticator = stauth.Authenticate(...)
```

### HTTPS (Production)
```bash
streamlit run src/dashboard/app.py --server.enableCORS=true --server.enableXsrfProtection=true
```

## Support

For issues or questions:
- Check logs: `streamlit run src/dashboard/app.py --logger.level=debug`
- Review error messages in the browser console
- Verify data file integrity
