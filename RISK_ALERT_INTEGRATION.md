# Risk Alert Feature Integration Guide

## Overview
This guide explains how to integrate the Risk Alert feature into the existing Slack Trading Bot application.

## Files Created

### Core Implementation
1. `models/risk_alert.py` - Data models for risk alerts
2. `services/alert_monitor.py` - Alert monitoring service
3. `ui/risk_alert_widget.py` - Slack UI components
4. `listeners/risk_alert_handlers.py` - Command and action handlers

### Updated Files
1. `services/database.py` - Added risk alert CRUD methods
2. `ui/notifications.py` - Added alert notification methods

## Integration Steps

### Step 1: Update app.py

Add imports at the top of `app.py`:

```python
from services.alert_monitor import get_alert_monitor
from listeners.risk_alert_handlers import register_risk_alert_handlers
```

After creating the service container (around line 60), initialize the alert monitor:

```python
# Initialize alert monitor
alert_monitor = get_alert_monitor(
    db_service=service_container.get(DatabaseService),
    notification_service=NotificationService(),
    market_data_service=service_container.get(MarketDataService)
)
```

After registering event handlers (around line 350), register risk alert handlers:

```python
# Register risk alert handlers
try:
    register_risk_alert_handlers(
        app=app,
        db_service=service_container.get(DatabaseService),
        auth_service=service_container.get(AuthService),
        alert_monitor=alert_monitor,
        notification_service=NotificationService()
    )
    logger.info("Risk alert handlers registered successfully")
except Exception as e:
    logger.error(f"Failed to register risk alert handlers: {e}")
```

### Step 2: Update listeners/actions.py

In the `_handle_submit_trade` method, after a trade is successfully executed, add:

```python
# After trade execution (around line 660)
if execution_result.success:
    trade.status = TradeStatus.EXECUTED
    trade.execution_id = execution_result.execution_id
    
    # **NEW: Check trade against active risk alerts**
    try:
        await alert_monitor.check_trade_against_alerts(trade)
        logger.info(f"Trade {trade.trade_id} checked against risk alerts")
    except Exception as e:
        logger.error(f"Failed to check risk alerts: {e}")
        # Don't fail trade if alert check fails
    
    # ... rest of existing code ...
```

### Step 3: Update DynamoDB Tables (if using AWS)

Add two new DynamoDB tables to `template.yaml`:

```yaml
RiskAlertsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: slack-trading-bot-alerts
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: alert_id
        AttributeType: S
      - AttributeName: manager_id
        AttributeType: S
    KeySchema:
      - AttributeName: alert_id
        KeyType: HASH
    GlobalSecondaryIndexes:
      - IndexName: manager_id-index
        KeySchema:
          - AttributeName: manager_id
            KeyType: HASH
        Projection:
          ProjectionType: ALL

AlertEventsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: slack-trading-bot-alert-events
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: event_id
        AttributeType: S
      - AttributeName: alert_id
        AttributeType: S
    KeySchema:
      - AttributeName: event_id
        KeyType: HASH
    GlobalSecondaryIndexes:
      - IndexName: alert_id-index
        KeySchema:
          - AttributeName: alert_id
            KeyType: HASH
        Projection:
          ProjectionType: ALL
```

### Step 4: Update Service Container

In `services/service_container.py`, add alert monitor to the container:

```python
from services.alert_monitor import RiskAlertMonitor

# In _configure_default_services function:
container.register(
    RiskAlertMonitor,
    dependencies=[DatabaseService, NotificationService, MarketDataService],
    startup_priority=45,
    shutdown_priority=55
)
```

## Usage Examples

### Creating a Risk Alert

1. User runs `/risk-alert` command in Slack
2. Modal opens with form fields:
   - Alert Name (optional)
   - Minimum Trade Size ($)
   - Loss Threshold (%)
   - VIX Threshold
   - Notification options (scan existing, monitor new)
3. User submits form
4. Alert is saved to database
5. If "scan existing" selected, existing trades are checked
6. User receives confirmation message

### Alert Triggers

When a new trade is executed:
1. Trade metrics are calculated (size, loss %, current VIX)
2. All active alerts are checked
3. If trade matches criteria, manager is notified via DM
4. Notification includes trade details and action buttons

### Managing Alerts

Users can list their alerts with `/risk-alerts` command:
- View all active/paused alerts
- Pause/resume alerts
- Edit alert criteria
- Delete alerts

## Testing

### Mock Mode Testing

The implementation works in mock mode (development) without AWS:
- All database operations use in-memory mock data
- Market data uses cached/mock VIX values
- Notifications are queued but not actually sent

### Manual Testing

1. Create a test alert with low thresholds
2. Execute a test trade that matches criteria
3. Verify manager receives notification
4. Test pause/resume functionality
5. Test alert editing and deletion

## Monitoring

### Logs

Monitor these log messages:
- `Risk alert {alert_id} created by {user_id}`
- `Checking trade {trade_id} against active alerts`
- `Trade {trade_id} triggered {count} alert(s)`
- `Alert {alert_id} paused/resumed/deleted`

### Metrics

Track:
- Number of active alerts per manager
- Alert trigger frequency
- Trade matching rates
- Notification delivery success

## Troubleshooting

### Alert not triggering
- Check alert is ACTIVE status
- Verify VIX threshold is met
- Check trade size calculation
- Review loss percentage calculation

### Modal not opening
- Verify user has PORTFOLIO_MANAGER or ADMIN role
- Check Slack app permissions
- Review app.py initialization

### Database errors
- Ensure tables exist (or mock mode is enabled)
- Check AWS credentials if using DynamoDB
- Verify GSI indexes are created

## Security Considerations

1. **Authorization**: Only Portfolio Managers and Admins can create alerts
2. **Data Privacy**: Alerts are user-scoped (managers only see their own)
3. **Audit Trail**: All alert triggers are logged to alert_events table
4. **Rate Limiting**: Consider adding rate limits for alert creation

## Performance Considerations

1. **VIX Caching**: VIX data cached for 5 minutes to reduce API calls
2. **Batch Scanning**: Existing trade scans limited to 100 trades
3. **Async Operations**: All alert checks are non-blocking
4. **Database Queries**: Uses GSI for efficient manager lookups

## Future Enhancements

1. **Email Notifications**: Add email delivery channel
2. **SMS Alerts**: Critical alerts via SMS
3. **Alert Templates**: Pre-configured alert templates
4. **Alert Groups**: Group multiple criteria into single alert
5. **Historical Reports**: Weekly alert trigger summaries
6. **Machine Learning**: Predictive alert recommendations
7. **Multi-Symbol Alerts**: Alert on portfolio-wide conditions
8. **Time-based Alerts**: Different thresholds for different times

