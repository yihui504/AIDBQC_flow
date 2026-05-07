import os
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PerformanceSnapshot:
    timestamp: str
    memory_mb: float
    cpu_percent: float
    node_name: str = ""

class PerformanceMonitor:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.snapshots: List[PerformanceSnapshot] = []
        self._start_time: Optional[float] = None
        self._psutil = None
        
        if self.enabled:
            try:
                import psutil
                self._psutil = psutil
                logger.info("[PerformanceMonitor] psutil loaded successfully")
            except ImportError:
                logger.warning("[PerformanceMonitor] psutil not available, monitoring disabled")
                self.enabled = False

    def start(self) -> None:
        if not self.enabled:
            return
        self._start_time = time.time()
        self.snapshots = []
        logger.info("[PerformanceMonitor] Monitoring started")

    def snapshot(self, node_name: str = "") -> Optional[PerformanceSnapshot]:
        if not self.enabled or not self._psutil:
            return None

        try:
            process = self._psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)
            
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow().isoformat(),
                memory_mb=round(memory_mb, 2),
                cpu_percent=round(cpu_percent, 2),
                node_name=node_name
            )
            
            self.snapshots.append(snapshot)
            
            if node_name:
                logger.info(f"[PerformanceMonitor] Node '{node_name}': Memory={memory_mb:.1f}MB, CPU={cpu_percent:.1f}%")
            
            return snapshot
        except Exception as e:
            logger.warning(f"[PerformanceMonitor] Failed to capture snapshot: {e}")
            return None

    def get_summary(self) -> Dict[str, Any]:
        if not self.snapshots:
            return {"enabled": self.enabled, "snapshots": 0}

        memory_values = [s.memory_mb for s in self.snapshots]
        cpu_values = [s.cpu_percent for s in self.snapshots]

        return {
            "enabled": self.enabled,
            "snapshots": len(self.snapshots),
            "memory": {
                "min_mb": round(min(memory_values), 2),
                "max_mb": round(max(memory_values), 2),
                "avg_mb": round(sum(memory_values) / len(memory_values), 2),
                "current_mb": round(memory_values[-1], 2) if memory_values else 0
            },
            "cpu": {
                "min_percent": round(min(cpu_values), 2),
                "max_percent": round(max(cpu_values), 2),
                "avg_percent": round(sum(cpu_values) / len(cpu_values), 2),
                "current_percent": round(cpu_values[-1], 2) if cpu_values else 0
            },
            "elapsed_seconds": round(time.time() - self._start_time, 2) if self._start_time else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        summary = self.get_summary()
        summary["snapshot_details"] = [
            {
                "timestamp": s.timestamp,
                "memory_mb": s.memory_mb,
                "cpu_percent": s.cpu_percent,
                "node_name": s.node_name
            }
            for s in self.snapshots[-10:]
        ]
        return summary

performance_monitor = PerformanceMonitor()
