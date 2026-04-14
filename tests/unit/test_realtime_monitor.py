import json
from pathlib import Path

from scripts.realtime_monitor import MonitorSample, MonitorThresholds, RealtimeMonitor


def test_threshold_evaluation_triggers_expected_alerts(tmp_path: Path):
    monitor = RealtimeMonitor(
        repo_root=tmp_path,
        thresholds=MonitorThresholds(
            cpu_percent=80,
            memory_percent=80,
            net_mbps=10,
            log_error_events=1,
            exception_hits=1,
        ),
        interval_seconds=1,
        duration_seconds=1,
    )
    sample = MonitorSample(
        timestamp="2026-01-01T00:00:00Z",
        cpu_percent=90.0,
        memory_percent=88.0,
        network_mbps=12.0,
        log_error_events_delta=2,
        exception_hits_delta=1,
        telemetry_events_total=20,
        latest_run_id="run_abc12345",
    )
    alerts = monitor._evaluate_thresholds(sample)
    assert len(alerts) == 5
    assert any("CPU" in x for x in alerts)
    assert any("内存" in x for x in alerts)
    assert any("网络吞吐" in x for x in alerts)
    assert any("日志错误事件" in x for x in alerts)
    assert any("异常栈命中" in x for x in alerts)


def test_collect_log_signals_from_telemetry_and_test_log(tmp_path: Path):
    monitor = RealtimeMonitor(
        repo_root=tmp_path,
        thresholds=MonitorThresholds(),
        interval_seconds=1,
        duration_seconds=1,
    )

    telemetry_file = tmp_path / ".trae" / "runs" / "telemetry.jsonl"
    telemetry_file.parent.mkdir(parents=True, exist_ok=True)
    telemetry_file.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "START", "node_name": "pipeline"}),
                json.dumps({"event_type": "ERROR", "node_name": "agent3_executor"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    test_log_file = tmp_path / ".trae" / "test_run.log"
    test_log_file.parent.mkdir(parents=True, exist_ok=True)
    test_log_file.write_text(
        "normal line\nTraceback (most recent call last):\nRuntimeError: boom\n",
        encoding="utf-8",
    )

    log_errors, exception_hits, telemetry_samples, stack_lines = monitor._collect_log_signals()
    assert log_errors == 1
    assert exception_hits >= 1
    assert len(telemetry_samples) == 1
    assert any("Traceback" in line for line in stack_lines)


def test_interrupt_alert_requires_consecutive_breach(tmp_path: Path):
    monitor = RealtimeMonitor(
        repo_root=tmp_path,
        thresholds=MonitorThresholds(),
        interval_seconds=1,
        duration_seconds=1,
        warmup_seconds=0,
        consecutive_breach_threshold=2,
    )

    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["CPU 超阈值"], elapsed_seconds=1
    )
    assert not should_interrupt
    assert "1/2" in message

    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["CPU 超阈值"], elapsed_seconds=2
    )
    assert should_interrupt
    assert "2/2" in message

    # 同一轮连续超阈值区间不重复触发中断告警
    should_interrupt, _ = monitor._should_trigger_interrupt_alert(
        alerts=["CPU 超阈值"], elapsed_seconds=3
    )
    assert not should_interrupt

    # 一旦恢复到阈值内，连续计数重置
    should_interrupt, _ = monitor._should_trigger_interrupt_alert(alerts=[], elapsed_seconds=4)
    assert not should_interrupt
    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["CPU 超阈值"], elapsed_seconds=5
    )
    assert not should_interrupt
    assert "1/2" in message


def test_warmup_seconds_blocks_consecutive_counting(tmp_path: Path):
    monitor = RealtimeMonitor(
        repo_root=tmp_path,
        thresholds=MonitorThresholds(),
        interval_seconds=1,
        duration_seconds=1,
        warmup_seconds=10,
        consecutive_breach_threshold=2,
    )

    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["网络吞吐超阈值"], elapsed_seconds=3
    )
    assert not should_interrupt
    assert "预热期" in message
    assert monitor._consecutive_breach_count == 0

    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["网络吞吐超阈值"], elapsed_seconds=11
    )
    assert not should_interrupt
    assert "1/2" in message

    should_interrupt, message = monitor._should_trigger_interrupt_alert(
        alerts=["网络吞吐超阈值"], elapsed_seconds=12
    )
    assert should_interrupt
    assert "2/2" in message
