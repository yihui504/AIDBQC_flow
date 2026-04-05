"""
Alert Manager for AI-DB-QC

Implements a multi-channel alerting system for monitoring test execution,
defect discovery, and system health.

Features:
- Multiple notification channels (console, email, webhook, Slack)
- Configurable alert severity levels
- Alert deduplication and rate limiting
- Alert history tracking

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import json

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert notification channels."""

    CONSOLE = "console"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    LOG_FILE = "log_file"


@dataclass
class Alert:
    """An alert notification."""

    alert_id: str
    title: str
    message: str
    severity: AlertSeverity
    channel: AlertChannel
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    run_id: str = ""
    component: str = ""
    defect_id: str = ""

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    sent: bool = False
    send_count: int = 0
    last_sent_at: Optional[datetime] = None

    def __hash__(self) -> int:
        """Hash for deduplication."""
        content = f"{self.title}:{self.message}:{self.component}:{self.severity.value}"
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "channel": self.channel.value,
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "component": self.component,
            "defect_id": self.defect_id,
            "metadata": self.metadata,
            "sent": self.sent,
            "send_count": self.send_count,
        }


class AlertFilter(BaseModel):
    """Filter criteria for alerts."""

    min_severity: Optional[AlertSeverity] = None
    components: List[str] = Field(default_factory=list)
    channels: List[AlertChannel] = Field(default_factory=list)
    time_window: Optional[int] = Field(default=None, description="Minutes")


class AlertStats(BaseModel):
    """Alert statistics."""

    total_alerts: int = 0
    alerts_by_severity: Dict[str, int] = Field(default_factory=dict)
    alerts_by_channel: Dict[str, int] = Field(default_factory=dict)
    alerts_by_component: Dict[str, int] = Field(default_factory=dict)
    recent_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class AlertHandler:
    """Base class for alert handlers."""

    async def send(self, alert: Alert) -> bool:
        """
        Send an alert.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        raise NotImplementedError


class ConsoleAlertHandler(AlertHandler):
    """Console output alert handler."""

    async def send(self, alert: Alert) -> bool:
        """Print alert to console."""
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        severity_icon = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }.get(alert.severity, "📋")

        print(f"[{timestamp}] {severity_icon} [{alert.severity.value.upper()}] {alert.title}")
        print(f"  Component: {alert.component or 'N/A'}")
        print(f"  Message: {alert.message}")
        if alert.run_id:
            print(f"  Run ID: {alert.run_id}")
        print()

        return True


class LogFileAlertHandler(AlertHandler):
    """Log file alert handler."""

    def __init__(self, log_file: str = "alerts.log"):
        self.log_file = log_file

    async def send(self, alert: Alert) -> bool:
        """Write alert to log file."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert.to_dict()) + '\n')
            return True
        except Exception as e:
            print(f"Failed to write to log file: {e}")
            return False


class WebhookAlertHandler(AlertHandler):
    """Webhook alert handler."""

    def __init__(self, url: str, timeout: float = 5.0):
        self.url = url
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            import aiohttp

            payload = alert.to_dict()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    return response.status == 200

        except ImportError:
            print("aiohttp not installed, webhook disabled")
            return False
        except Exception as e:
            print(f"Webhook send failed: {e}")
            return False


class EmailAlertHandler(AlertHandler):
    """Email alert handler (stub implementation)."""

    def __init__(self, smtp_server: str, from_addr: str, to_addrs: List[str]):
        self.smtp_server = smtp_server
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    async def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        # Stub implementation - integrate with actual SMTP in production
        print(f"[EMAIL STUB] To: {', '.join(self.to_addrs)}")
        print(f"  Subject: [{alert.severity.value.upper()}] {alert.title}")
        print(f"  Body: {alert.message}")
        return True


class SlackAlertHandler(AlertHandler):
    """Slack alert handler (stub implementation)."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        # Stub implementation - integrate with actual Slack webhook in production
        print(f"[SLACK STUB] Channel: #alerts")
        print(f"  {alert.title}: {alert.message}")
        return True


class AlertManager:
    """
    Manages alert generation, deduplication, and delivery.

    Features:
    - Multi-channel alert delivery
    - Alert deduplication (hash-based)
    - Rate limiting per alert
    - Alert history tracking
    """

    def __init__(
        self,
        enabled_channels: List[AlertChannel] = None,
        dedup_window_minutes: int = 30,
        max_send_count: int = 3,
    ):
        self.enabled_channels = enabled_channels or [AlertChannel.CONSOLE]
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.max_send_count = max_send_count

        # Handlers
        self.handlers: Dict[AlertChannel, AlertHandler] = {}
        self._register_default_handlers()

        # Alert tracking
        self.alert_history: List[Alert] = []
        self.alert_hashes: Dict[int, datetime] = {}  # hash -> first_seen
        self.pending_alerts: List[Alert] = []

        # Statistics
        self.stats = AlertStats()

    def _register_default_handlers(self):
        """Register default alert handlers."""
        self.handlers[AlertChannel.CONSOLE] = ConsoleAlertHandler()
        self.handlers[AlertChannel.LOG_FILE] = LogFileAlertHandler()

    def register_handler(self, channel: AlertChannel, handler: AlertHandler) -> None:
        """Register a custom alert handler."""
        self.handlers[channel] = handler

    async def fire_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        channels: Optional[List[AlertChannel]] = None,
        **kwargs
    ) -> Alert:
        """
        Fire an alert.

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            channels: Channels to send to (defaults to enabled)
            **kwargs: Additional alert metadata

        Returns:
            The Alert object
        """
        channels = channels or self.enabled_channels

        for channel in channels:
            alert = Alert(
                alert_id=self._generate_alert_id(),
                title=title,
                message=message,
                severity=severity,
                channel=channel,
                **kwargs
            )

            await self._process_alert(alert)

        return alert

    async def _process_alert(self, alert: Alert) -> None:
        """Process an alert through deduplication and delivery."""
        # Update statistics
        self.stats.total_alerts += 1
        severity_key = alert.severity.value
        self.stats.alerts_by_severity[severity_key] = (
            self.stats.alerts_by_severity.get(severity_key, 0) + 1
        )

        channel_key = alert.channel.value
        self.stats.alerts_by_channel[channel_key] = (
            self.stats.alerts_by_channel.get(channel_key, 0) + 1
        )

        if alert.component:
            self.stats.alerts_by_component[alert.component] = (
                self.stats.alerts_by_component.get(alert.component, 0) + 1
            )

        # Check deduplication
        alert_hash = hash(alert)
        now = datetime.now()

        if alert_hash in self.alert_hashes:
            first_seen = self.alert_hashes[alert_hash]
            if now - first_seen < self.dedup_window:
                # Within dedup window - skip
                return

        # Record alert hash
        self.alert_hashes[alert_hash] = now

        # Check rate limiting
        if alert.send_count >= self.max_send_count:
            return

        # Send alert
        handler = self.handlers.get(alert.channel)
        if handler:
            try:
                success = await handler.send(alert)
                if success:
                    alert.sent = True
                    alert.send_count += 1
                    alert.last_sent_at = now
            except Exception as e:
                print(f"Alert send failed: {e}")

        # Store in history
        self.alert_history.append(alert)
        self.stats.recent_alerts.append(alert.to_dict())

        # Limit recent alerts
        if len(self.stats.recent_alerts) > 100:
            self.stats.recent_alerts = self.stats.recent_alerts[-100:]

        # Clean old hashes
        self._cleanup_old_hashes()

    def _generate_alert_id(self) -> str:
        """Generate a unique alert ID."""
        return f"alert-{datetime.now().timestamp()}-{len(self.alert_history)}"

    def _cleanup_old_hashes(self) -> None:
        """Remove old alert hashes outside dedup window."""
        now = datetime.now()
        expired = [
            h for h, t in self.alert_hashes.items()
            if now - t > self.dedup_window
        ]
        for h in expired:
            del self.alert_hashes[h]

    async def fire_defect_alert(
        self,
        defect_id: str,
        bug_type: str,
        title: str,
        **kwargs
    ) -> Alert:
        """
        Fire a defect discovery alert.

        Args:
            defect_id: Defect identifier
            bug_type: Type of bug (Type-1/2/3/4)
            title: Alert title
            **kwargs: Additional metadata

        Returns:
            The Alert object
        """
        severity = {
            "Type-1": AlertSeverity.CRITICAL,
            "Type-2": AlertSeverity.ERROR,
            "Type-3": AlertSeverity.WARNING,
            "Type-4": AlertSeverity.INFO,
        }.get(bug_type, AlertSeverity.INFO)

        message = f"Defect discovered: {bug_type} bug ({defect_id})"

        return await self.fire_alert(
            title=title,
            message=message,
            severity=severity,
            component="defect_discovery",
            defect_id=defect_id,
            **kwargs
        )

    async def fire_test_failure_alert(
        self,
        test_id: str,
        error_message: str,
        **kwargs
    ) -> Alert:
        """Fire a test failure alert."""
        return await self.fire_alert(
            title=f"Test Failed: {test_id}",
            message=f"Test execution failed: {error_message}",
            severity=AlertSeverity.ERROR,
            component="test_executor",
            **kwargs
        )

    async def fire_system_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        **kwargs
    ) -> Alert:
        """Fire a system alert."""
        return await self.fire_alert(
            title="System Alert",
            message=message,
            severity=severity,
            component="system",
            **kwargs
        )

    def get_alerts(
        self,
        filter: Optional[AlertFilter] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get alerts from history.

        Args:
            filter: Optional filter criteria
            limit: Maximum number of alerts to return

        Returns:
            List of alerts
        """
        alerts = self.alert_history[-limit:]

        if filter:
            if filter.min_severity:
                severity_order = {
                    AlertSeverity.INFO: 0,
                    AlertSeverity.WARNING: 1,
                    AlertSeverity.ERROR: 2,
                    AlertSeverity.CRITICAL: 3,
                }
                min_level = severity_order[filter.min_severity]
                alerts = [
                    a for a in alerts
                    if severity_order.get(a.severity, 0) >= min_level
                ]

            if filter.components:
                alerts = [a for a in alerts if a.component in filter.components]

            if filter.channels:
                alerts = [a for a in alerts if a.channel in filter.channels]

            if filter.time_window:
                cutoff = datetime.now() - timedelta(minutes=filter.time_window)
                alerts = [a for a in alerts if a.timestamp >= cutoff]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def get_statistics(self) -> AlertStats:
        """Get alert statistics."""
        return self.stats

    def clear_history(self) -> None:
        """Clear alert history."""
        self.alert_history.clear()
        self.alert_hashes.clear()
        self.stats = AlertStats()


# ============================================================================
# Convenience Functions
# ============================================================================

# Global alert manager instance
_global_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = AlertManager()
    return _global_manager


async def fire_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    **kwargs
) -> Alert:
    """Convenience function to fire an alert using the global manager."""
    manager = get_alert_manager()
    return await manager.fire_alert(title, message, severity, **kwargs)


async def fire_defect_alert(
    defect_id: str,
    bug_type: str,
    title: str,
    **kwargs
) -> Alert:
    """Convenience function to fire a defect alert."""
    manager = get_alert_manager()
    return await manager.fire_defect_alert(defect_id, bug_type, title, **kwargs)
