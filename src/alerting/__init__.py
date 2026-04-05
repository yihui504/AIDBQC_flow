"""
Alerting Module for AI-DB-QC

This module implements a multi-channel alerting system for monitoring
test execution, defect discovery, and system health.

Author: AI-DB-QC Team
Version: 1.0.0
Date: 2026-03-30
"""

from src.alerting.alert_manager import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertChannel,
    AlertFilter,
    AlertStats,
    get_alert_manager,
    fire_alert,
    fire_defect_alert,
)
from src.alerting.handlers import (
    EnhancedConsoleHandler,
    RotatingFileHandler,
    AggregateHandler,
    FilterHandler,
    HandlerFactory,
    EmailConfig,
    SlackConfig,
    WebhookConfig,
)

__all__ = [
    # Core
    "AlertManager",
    "Alert",
    "AlertSeverity",
    "AlertChannel",
    "AlertFilter",
    "AlertStats",
    # Convenience
    "get_alert_manager",
    "fire_alert",
    "fire_defect_alert",
    # Handlers
    "EnhancedConsoleHandler",
    "RotatingFileHandler",
    "AggregateHandler",
    "FilterHandler",
    "HandlerFactory",
    # Configs
    "EmailConfig",
    "SlackConfig",
    "WebhookConfig",
]
