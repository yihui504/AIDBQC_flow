# AI-DB-QC Alerting Guide

## Overview

The AI-DB-QC Alerting system provides multi-channel notifications for test execution, defect discovery, and system events.

## Features

### Multi-Channel Support
- **Console**: Real-time console output with color support
- **Log File**: Persistent logging with rotation
- **Email**: SMTP-based email notifications
- **Webhook**: HTTP webhook delivery
- **Slack**: Slack integration (via webhooks)

### Alert Management
- **Severity Levels**: INFO, WARNING, ERROR, CRITICAL
- **Deduplication**: Hash-based duplicate detection (30min window)
- **Rate Limiting**: Configurable max send count per alert
- **Filtering**: Component and severity-based filtering
- **Aggregation**: Batch alerts to reduce noise

## Quick Start

### Runtime Monitoring Script (Task4/Task5)

Use the built-in runtime monitor to collect CPU/memory/network/log/exception-stack signals and trigger interrupt alerts only when threshold breaches are consecutive:

```bash
python scripts/realtime_monitor.py --interval 5 --cpu-threshold 85 --mem-threshold 85 --net-threshold 100 --warmup-seconds 30 --consecutive-breach-threshold 3
```

- Metric stream: `.trae/runs/monitoring/realtime_metrics_*.jsonl`
- Alert snapshots (interrupt alerts): `.trae/runs/monitor_alerts/alert_snapshot_*.json`
- `warmup_seconds`: ignore breaches during startup/doc-fetch burst window
- `consecutive_breach_threshold`: only trigger interrupt alert when breaches happen continuously

### Basic Usage

```python
from src.alerting import get_alert_manager, AlertSeverity

# Get global alert manager
manager = get_alert_manager()

# Fire an alert
await manager.fire_alert(
    title="Test Failed",
    message="Test case TC-001 failed with timeout",
    severity=AlertSeverity.ERROR,
    component="test_executor",
    run_id="run-123"
)
```

### Convenience Functions

```python
from src.alerting import fire_defect_alert

# Fire defect alert
await fire_defect_alert(
    defect_id="DEF-001",
    bug_type="Type-1",
    title="Critical Bug Found",
    run_id="run-123"
)
```

## Configuration

### Enable Channels

```python
from src.alerting import AlertManager, AlertChannel

manager = AlertManager(
    enabled_channels=[
        AlertChannel.CONSOLE,
        AlertChannel.LOG_FILE,
        AlertChannel.WEBHOOK,
    ],
    dedup_window_minutes=30,
    max_send_count=3,
)
```

### Register Custom Handlers

```python
from src.alerting.handlers import HandlerFactory

# Console handler
console_handler = HandlerFactory.create_console_handler(use_colors=True)
manager.register_handler(AlertChannel.CONSOLE, console_handler)

# File handler with rotation
file_handler = HandlerFactory.create_file_handler(
    filename="alerts.log",
    rotate=True,
    max_bytes=10*1024*1024,  # 10 MB
)
manager.register_handler(AlertChannel.LOG_FILE, file_handler)
```

## Alert Types

### System Alerts

```python
await manager.fire_system_alert(
    message="Memory usage above 90%",
    severity=AlertSeverity.WARNING
)
```

### Test Failure Alerts

```python
await manager.fire_test_failure_alert(
    test_id="TC-001",
    error_message="Assertion failed: expected 200, got 500",
    run_id="run-123"
)
```

### Defect Alerts

```python
await manager.fire_defect_alert(
    defect_id="DEF-001",
    bug_type="Type-1",
    title="API Validation Missing",
    run_id="run-123"
)
```

## Advanced Features

### Alert Filtering

```python
from src.alerting.handlers import HandlerFactory, FilterHandler, AlertSeverity

# Create filtered handler
base_handler = HandlerFactory.create_console_handler()
filtered_handler = FilterHandler(
    inner_handler=base_handler,
    min_severity=AlertSeverity.ERROR,  # Only ERROR and CRITICAL
    blocked_components=["debug"],     # Block debug component
)

manager.register_handler(AlertChannel.CONSOLE, filtered_handler)
```

### Alert Aggregation

```python
from src.alerting.handlers import HandlerFactory, AggregateHandler

# Create aggregate handler
base_handler = HandlerFactory.create_console_handler()
aggregate_handler = AggregateHandler(
    inner_handler=base_handler,
    window_seconds=60,    # Aggregate 60 second window
    max_size=100,         # Or flush at 100 alerts
)

manager.register_handler(AlertChannel.CONSOLE, aggregate_handler)
```

### Query Alerts

```python
from src.alerting import AlertFilter

# Get recent critical alerts
filter = AlertFilter(
    min_severity=AlertSeverity.CRITICAL,
    time_window=60,  # Last 60 minutes
)

alerts = manager.get_alerts(filter=filter, limit=50)

for alert in alerts:
    print(f"{alert.timestamp}: {alert.title}")
```

## Handlers

### Enhanced Console Handler

```python
from src.alerting.handlers import EnhancedConsoleHandler

handler = EnhancedConsoleHandler(use_colors=True)
await handler.send(alert)
```

### Rotating File Handler

```python
from src.alerting.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    base_filename="alerts.log",
    max_bytes=10*1024*1024,  # 10 MB per file
    backup_count=5,           # Keep 5 backups
)
```

### Email Handler

```python
from src.alerting.handlers import HandlerFactory, EmailConfig

config = EmailConfig(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    from_addr="alerts@example.com",
    to_addrs=["team@example.com"],
)

handler = HandlerFactory.create_email_handler(config)
```

### Webhook Handler

```python
from src.alerting.handlers import HandlerFactory, WebhookConfig

config = WebhookConfig(
    url="https://hooks.example.com/alerts",
    timeout=5.0,
    headers={"Authorization": "Bearer token123"},
)

handler = HandlerFactory.create_webhook_handler(config)
```

### Slack Handler

```python
from src.alerting.handlers import HandlerFactory, SlackConfig

config = SlackConfig(
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    channel="#alerts",
    username="AI-DB-QC Bot",
    icon_emoji=":warning:",
)

handler = HandlerFactory.create_slack_handler(config)
```

## Statistics

### Get Alert Statistics

```python
stats = manager.get_statistics()

print(f"Total alerts: {stats.total_alerts}")
print(f"By severity: {stats.alerts_by_severity}")
print(f"By channel: {stats.alerts_by_channel}")
print(f"By component: {stats.alerts_by_component}")
```

### Clear History

```python
manager.clear_history()
```

## Best Practices

1. **Use Appropriate Severity**
   - INFO: Normal operations, milestones
   - WARNING: Potential issues, degraded performance
   - ERROR: Failures requiring attention
   - CRITICAL: System-breaking issues, data loss

2. **Set Component Names**
   - Helps with filtering and analysis
   - Use consistent naming: `test_executor`, `defect_discovery`

3. **Enable Deduplication**
   - Prevents alert spam
   - Default: 30-minute window

4. **Monitor Alert Statistics**
   - Track alert frequency
   - Identify noisy components
   - Tune filters accordingly

5. **Use Aggregation for High-Volume Events**
   - Reduces notification fatigue
   - Preserves context

## Performance

### Target Metrics
- **Alert delivery latency**: < 1 second
- **Alert coverage**: 100% of critical events

### Optimization Tips
1. Use filtering to reduce noise
2. Aggregate high-volume alerts
3. Rotate log files to prevent disk issues
4. Set appropriate deduplication windows

## Troubleshooting

### Alerts Not Sending
- Check handler registration
- Verify channel is enabled
- Check for filter blocks

### Too Many Alerts
- Increase deduplication window
- Add component filters
- Raise minimum severity
- Enable aggregation

### Email Not Sending
- Verify SMTP credentials
- Check firewall rules
- Test with telnet: `telnet smtp.gmail.com 587`

### Webhook Failing
- Verify URL is accessible
- Check timeout setting
- Review error logs

## Examples

### Complete Setup

```python
from src.alerting import AlertManager, AlertChannel
from src.alerting.handlers import HandlerFactory

# Create manager
manager = AlertManager(
    enabled_channels=[
        AlertChannel.CONSOLE,
        AlertChannel.LOG_FILE,
    ]
)

# Configure handlers
console_handler = HandlerFactory.create_console_handler(use_colors=True)
file_handler = HandlerFactory.create_file_handler(rotate=True)

manager.register_handler(AlertChannel.CONSOLE, console_handler)
manager.register_handler(AlertChannel.LOG_FILE, file_handler)

# Use in code
await manager.fire_alert(
    title="Test Suite Started",
    message="Running 100 test cases",
    severity=AlertSeverity.INFO,
)
```

### Integration with Test Runner

```python
from src.alerting import fire_defect_alert

async def run_test(test_case):
    try:
        result = await execute_test(test_case)

        if not result.success and result.is_bug:
            await fire_defect_alert(
                defect_id=result.defect_id,
                bug_type=result.bug_type,
                title=f"Bug Found: {result.defect_id}",
                run_id=current_run_id,
            )

    except Exception as e:
        await manager.fire_test_failure_alert(
            test_id=test_case.id,
            error_message=str(e),
            run_id=current_run_id,
        )
```
