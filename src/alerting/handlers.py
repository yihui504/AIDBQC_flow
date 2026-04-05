"""
Alert Handlers for AI-DB-QC

Provides additional alert handlers for various notification channels.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from src.alerting.alert_manager import Alert, AlertHandler, AlertSeverity


# ============================================================================
# Configuration Models
# ============================================================================

class EmailConfig(BaseModel):
    """Email handler configuration."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: List[str] = Field(default_factory=list)
    use_tls: bool = True


class SlackConfig(BaseModel):
    """Slack handler configuration."""
    webhook_url: str = ""
    channel: str = "#alerts"
    username: str = "AI-DB-QC Bot"
    icon_emoji: str = ":warning:"


class WebhookConfig(BaseModel):
    """Webhook handler configuration."""
    url: str = ""
    timeout: float = 5.0
    headers: Dict[str, str] = Field(default_factory=dict)


# ============================================================================
# Enhanced Handlers
# ============================================================================

class EnhancedConsoleHandler(AlertHandler):
    """Enhanced console handler with color support."""

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors

        # ANSI color codes
        self.colors = {
            AlertSeverity.INFO: "\033[94m",      # Blue
            AlertSeverity.WARNING: "\033[93m",    # Yellow
            AlertSeverity.ERROR: "\033[91m",      # Red
            AlertSeverity.CRITICAL: "\033[95m",   # Magenta
        }
        self.reset = "\033[0m"

    async def send(self, alert: Alert) -> bool:
        """Print alert to console with colors."""
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if self.use_colors:
            color = self.colors.get(alert.severity, "")
            severity_str = f"{color}[{alert.severity.value.upper()}]{self.reset}"
        else:
            severity_str = f"[{alert.severity.value.upper()}]"

        print(f"{timestamp} {severity_str} {alert.title}")

        if alert.component:
            print(f"  Component: {alert.component}")

        print(f"  Message: {alert.message}")

        if alert.run_id:
            print(f"  Run ID: {alert.run_id}")

        if alert.metadata:
            print(f"  Metadata: {alert.metadata}")

        return True


class RotatingFileHandler(AlertHandler):
    """Log file handler with rotation support."""

    def __init__(
        self,
        base_filename: str = "alerts.log",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
    ):
        self.base_filename = base_filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    async def send(self, alert: Alert) -> bool:
        """Write alert to rotating log file."""
        import json
        import os

        # Check rotation
        if os.path.exists(self.base_filename):
            size = os.path.getsize(self.base_filename)
            if size >= self.max_bytes:
                self._rotate_logs()

        try:
            with open(self.base_filename, 'a', encoding='utf-8') as f:
                log_entry = {
                    **alert.to_dict(),
                    "logged_at": datetime.now().isoformat(),
                }
                f.write(json.dumps(log_entry) + '\n')
            return True
        except Exception as e:
            print(f"Failed to write to log file: {e}")
            return False

    def _rotate_logs(self):
        """Rotate log files."""
        import os
        import shutil

        # Remove oldest backup if it exists
        oldest = f"{self.base_filename}.{self.backup_count}"
        if os.path.exists(oldest):
            os.remove(oldest)

        # Rotate existing backups
        for i in range(self.backup_count - 1, 0, -1):
            old_file = f"{self.base_filename}.{i}"
            new_file = f"{self.base_filename}.{i + 1}"
            if os.path.exists(old_file):
                shutil.move(old_file, new_file)

        # Move current log to .1
        if os.path.exists(self.base_filename):
            shutil.move(self.base_filename, f"{self.base_filename}.1")


class AggregateHandler(AlertHandler):
    """Handler that aggregates alerts before sending."""

    def __init__(
        self,
        inner_handler: AlertHandler,
        aggregate_window: int = 60,  # seconds
        max_aggregate_size: int = 100,
    ):
        self.inner_handler = inner_handler
        self.aggregate_window = aggregate_window
        self.max_aggregate_size = max_aggregate_size

        self.pending_alerts: List[Alert] = []
        self.last_send_time = datetime.now()

    async def send(self, alert: Alert) -> bool:
        """Add alert to aggregation buffer."""
        self.pending_alerts.append(alert)

        # Check if we should flush
        now = datetime.now()
        should_flush = (
            len(self.pending_alerts) >= self.max_aggregate_size or
            (now - self.last_send_time).total_seconds() >= self.aggregate_window
        )

        if should_flush:
            await self._flush()

        return True

    async def _flush(self) -> None:
        """Flush pending alerts."""
        if not self.pending_alerts:
            return

        # Create aggregated alert
        count = len(self.pending_alerts)
        severities = [a.severity for a in self.pending_alerts]
        max_severity = max(severities, key=lambda s: ["info", "warning", "error", "critical"].index(s.value))

        components = set(a.component for a in self.pending_alerts if a.component)

        aggregated = Alert(
            alert_id=f"aggregate-{datetime.now().timestamp()}",
            title=f"Aggregated {count} Alerts",
            message=f"{count} alerts from {len(components)} components: {', '.join(components)}",
            severity=max_severity,
            channel=AlertChannel.CONSOLE,
            metadata={
                "aggregate_count": count,
                "alert_ids": [a.alert_id for a in self.pending_alerts],
            }
        )

        await self.inner_handler.send(aggregated)

        self.pending_alerts.clear()
        self.last_send_time = datetime.now()

    async def flush(self) -> None:
        """Manually flush pending alerts."""
        await self._flush()


class FilterHandler(AlertHandler):
    """Handler that filters alerts based on criteria."""

    def __init__(
        self,
        inner_handler: AlertHandler,
        min_severity: AlertSeverity = AlertSeverity.INFO,
        allowed_components: Optional[List[str]] = None,
        blocked_components: Optional[List[str]] = None,
    ):
        self.inner_handler = inner_handler
        self.min_severity = min_severity
        self.allowed_components = allowed_components
        self.blocked_components = blocked_components or []

    async def send(self, alert: Alert) -> bool:
        """Send alert only if it passes filters."""
        # Check severity
        severity_order = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3,
        }

        if severity_order[alert.severity] < severity_order[self.min_severity]:
            return False

        # Check blocked components
        if alert.component in self.blocked_components:
            return False

        # Check allowed components
        if self.allowed_components and alert.component not in self.allowed_components:
            return False

        return await self.inner_handler.send(alert)


# ============================================================================
# Handler Factory
# ============================================================================

class HandlerFactory:
    """Factory for creating alert handlers."""

    @staticmethod
    def create_console_handler(use_colors: bool = True) -> EnhancedConsoleHandler:
        """Create a console handler."""
        return EnhancedConsoleHandler(use_colors=use_colors)

    @staticmethod
    def create_file_handler(
        filename: str = "alerts.log",
        rotate: bool = True,
        max_bytes: int = 10 * 1024 * 1024,
    ) -> AlertHandler:
        """Create a file handler."""
        if rotate:
            return RotatingFileHandler(
                base_filename=filename,
                max_bytes=max_bytes,
            )
        else:
            from src.alerting.alert_manager import LogFileAlertHandler
            return LogFileAlertHandler(log_file=filename)

    @staticmethod
    def create_email_handler(config: EmailConfig) -> AlertHandler:
        """Create an email handler."""
        from src.alerting.alert_manager import EmailAlertHandler
        return EmailAlertHandler(
            smtp_server=config.smtp_server,
            from_addr=config.from_addr,
            to_addrs=config.to_addrs,
        )

    @staticmethod
    def create_webhook_handler(config: WebhookConfig) -> AlertHandler:
        """Create a webhook handler."""
        from src.alerting.alert_manager import WebhookAlertHandler
        return WebhookAlertHandler(
            url=config.url,
            timeout=config.timeout,
        )

    @staticmethod
    def create_slack_handler(config: SlackConfig) -> AlertHandler:
        """Create a Slack handler."""
        from src.alerting.alert_manager import SlackAlertHandler
        return SlackAlertHandler(webhook_url=config.webhook_url)

    @staticmethod
    def create_aggregate_handler(
        inner_handler: AlertHandler,
        window_seconds: int = 60,
        max_size: int = 100,
    ) -> AggregateHandler:
        """Create an aggregate handler."""
        return AggregateHandler(
            inner_handler=inner_handler,
            aggregate_window=window_seconds,
            max_aggregate_size=max_size,
        )

    @staticmethod
    def create_filter_handler(
        inner_handler: AlertHandler,
        min_severity: AlertSeverity = AlertSeverity.INFO,
        allowed_components: Optional[List[str]] = None,
        blocked_components: Optional[List[str]] = None,
    ) -> FilterHandler:
        """Create a filter handler."""
        return FilterHandler(
            inner_handler=inner_handler,
            min_severity=min_severity,
            allowed_components=allowed_components,
            blocked_components=blocked_components,
        )
