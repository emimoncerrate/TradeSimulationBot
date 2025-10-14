"""
Risk Alert Command and Action Handlers for Jain Global Slack Trading Bot.

This module provides Slack command and interactive action handlers for
the risk alert feature, including alert creation, editing, and management.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from slack_bolt import App, Ack, Say
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from models.user import UserRole
from models.risk_alert import RiskAlertConfig, AlertStatus, RiskAlertValidationError
from services.database import DatabaseService
from services.auth import AuthService
from services.alert_monitor import RiskAlertMonitor
from ui.notifications import NotificationService
from ui.risk_alert_widget import (
    create_risk_alert_modal,
    create_alert_list_message,
    create_alert_confirmation_message
)

logger = logging.getLogger(__name__)


def register_risk_alert_handlers(
    app: App,
    db_service: DatabaseService,
    auth_service: AuthService,
    alert_monitor: RiskAlertMonitor,
    notification_service: NotificationService
) -> None:
    """
    Register all risk alert command and action handlers.
    
    Args:
        app: Slack Bolt app instance
        db_service: Database service
        auth_service: Authentication service
        alert_monitor: Alert monitoring service
        notification_service: Notification service
    """
    
    # ========== Slash Commands ==========
    
    def handle_risk_alert_command(ack, body, client):
        """Handle /risk-alert command - opens configuration modal."""
        import time
        start_time = time.time()
        
        ack()  # Acknowledge immediately
        ack_time = time.time()
        logger.info(f"⏱️  ACK took {(ack_time - start_time)*1000:.2f}ms")
        
        try:
            # TEMPORARY: Allow all users to create risk alerts (no role restriction)
            # No auth check needed - just open the modal immediately
            
            # Create and open modal immediately (trigger_id expires in 3 seconds!)
            logger.info(f"🔨 Creating modal for user {body['user_id']}...")
            modal = create_risk_alert_modal()
            modal_time = time.time()
            logger.info(f"⏱️  Modal creation took {(modal_time - ack_time)*1000:.2f}ms")
            
            # Log modal structure for debugging
            import json
            logger.debug(f"📋 Modal structure: {json.dumps(modal, indent=2)[:500]}...")
            
            # Validate trigger_id exists
            trigger_id = body.get('trigger_id')
            if not trigger_id:
                raise ValueError("No trigger_id in request body")
            
            logger.info(f"📤 Opening modal with trigger_id: {trigger_id[:20]}... (full: {len(trigger_id)} chars)")
            
            try:
                response = client.views_open(
                    trigger_id=trigger_id,
                    view=modal
                )
                logger.info(f"📥 Slack API response OK: {response.get('ok', False)}")
            except SlackApiError as slack_err:
                logger.error(f"🚫 Slack API Error: {slack_err.response['error']}")
                logger.error(f"🚫 Full response: {slack_err.response}")
                raise
            open_time = time.time()
            logger.info(f"⏱️  Modal open took {(open_time - modal_time)*1000:.2f}ms")
            logger.info(f"✅ TOTAL TIME: {(open_time - start_time)*1000:.2f}ms")
            
            logger.info(f"Risk alert modal opened for user {body['user_id']}")
            
        except Exception as e:
            # Get detailed error info
            error_details = str(e)
            if hasattr(e, 'response'):
                error_details = f"{str(e)}\nResponse: {e.response}"
            
            logger.error(f"❌ Error handling /risk-alert command: {error_details}", exc_info=True)
            
            try:
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text=f"❌ Error opening risk alert configuration: {str(e)}"
                )
            except:
                pass
    
    def handle_list_alerts_command(ack, body, client):
        """Handle /risk-alerts command - lists user's alerts."""
        ack()  # Acknowledge immediately
        
        async def async_handler():
            try:
                command = body
                # Get user's alerts
                alerts = await db_service.get_manager_alerts(
                    manager_id=command['user_id'],
                    active_only=False
                )
                
                # Create list message
                message = create_alert_list_message(alerts)
                
                # Send as ephemeral message
                await client.chat_postEphemeral(
                    channel=command['channel_id'],
                    user=command['user_id'],
                    **message
                )
                
                logger.info(f"Alert list sent to user {command['user_id']}")
                
            except Exception as e:
                logger.error(f"Error listing alerts: {str(e)}", exc_info=True)
                try:
                    await client.chat_postEphemeral(
                        channel=command['channel_id'],
                        user=command['user_id'],
                        text=f"❌ Error retrieving your alerts: {str(e)}"
                    )
                except:
                    pass
        
        # Run async handler
        import asyncio
        import threading
        def run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(async_handler())
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    
    # ========== Modal Submissions ==========
    
    async def handle_risk_alert_submission(ack: Ack, body: Dict, view: Dict, client: WebClient):
        """Handle risk alert modal submission."""
        
        try:
            # Extract form values
            values = view['state']['values']
            user_id = body['user']['id']
            
            # Parse form data
            alert_name = values['alert_name']['name_input']['value']
            trade_size = Decimal(values['trade_size']['size_input']['value'])
            loss_percent = Decimal(values['loss_percent']['loss_input']['value'])
            vix_threshold = Decimal(values['vix_threshold']['vix_input']['value'])
            
            # Get notification options
            selected_options = values['notification_options']['notify_checkboxes'].get('selected_options', [])
            option_values = [opt['value'] for opt in selected_options]
            notify_existing = 'scan_existing' in option_values
            notify_new = 'monitor_new' in option_values
            
            # Validate inputs
            errors = {}
            
            if trade_size <= 0:
                errors['trade_size'] = "Trade size must be positive"
            if loss_percent < 0 or loss_percent > 100:
                errors['loss_percent'] = "Loss percentage must be between 0 and 100"
            if vix_threshold < 0 or vix_threshold > 100:
                errors['vix_threshold'] = "VIX threshold must be between 0 and 100"
            if not notify_existing and not notify_new:
                errors['notification_options'] = "Select at least one notification option"
            
            if errors:
                await ack(response_action="errors", errors=errors)
                return
            
            # Acknowledge modal
            await ack()
            
            # Create alert configuration
            alert_config = RiskAlertConfig(
                manager_id=user_id,
                name=alert_name if alert_name else None,
                trade_size_threshold=trade_size,
                loss_percent_threshold=loss_percent,
                vix_threshold=vix_threshold,
                notify_on_existing=notify_existing,
                notify_on_new=notify_new
            )
            
            # Save to database
            await db_service.save_risk_alert(alert_config)
            
            logger.info(f"Risk alert {alert_config.alert_id} created by {user_id}")
            
            # Send confirmation
            await notification_service.send_alert_confirmation(user_id, alert_config)
            
            # Scan existing trades if requested
            if notify_existing:
                logger.info(f"Scanning existing trades for alert {alert_config.alert_id}")
                matching_trades = await alert_monitor.scan_existing_trades(alert_config)
                
                if matching_trades:
                    await notification_service.send_risk_alert_summary(
                        manager_id=user_id,
                        alert=alert_config,
                        trades=matching_trades
                    )
                    logger.info(f"Found {len(matching_trades)} matching trades")
                else:
                    logger.info("No existing trades match criteria")
            
        except RiskAlertValidationError as e:
            await ack(response_action="errors", errors={e.field or 'general': e.message})
            logger.warning(f"Alert validation error: {e.message}")
            
        except ValueError as e:
            await ack(response_action="errors", errors={'general': "Invalid number format"})
            logger.warning(f"Value error in alert submission: {str(e)}")
            
        except Exception as e:
            await ack()
            logger.error(f"Error creating risk alert: {str(e)}", exc_info=True)
            
            # Send error message to user
            try:
                await client.chat_postMessage(
                    channel=body['user']['id'],
                    text=f"❌ Error creating risk alert: {str(e)}"
                )
            except:
                pass
    
    # ========== Interactive Actions ==========
    
    async def handle_view_all_alerts(ack: Ack, body: Dict, client: WebClient):
        """Handle 'View All Alerts' button click."""
        await ack()
        
        try:
            user_id = body['user']['id']
            
            # Get user's alerts
            alerts = await db_service.get_manager_alerts(
                manager_id=user_id,
                active_only=False
            )
            
            # Create list message
            message = create_alert_list_message(alerts)
            
            # Send as DM
            await client.chat_postMessage(
                channel=user_id,
                **message
            )
            
        except Exception as e:
            logger.error(f"Error viewing all alerts: {str(e)}", exc_info=True)
    
    async def handle_create_new_alert(ack: Ack, body: Dict, client: WebClient):
        """Handle 'Create Another' button click."""
        await ack()
        
        try:
            # Open new alert modal
            modal = create_risk_alert_modal()
            await client.views_open(
                trigger_id=body['trigger_id'],
                view=modal
            )
            
        except Exception as e:
            logger.error(f"Error creating new alert: {str(e)}", exc_info=True)
    
    async def handle_alert_menu(ack: Ack, body: Dict, action: Dict, client: WebClient):
        """Handle alert overflow menu actions."""
        await ack()
        
        try:
            selected_value = action['selected_option']['value']
            user_id = body['user']['id']
            
            if selected_value.startswith('toggle_'):
                alert_id = selected_value.replace('toggle_', '')
                await handle_toggle_alert(alert_id, user_id, client)
                
            elif selected_value.startswith('edit_'):
                alert_id = selected_value.replace('edit_', '')
                await handle_edit_alert(alert_id, user_id, body['trigger_id'], client)
                
            elif selected_value.startswith('delete_'):
                alert_id = selected_value.replace('delete_', '')
                await handle_delete_alert(alert_id, user_id, client)
                
        except Exception as e:
            logger.error(f"Error handling alert menu: {str(e)}", exc_info=True)
    
    async def handle_pause_alert_button(ack: Ack, body: Dict, action: Dict, client: WebClient):
        """Handle 'Pause Alert' button from notification."""
        await ack()
        
        try:
            alert_id = action['action_id'].replace('pause_alert_', '')
            user_id = body['user']['id']
            
            # Pause the alert
            alert = await db_service.get_risk_alert(alert_id)
            if alert and alert.manager_id == user_id:
                await db_service.update_alert_status(alert_id, AlertStatus.PAUSED)
                
                await client.chat_postMessage(
                    channel=user_id,
                    text=f"⏸️ Alert '{alert.name or alert_id[:8]}' has been paused."
                )
                
                logger.info(f"Alert {alert_id} paused by user {user_id}")
            else:
                await client.chat_postMessage(
                    channel=user_id,
                    text="❌ Alert not found or you don't have permission to pause it."
                )
                
        except Exception as e:
            logger.error(f"Error pausing alert: {str(e)}", exc_info=True)
    
    # ========== Helper Functions ==========
    
    async def handle_toggle_alert(alert_id: str, user_id: str, client: WebClient):
        """Toggle alert between active and paused."""
        try:
            alert = await db_service.get_risk_alert(alert_id)
            
            if not alert or alert.manager_id != user_id:
                await client.chat_postMessage(
                    channel=user_id,
                    text="❌ Alert not found or access denied."
                )
                return
            
            if alert.status == AlertStatus.ACTIVE:
                alert.pause()
                await db_service.update_alert_status(alert_id, AlertStatus.PAUSED)
                status_text = "⏸️ paused"
            elif alert.status == AlertStatus.PAUSED:
                alert.resume()
                await db_service.update_alert_status(alert_id, AlertStatus.ACTIVE)
                status_text = "▶️ resumed"
            else:
                await client.chat_postMessage(
                    channel=user_id,
                    text="❌ Cannot toggle this alert."
                )
                return
            
            await client.chat_postMessage(
                channel=user_id,
                text=f"{status_text.split()[0]} Alert '{alert.name or alert_id[:8]}' has been {status_text.split()[1]}."
            )
            
            logger.info(f"Alert {alert_id} toggled to {alert.status.value}")
            
        except Exception as e:
            logger.error(f"Error toggling alert: {str(e)}", exc_info=True)
    
    async def handle_edit_alert(alert_id: str, user_id: str, trigger_id: str, client: WebClient):
        """Open modal to edit alert."""
        try:
            alert = await db_service.get_risk_alert(alert_id)
            
            if not alert or alert.manager_id != user_id:
                await client.chat_postMessage(
                    channel=user_id,
                    text="❌ Alert not found or access denied."
                )
                return
            
            # Open edit modal
            modal = create_risk_alert_modal(existing_alert=alert)
            await client.views_open(
                trigger_id=trigger_id,
                view=modal
            )
            
        except Exception as e:
            logger.error(f"Error editing alert: {str(e)}", exc_info=True)
    
    async def handle_delete_alert(alert_id: str, user_id: str, client: WebClient):
        """Delete (soft delete) an alert."""
        try:
            alert = await db_service.get_risk_alert(alert_id)
            
            if not alert or alert.manager_id != user_id:
                await client.chat_postMessage(
                    channel=user_id,
                    text="❌ Alert not found or access denied."
                )
                return
            
            # Delete alert
            await db_service.delete_alert(alert_id)
            
            await client.chat_postMessage(
                channel=user_id,
                text=f"🗑️ Alert '{alert.name or alert_id[:8]}' has been deleted."
            )
            
            logger.info(f"Alert {alert_id} deleted by user {user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting alert: {str(e)}", exc_info=True)
    
    # Manually register the command handlers
    app.command("/risk-alert")(handle_risk_alert_command)
    app.command("/risk-alerts")(handle_list_alerts_command)
    
    # Manually register view handlers
    app.view("risk_alert_setup")(handle_risk_alert_submission)
    
    # Manually register action handlers
    app.action("view_all_alerts")(handle_view_all_alerts)
    app.action("create_new_alert")(handle_create_new_alert)
    app.action({"action_id": {"type": "regex", "pattern": r"^alert_menu_.*"}})(handle_alert_menu)
    app.action({"action_id": {"type": "regex", "pattern": r"^pause_alert_.*"}})(handle_pause_alert_button)
    
    logger.info("Risk alert handlers registered successfully")

