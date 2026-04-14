"""
AI-DB-QC 实时监控脚本

采集：
- CPU / 内存 / 网络吞吐
- Telemetry 日志关键事件
- 运行日志异常栈（Traceback/Exception）

并在超过阈值时触发告警并保存快照。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil


def _ensure_utf8_console() -> None:
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


TELEMETRY_EVENT_ERROR_TYPES = {"ERROR", "CIRCUIT_BREAK"}
EXCEPTION_PATTERN = re.compile(r"(Traceback \(most recent call last\)|\bException\b|\bError\b)")


@dataclass
class MonitorThresholds:
    cpu_percent: float = 85.0
    memory_percent: float = 85.0
    net_mbps: float = 100.0
    log_error_events: int = 1
    exception_hits: int = 1


@dataclass
class MonitorSample:
    timestamp: str
    cpu_percent: float
    memory_percent: float
    network_mbps: float
    log_error_events_delta: int
    exception_hits_delta: int
    telemetry_events_total: int
    latest_run_id: Optional[str]


class FileTailReader:
    """按偏移增量读取文件新增内容。"""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0

    def read_new_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(self.offset)
            lines = f.readlines()
            self.offset = f.tell()
        return lines


class RealtimeMonitor:
    def __init__(
        self,
        repo_root: Path,
        thresholds: MonitorThresholds,
        interval_seconds: int = 5,
        duration_seconds: int = 0,
        warmup_seconds: int = 30,
        consecutive_breach_threshold: int = 3,
    ):
        self.repo_root = repo_root
        self.thresholds = thresholds
        self.interval_seconds = interval_seconds
        self.duration_seconds = duration_seconds
        self.warmup_seconds = max(0, warmup_seconds)
        self.consecutive_breach_threshold = max(1, consecutive_breach_threshold)

        self.runs_dir = self.repo_root / ".trae" / "runs"
        self.monitor_dir = self.runs_dir / "monitoring"
        self.alert_dir = self.runs_dir / "monitor_alerts"
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        self.alert_dir.mkdir(parents=True, exist_ok=True)

        timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metric_file = self.monitor_dir / f"realtime_metrics_{timestamp_tag}.jsonl"

        self.telemetry_path = self.runs_dir / "telemetry.jsonl"
        self.test_log_path = self.repo_root / ".trae" / "test_run.log"
        self.telemetry_tail = FileTailReader(self.telemetry_path)
        self.test_log_tail = FileTailReader(self.test_log_path)

        self._last_net_io = psutil.net_io_counters()
        self._last_ts = time.time()
        self.telemetry_events_total = 0
        self._consecutive_breach_count = 0
        self._interrupt_alert_fired_in_streak = False

    def _latest_run_id(self) -> Optional[str]:
        if not self.runs_dir.exists():
            return None
        run_dirs = [d for d in self.runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if not run_dirs:
            return None
        latest = max(run_dirs, key=lambda d: d.stat().st_mtime)
        return latest.name

    def _collect_resource_metrics(self) -> Tuple[float, float, float]:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent

        now = time.time()
        current_net = psutil.net_io_counters()
        elapsed = max(now - self._last_ts, 1e-6)
        bytes_delta = (current_net.bytes_sent - self._last_net_io.bytes_sent) + (
            current_net.bytes_recv - self._last_net_io.bytes_recv
        )
        network_mbps = round((bytes_delta * 8) / (elapsed * 1024 * 1024), 3)

        self._last_net_io = current_net
        self._last_ts = now
        return round(cpu_percent, 2), round(memory_percent, 2), network_mbps

    def _collect_log_signals(self) -> Tuple[int, int, List[dict], List[str]]:
        telemetry_errors = 0
        telemetry_samples: List[dict] = []
        stack_lines: List[str] = []

        for line in self.telemetry_tail.read_new_lines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                self.telemetry_events_total += 1
                event_type = str(event.get("event_type", "")).upper()
                if event_type in TELEMETRY_EVENT_ERROR_TYPES:
                    telemetry_errors += 1
                    telemetry_samples.append(event)
            except json.JSONDecodeError:
                continue

        exception_hits = 0
        for line in self.test_log_tail.read_new_lines():
            if EXCEPTION_PATTERN.search(line):
                exception_hits += 1
                stack_lines.append(line.rstrip("\n"))

        # emergency_dump 兜底：若存在 error 字段，也计为异常栈信号
        latest_run = self._latest_run_id()
        if latest_run:
            emergency_dump = self.runs_dir / latest_run / "emergency_dump.json"
            if emergency_dump.exists():
                try:
                    data = json.loads(emergency_dump.read_text(encoding="utf-8"))
                    err = data.get("error")
                    if err:
                        exception_hits += 1
                        stack_lines.append(f"emergency_dump.error: {err}")
                except Exception:
                    pass

        return telemetry_errors, exception_hits, telemetry_samples[-5:], stack_lines[-10:]

    def _evaluate_thresholds(self, sample: MonitorSample) -> List[str]:
        alerts: List[str] = []
        if sample.cpu_percent >= self.thresholds.cpu_percent:
            alerts.append(
                f"CPU 超阈值: {sample.cpu_percent:.2f}% >= {self.thresholds.cpu_percent:.2f}%"
            )
        if sample.memory_percent >= self.thresholds.memory_percent:
            alerts.append(
                f"内存超阈值: {sample.memory_percent:.2f}% >= {self.thresholds.memory_percent:.2f}%"
            )
        if sample.network_mbps >= self.thresholds.net_mbps:
            alerts.append(
                f"网络吞吐超阈值: {sample.network_mbps:.3f} Mbps >= {self.thresholds.net_mbps:.3f} Mbps"
            )
        if sample.log_error_events_delta >= self.thresholds.log_error_events:
            alerts.append(
                f"日志错误事件超阈值: {sample.log_error_events_delta} >= {self.thresholds.log_error_events}"
            )
        if sample.exception_hits_delta >= self.thresholds.exception_hits:
            alerts.append(
                f"异常栈命中超阈值: {sample.exception_hits_delta} >= {self.thresholds.exception_hits}"
            )
        return alerts

    def _should_trigger_interrupt_alert(self, alerts: List[str], elapsed_seconds: float) -> Tuple[bool, str]:
        if not alerts:
            self._consecutive_breach_count = 0
            self._interrupt_alert_fired_in_streak = False
            return False, "当前周期未超阈值，连续计数已重置。"

        if elapsed_seconds < self.warmup_seconds:
            return (
                False,
                f"处于预热期（{elapsed_seconds:.1f}s/{self.warmup_seconds}s），本周期超阈值不计入连续计数。",
            )

        self._consecutive_breach_count += 1
        if (
            self._consecutive_breach_count >= self.consecutive_breach_threshold
            and not self._interrupt_alert_fired_in_streak
        ):
            self._interrupt_alert_fired_in_streak = True
            return (
                True,
                f"连续超阈值 {self._consecutive_breach_count}/{self.consecutive_breach_threshold}，触发中断告警。",
            )

        return (
            False,
            f"连续超阈值 {self._consecutive_breach_count}/{self.consecutive_breach_threshold}，暂不触发中断告警。",
        )

    def _append_metric(self, sample: MonitorSample) -> None:
        with self.metric_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(sample), ensure_ascii=False) + "\n")

    def _save_alert_snapshot(
        self,
        sample: MonitorSample,
        alerts: List[str],
        telemetry_samples: List[dict],
        stack_lines: List[str],
        elapsed_seconds: float,
        breach_count: int,
        snapshot_type: str = "interrupt_alert",
    ) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.alert_dir / f"alert_snapshot_{ts}.json"
        payload = {
            "alerts": alerts,
            "snapshot_type": snapshot_type,
            "sample": asdict(sample),
            "threshold_policy": {
                "warmup_seconds": self.warmup_seconds,
                "consecutive_breach_threshold": self.consecutive_breach_threshold,
                "current_consecutive_breach_count": breach_count,
                "elapsed_seconds": round(elapsed_seconds, 3),
            },
            "telemetry_error_samples": telemetry_samples,
            "exception_stack_samples": stack_lines,
        }
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshot_path

    def _print_sample(self, sample: MonitorSample) -> None:
        print(
            "[MONITOR] "
            f"time={sample.timestamp} "
            f"run={sample.latest_run_id or 'N/A'} "
            f"cpu={sample.cpu_percent:.2f}% "
            f"mem={sample.memory_percent:.2f}% "
            f"net={sample.network_mbps:.3f}Mbps "
            f"log_errors={sample.log_error_events_delta} "
            f"exceptions={sample.exception_hits_delta}"
        )

    def run(self) -> None:
        print("启动实时监控：CPU/内存/网络/日志/异常栈，支持阈值告警与快照落盘。")
        print(f"指标输出文件: {self.metric_file}")
        print(f"告警快照目录: {self.alert_dir}")
        print(
            "阈值策略: "
            f"warmup_seconds={self.warmup_seconds}, "
            f"consecutive_breach_threshold={self.consecutive_breach_threshold}"
        )

        start_ts = time.time()
        psutil.cpu_percent(interval=None)  # warmup

        while True:
            now_iso = datetime.utcnow().isoformat() + "Z"
            cpu_percent, memory_percent, network_mbps = self._collect_resource_metrics()
            log_error_delta, exception_delta, telemetry_samples, stack_lines = self._collect_log_signals()
            sample = MonitorSample(
                timestamp=now_iso,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                network_mbps=network_mbps,
                log_error_events_delta=log_error_delta,
                exception_hits_delta=exception_delta,
                telemetry_events_total=self.telemetry_events_total,
                latest_run_id=self._latest_run_id(),
            )
            self._append_metric(sample)
            self._print_sample(sample)

            alerts = self._evaluate_thresholds(sample)
            elapsed_seconds = time.time() - start_ts
            should_interrupt, policy_message = self._should_trigger_interrupt_alert(
                alerts=alerts,
                elapsed_seconds=elapsed_seconds,
            )
            if alerts:
                for message in alerts:
                    print(f"[WARN] {message}")
                print(f"[MONITOR] 阈值策略判定: {policy_message}")
                if should_interrupt:
                    snapshot_path = self._save_alert_snapshot(
                        sample=sample,
                        alerts=alerts,
                        telemetry_samples=telemetry_samples,
                        stack_lines=stack_lines,
                        elapsed_seconds=elapsed_seconds,
                        breach_count=self._consecutive_breach_count,
                    )
                    print(f"[ALERT][INTERRUPT] 已保存中断告警快照: {snapshot_path}")

            if self.duration_seconds > 0 and (time.time() - start_ts) >= self.duration_seconds:
                print("已达到监控时长，退出。")
                break
            time.sleep(self.interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-DB-QC 实时监控脚本（阈值告警版）")
    parser.add_argument("--interval", type=int, default=5, help="采样间隔（秒）")
    parser.add_argument("--duration", type=int, default=0, help="运行时长（秒），0 表示持续运行")
    parser.add_argument("--cpu-threshold", type=float, default=85.0, help="CPU 告警阈值（%）")
    parser.add_argument("--mem-threshold", type=float, default=85.0, help="内存告警阈值（%）")
    parser.add_argument("--net-threshold", type=float, default=100.0, help="网络吞吐告警阈值（Mbps）")
    parser.add_argument("--log-error-threshold", type=int, default=1, help="单周期日志错误事件阈值")
    parser.add_argument("--exception-threshold", type=int, default=1, help="单周期异常栈命中阈值")
    parser.add_argument("--warmup-seconds", type=int, default=30, help="预热期（秒），期间超阈值不触发中断告警")
    parser.add_argument(
        "--consecutive-breach-threshold",
        type=int,
        default=3,
        help="连续超阈值达到该次数后才触发中断告警",
    )
    return parser.parse_args()


def main() -> None:
    _ensure_utf8_console()
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    thresholds = MonitorThresholds(
        cpu_percent=args.cpu_threshold,
        memory_percent=args.mem_threshold,
        net_mbps=args.net_threshold,
        log_error_events=args.log_error_threshold,
        exception_hits=args.exception_threshold,
    )
    monitor = RealtimeMonitor(
        repo_root=repo_root,
        thresholds=thresholds,
        interval_seconds=max(1, args.interval),
        duration_seconds=max(0, args.duration),
        warmup_seconds=max(0, args.warmup_seconds),
        consecutive_breach_threshold=max(1, args.consecutive_breach_threshold),
    )
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("收到中断信号，监控停止。")


if __name__ == "__main__":
    main()
