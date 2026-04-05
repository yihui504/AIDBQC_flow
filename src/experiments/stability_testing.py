"""
Long-term Stability Testing for AI-DB-QC

Implements 24-hour continuous run testing to verify system stability.

Deliverables:
- Stability test report
- Monitoring data

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
import psutil
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

from pydantic import BaseModel, Field


class StabilityStatus(str, Enum):
    """Status of stability testing."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""

    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "percent": self.percent,
            "available_mb": self.available_mb,
        }


@dataclass
class StabilityMetrics:
    """Metrics collected during stability testing."""

    # Test execution
    total_iterations: int = 0
    successful_iterations: int = 0
    failed_iterations: int = 0

    # Defects discovered
    defects_found: int = 0
    unique_defects: int = 0

    # Performance
    avg_iteration_time_ms: float = 0.0
    min_iteration_time_ms: float = float('inf')
    max_iteration_time_ms: float = 0.0

    # Resource usage
    memory_snapshots: List[MemorySnapshot] = field(default_factory=list)

    # Errors
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Uptime
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def uptime_hours(self) -> float:
        """Get uptime in hours."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() / 3600

    @property
    def memory_growth_rate_per_hour(self) -> float:
        """Calculate memory growth rate per hour (%)."""
        if len(self.memory_snapshots) < 2:
            return 0.0

        first = self.memory_snapshots[0]
        last = self.memory_snapshots[-1]

        hours = (last.timestamp - first.timestamp).total_seconds() / 3600
        if hours <= 0:
            return 0.0

        growth_pct = last.percent - first.percent
        return growth_pct / hours

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_iterations": self.total_iterations,
            "successful_iterations": self.successful_iterations,
            "failed_iterations": self.failed_iterations,
            "defects_found": self.defects_found,
            "unique_defects": self.unique_defects,
            "avg_iteration_time_ms": self.avg_iteration_time_ms,
            "min_iteration_time_ms": self.min_iteration_time_ms,
            "max_iteration_time_ms": self.max_iteration_time_ms,
            "memory_snapshots": [s.to_dict() for s in self.memory_snapshots],
            "errors": self.errors,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "uptime_hours": self.uptime_hours,
            "memory_growth_rate_per_hour": self.memory_growth_rate_per_hour,
        }


@dataclass
class StabilityTestResult:
    """Result of stability testing."""

    test_id: str
    status: StabilityStatus
    start_time: datetime
    end_time: datetime

    # Duration
    target_duration_hours: float
    actual_duration_hours: float

    # Metrics
    metrics: StabilityMetrics

    # Outcome
    passed: bool
    failure_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_id": self.test_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "target_duration_hours": self.target_duration_hours,
            "actual_duration_hours": self.actual_duration_hours,
            "metrics": self.metrics.to_dict(),
            "passed": self.passed,
            "failure_reason": self.failure_reason,
        }


class StabilityTester:
    """
    Runs long-term stability tests.

    Monitors system health over extended run times.
    """

    def __init__(
        self,
        target_duration_hours: float = 24.0,
        memory_check_interval_seconds: int = 60,
        snapshot_interval_seconds: int = 300,  # 5 minutes
    ):
        self.target_duration_hours = target_duration_hours
        self.memory_check_interval = memory_check_interval_seconds
        self.snapshot_interval = snapshot_interval_seconds

        # Process tracking
        self.process = psutil.Process()

        # Output
        self.output_dir = Path("experiments/stability")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_stability_test(
        self,
        test_iteration: Callable,
        iteration_delay_seconds: float = 1.0,
        stop_event: Optional[asyncio.Event] = None,
    ) -> StabilityTestResult:
        """
        Run stability test.

        Args:
            test_iteration: Async function to run each iteration
            iteration_delay_seconds: Delay between iterations
            stop_event: Optional event to stop testing early

        Returns:
            Stability test result
        """
        test_id = f"stability_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        metrics = StabilityMetrics(start_time=start_time)

        print(f"Starting stability test: {test_id}")
        print(f"Target duration: {self.target_duration_hours} hours")

        try:
            # Run test loop
            await self._test_loop(
                test_iteration,
                metrics,
                iteration_delay_seconds,
                stop_event,
            )

            # Test completed
            metrics.end_time = datetime.now()
            status = StabilityStatus.COMPLETED

        except Exception as e:
            # Test failed
            metrics.end_time = datetime.now()
            status = StabilityStatus.FAILED

            metrics.errors.append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "type": type(e).__name__,
            })

            print(f"Stability test failed: {e}")

        # Calculate result
        end_time = metrics.end_time or datetime.now()
        actual_duration = (end_time - start_time).total_seconds() / 3600

        result = StabilityTestResult(
            test_id=test_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            target_duration_hours=self.target_duration_hours,
            actual_duration_hours=actual_duration,
            metrics=metrics,
            passed=self._check_pass_criteria(metrics),
        )

        if not result.passed:
            if result.actual_duration_hours < self.target_duration_hours:
                result.failure_reason = f"Test stopped early at {actual_duration_hours:.1f} hours"
            elif metrics.memory_growth_rate_per_hour > 10:
                result.failure_reason = f"Memory growth rate too high: {metrics.memory_growth_rate_per_hour:.1f}%/h"

        # Save results
        self._save_test_result(result)

        return result

    async def _test_loop(
        self,
        test_iteration: Callable,
        metrics: StabilityMetrics,
        iteration_delay: float,
        stop_event: Optional[asyncio.Event],
    ) -> None:
        """Run the main test loop."""
        start_time = datetime.now()
        last_snapshot_time = start_time

        while True:
            # Check stop conditions
            if stop_event and stop_event.is_set():
                print("Stop event received, ending test")
                break

            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= self.target_duration_hours * 3600:
                print(f"Target duration reached: {self.target_duration_hours} hours")
                break

            # Run iteration
            iteration_start = time.time()

            try:
                await test_iteration()
                metrics.successful_iterations += 1
            except Exception as e:
                metrics.failed_iterations += 1
                metrics.errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "type": type(e).__name__,
                })

            metrics.total_iterations += 1

            # Track iteration time
            iteration_time = (time.time() - iteration_start) * 1000  # ms
            metrics.avg_iteration_time_ms = (
                (metrics.avg_iteration_time_ms * (metrics.total_iterations - 1) + iteration_time) /
                metrics.total_iterations
            )
            metrics.min_iteration_time_ms = min(
                metrics.min_iteration_time_ms,
                iteration_time
            )
            metrics.max_iteration_time_ms = max(
                metrics.max_iteration_time_ms,
                iteration_time
            )

            # Take memory snapshot
            now = datetime.now()
            if (now - last_snapshot_time).total_seconds() >= self.snapshot_interval:
                snapshot = self._take_memory_snapshot()
                metrics.memory_snapshots.append(snapshot)
                last_snapshot_time = now

                # Log status
                print(f"[{now.strftime('%H:%M:%S')}] "
                      f"Iteration {metrics.total_iterations}, "
                      f"Memory: {snapshot.percent:.1f}%, "
                      f"Uptime: {metrics.uptime_hours:.1f}h")

            # Delay before next iteration
            await asyncio.sleep(iteration_delay)

    def _take_memory_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        mem_info = self.process.memory_info()

        return MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=mem_info.rss / 1024 / 1024,  # Resident Set Size
            vms_mb=mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            percent=self.process.memory_percent(),
            available_mb=psutil.virtual_memory().available / 1024 / 1024,
        )

    def _check_pass_criteria(self, metrics: StabilityMetrics) -> bool:
        """Check if test passes acceptance criteria."""
        # Must run for target duration
        if metrics.uptime_hours < self.target_duration_hours * 0.95:
            return False

        # Memory growth rate should be reasonable
        if metrics.memory_growth_rate_per_hour > 10.0:
            return False

        # Should not have excessive failures
        if metrics.total_iterations > 0:
            failure_rate = metrics.failed_iterations / metrics.total_iterations
            if failure_rate > 0.1:  # More than 10% failures
                return False

        return True

    def _save_test_result(self, result: StabilityTestResult) -> None:
        """Save test result to file."""
        output_file = self.output_dir / f"{result.test_id}.json"

        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"Stability test results saved to {output_file}")

    def generate_monitoring_data(
        self,
        result: StabilityTestResult,
    ) -> str:
        """
        Generate monitoring data export.

        Args:
            result: Test result

        Returns:
            Path to monitoring data file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"monitoring_{result.test_id}_{timestamp}.csv"

        with open(output_file, 'w') as f:
            # CSV header
            f.write("timestamp,rss_mb,vms_mb,percent,available_mb,iteration,errors\n")

            # Data rows
            for i, snapshot in enumerate(result.metrics.memory_snapshots):
                errors_at_time = sum(
                    1 for e in result.metrics.errors
                    if snapshot.timestamp.isoformat() in e.get("timestamp", "")
                )

                f.write(f"{snapshot.timestamp.isoformat()},"
                       f"{snapshot.rss_mb:.2f},"
                       f"{snapshot.vms_mb:.2f},"
                       f"{snapshot.percent:.2f},"
                       f"{snapshot.available_mb:.2f},"
                       f"{i},"
                       f"{errors_at_time}\n")

        return str(output_file)


# ============================================================================
# Mock Test Iteration
# ============================================================================

async def mock_test_iteration() -> None:
    """Mock test iteration for stability testing."""
    # Simulate some work
    await asyncio.sleep(0.1)

    # Random small chance of failure
    import random
    if random.random() < 0.01:  # 1% failure rate
        raise RuntimeError("Simulated test failure")


# ============================================================================
# Convenience Functions
# ============================================================================

async def run_stability_test(
    duration_hours: float = 24.0,
    test_iteration: Optional[Callable] = None,
) -> StabilityTestResult:
    """
    Run stability test.

    Args:
        duration_hours: Target duration in hours
        test_iteration: Optional custom test iteration function

    Returns:
        Stability test result
    """
    tester = StabilityTester(target_duration_hours=duration_hours)

    iteration = test_iteration or mock_test_iteration

    return await tester.run_stability_test(iteration)
