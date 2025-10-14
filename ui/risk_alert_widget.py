"""
Risk Alert UI Widgets for Jain Global Slack Trading Bot.

This module provides Slack UI components for risk alert configuration,
management, and display. Includes modals, blocks, and interactive elements
for creating, viewing, and managing risk alerts.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional

from models.risk_alert import RiskAlertConfig, AlertStatus
from models.trade import Trade
from utils.formatters import format_money, format_percent, format_date

logger = logging.getLogger(__name__)


def create_risk_alert_modal(existing_alert: Optional[RiskAlertConfig] = None) -> Dict:
    """
    Create modal for configuring risk alerts.
    
    Args:
        existing_alert: Optional existing alert for editing
        
    Returns:
        Slack modal view dictionary
    """
    is_edit = existing_alert is not None
    
    modal = {
        "type": "modal",
        "callback_id": "risk_alert_setup",
        "title": {
            "type": "plain_text",
            "text": "Edit Risk Alert" if is_edit else "Create Risk Alert"
        },
        "submit": {
            "type": "plain_text",
            "text": "Save Alert" if is_edit else "Create Alert"
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🚨 *Configure Risk Alert Parameters*\n"
                           "You'll be notified when trades match these criteria:"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "input",
                "block_id": "alert_name",
                "label": {
                    "type": "plain_text",
                    "text": "Alert Name"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "name_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., High Risk Large Cap Alert"
                    },
                    "initial_value": existing_alert.name if is_edit and existing_alert.name else ""
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "trade_size",
                "label": {
                    "type": "plain_text",
                    "text": "Minimum Trade Size ($)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "size_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., 100000"
                    },
                    "initial_value": str(existing_alert.trade_size_threshold) if is_edit else ""
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Alert triggers when trade size exceeds this amount"
                }
            },
            {
                "type": "input",
                "block_id": "loss_percent",
                "label": {
                    "type": "plain_text",
                    "text": "Loss Threshold (%)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "loss_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., 5"
                    },
                    "initial_value": str(existing_alert.loss_percent_threshold) if is_edit else ""
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Alert triggers when loss percentage exceeds this value"
                }
            },
            {
                "type": "input",
                "block_id": "vix_threshold",
                "label": {
                    "type": "plain_text",
                    "text": "VIX Threshold"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "vix_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., 20"
                    },
                    "initial_value": str(existing_alert.vix_threshold) if is_edit else ""
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Alert triggers when VIX level exceeds this value"
                }
            },
            {
                "type": "input",
                "block_id": "notification_options",
                "label": {
                    "type": "plain_text",
                    "text": "Notification Settings"
                },
                "element": {
                    "type": "checkboxes",
                    "action_id": "notify_checkboxes",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Scan existing trades now"
                            },
                            "value": "scan_existing",
                            "description": {
                                "type": "plain_text",
                                "text": "Check current open positions immediately"
                            }
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Monitor new trades"
                            },
                            "value": "monitor_new",
                            "description": {
                                "type": "plain_text",
                                "text": "Alert on future trades that match criteria"
                            }
                        }
                    ],
                    "initial_options": [
                        {
                            "text": {"type": "plain_text", "text": "Scan existing trades now"},
                            "value": "scan_existing",
                            "description": {"type": "plain_text", "text": "Check current open positions immediately"}
                        },
                        {
                            "text": {"type": "plain_text", "text": "Monitor new trades"},
                            "value": "monitor_new",
                            "description": {"type": "plain_text", "text": "Alert on future trades that match criteria"}
                        }
                    ] if not is_edit else (
                        [{
                            "text": {"type": "plain_text", "text": "Scan existing trades now"},
                            "value": "scan_existing",
                            "description": {"type": "plain_text", "text": "Check current open positions immediately"}
                        }] if existing_alert.notify_on_existing else []
                    ) + (
                        [{
                            "text": {"type": "plain_text", "text": "Monitor new trades"},
                            "value": "monitor_new",
                            "description": {"type": "plain_text", "text": "Alert on future trades that match criteria"}
                        }] if existing_alert.notify_on_new else []
                    )
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 *Tip:* Select both options for comprehensive monitoring"
                    }
                ]
            }
        ]
    }
    
    # Add private metadata if editing
    if is_edit:
        modal["private_metadata"] = existing_alert.alert_id
    
    return modal


def create_alert_list_message(alerts: List[RiskAlertConfig]) -> Dict:
    """
    Create message displaying list of risk alerts.
    
    Args:
        alerts: List of risk alert configurations
        
    Returns:
        Slack message blocks
    """
    if not alerts:
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📋 *Your Risk Alerts*\n\nYou don't have any active risk alerts.\n\n"
                               "Use `/risk-alert` to create your first alert."
                    }
                }
            ]
        }
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Your Risk Alerts ({len(alerts)} active)"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    for alert in alerts:
        alert_block = create_alert_summary_block(alert)
        blocks.append(alert_block)
        blocks.append({"type": "divider"})
    
    return {"blocks": blocks}


def create_alert_summary_block(alert: RiskAlertConfig) -> Dict:
    """
    Create block summarizing a single alert.
    
    Args:
        alert: Risk alert configuration
        
    Returns:
        Slack block
    """
    status_emoji = {
        AlertStatus.ACTIVE: "✅",
        AlertStatus.PAUSED: "⏸️",
        AlertStatus.EXPIRED: "⏱️",
        AlertStatus.DELETED: "🗑️"
    }
    
    alert_name = alert.name or f"Alert {alert.alert_id[:8]}"
    
    trigger_info = ""
    if alert.trigger_count > 0:
        trigger_info = f"\n🔔 Triggered {alert.trigger_count} time(s)"
        if alert.last_triggered_at:
            trigger_info += f" • Last: {format_date(alert.last_triggered_at)}"
    
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{status_emoji.get(alert.status, '⚪')} *{alert_name}*\n"
                   f"📊 Trade Size: ≥ {format_money(alert.trade_size_threshold)}\n"
                   f"📉 Loss: ≥ {alert.loss_percent_threshold}%\n"
                   f"📈 VIX: ≥ {alert.vix_threshold}\n"
                   f"📅 Created: {format_date(alert.created_at)}"
                   f"{trigger_info}"
        },
        "accessory": {
            "type": "overflow",
            "action_id": f"alert_menu_{alert.alert_id}",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "⏸️ Pause" if alert.status == AlertStatus.ACTIVE else "▶️ Resume"
                    },
                    "value": f"toggle_{alert.alert_id}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit"
                    },
                    "value": f"edit_{alert.alert_id}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "🗑️ Delete"
                    },
                    "value": f"delete_{alert.alert_id}"
                }
            ]
        }
    }


def create_alert_triggered_message(
    alert: RiskAlertConfig,
    trade: Trade,
    metrics: Dict[str, Any]
) -> Dict:
    """
    Create message for a single trade alert.
    
    Args:
        alert: Alert that was triggered
        trade: Trade that triggered the alert
        metrics: Trade metrics (size, loss, VIX)
        
    Returns:
        Slack message blocks
    """
    trade_size = metrics.get('trade_size', trade.quantity * trade.price)
    loss_percent = metrics.get('loss_percent', 0)
    vix_level = metrics.get('vix_level', 0)
    current_price = metrics.get('current_price', trade.price)
    
    # Determine severity color
    if abs(loss_percent) >= 10 or vix_level >= 30:
        color = "#ff0000"  # Red - High severity
    elif abs(loss_percent) >= 5 or vix_level >= 20:
        color = "#ff9900"  # Orange - Medium severity
    else:
        color = "#ffcc00"  # Yellow - Low severity
    
    alert_name = alert.name or f"Alert {alert.alert_id[:8]}"
    
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Risk Alert Triggered: {alert_name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Trade Alert Details*\n\n"
                           f"📊 *Symbol:* {trade.symbol}\n"
                           f"💼 *Trade Type:* {trade.trade_type.value.upper()}\n"
                           f"💵 *Trade Size:* {format_money(trade_size)}\n"
                           f"📈 *Quantity:* {trade.quantity:,} shares\n"
                           f"💰 *Entry Price:* {format_money(trade.price)}\n"
                           f"📍 *Current Price:* {format_money(current_price)}\n"
                           f"📉 *Loss:* {format_percent(abs(loss_percent))}\n"
                           f"📊 *VIX Level:* {vix_level}\n"
                           f"👤 *Trader:* <@{trade.user_id}>\n"
                           f"🕐 *Trade Time:* {format_date(trade.timestamp)}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Alert Criteria Met:*\n"
                           f"{'✅' if trade_size >= alert.trade_size_threshold else '❌'} Trade Size: "
                           f"{format_money(trade_size)} ≥ {format_money(alert.trade_size_threshold)}\n"
                           f"{'✅' if abs(loss_percent) >= alert.loss_percent_threshold else '❌'} Loss: "
                           f"{format_percent(abs(loss_percent))} ≥ {format_percent(alert.loss_percent_threshold)}\n"
                           f"{'✅' if vix_level >= alert.vix_threshold else '❌'} VIX: "
                           f"{vix_level} ≥ {alert.vix_threshold}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Trade Details"
                        },
                        "action_id": f"view_trade_{trade.trade_id}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Contact Trader"
                        },
                        "action_id": f"contact_trader_{trade.user_id}",
                        "url": f"slack://user?team=xxx&id={trade.user_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Pause Alert"
                        },
                        "action_id": f"pause_alert_{alert.alert_id}",
                        "style": "danger"
                    }
                ]
            }
        ],
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Alert ID: `{alert.alert_id}` • Trade ID: `{trade.trade_id}`"
                            }
                        ]
                    }
                ]
            }
        ]
    }


def create_existing_trades_summary(
    alert: RiskAlertConfig,
    trades: List[Trade],
    show_all: bool = False
) -> Dict:
    """
    Create message summarizing existing trades that match alert.
    
    Args:
        alert: Alert configuration
        trades: List of matching trades
        show_all: Whether to show all trades or just summary
        
    Returns:
        Slack message blocks
    """
    alert_name = alert.name or f"Alert {alert.alert_id[:8]}"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 Existing Trades Scan: {alert_name}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Alert Criteria:*\n"
                       f"📊 Trade Size: ≥ {format_money(alert.trade_size_threshold)}\n"
                       f"📉 Loss: ≥ {format_percent(alert.loss_percent_threshold)}\n"
                       f"📈 VIX: ≥ {alert.vix_threshold}\n\n"
                       f"*Found {len(trades)} matching trade(s)*"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    if not trades:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ No existing trades match your alert criteria."
            }
        })
    else:
        # Show summary or detailed view
        display_limit = len(trades) if show_all else min(5, len(trades))
        
        for i, trade in enumerate(trades[:display_limit]):
            metrics = trade.market_data or {}
            trade_size = metrics.get('trade_size', float(trade.quantity * trade.price))
            loss_percent = metrics.get('loss_percent', 0)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i+1}. {trade.symbol}* - {trade.trade_type.value.upper()}\n"
                           f"💵 Size: {format_money(trade_size)} | "
                           f"📉 Loss: {format_percent(abs(loss_percent))} | "
                           f"👤 <@{trade.user_id}>"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View"
                    },
                    "action_id": f"view_trade_{trade.trade_id}",
                    "value": trade.trade_id
                }
            })
        
        if len(trades) > display_limit:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_... and {len(trades) - display_limit} more trade(s)_"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Show All"
                    },
                    "action_id": f"show_all_trades_{alert.alert_id}",
                    "value": alert.alert_id
                }
            })
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Scan completed at {format_date(datetime.utcnow())} • "
                       f"Alert will continue monitoring new trades"
            }
        ]
    })
    
    return {"blocks": blocks}


def create_alert_confirmation_message(alert: RiskAlertConfig) -> Dict:
    """
    Create confirmation message after alert creation.
    
    Args:
        alert: Created alert configuration
        
    Returns:
        Slack message blocks
    """
    alert_name = alert.name or f"Alert {alert.alert_id[:8]}"
    
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Risk Alert Created Successfully*\n\n"
                           f"*{alert_name}*\n"
                           f"📊 Trade Size: ≥ {format_money(alert.trade_size_threshold)}\n"
                           f"📉 Loss: ≥ {format_percent(alert.loss_percent_threshold)}\n"
                           f"📈 VIX: ≥ {alert.vix_threshold}\n\n"
                           f"🔔 You'll receive notifications when trades match these criteria."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View All Alerts"
                        },
                        "action_id": "view_all_alerts",
                        "value": "view_all"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Create Another"
                        },
                        "action_id": "create_new_alert",
                        "value": "create_new"
                    }
                ]
            }
        ]
    }

