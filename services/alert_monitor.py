"""
Risk Alert Monitoring Service for Jain Global Slack Trading Bot.

This module provides the core monitoring functionality for risk alerts,
including real-time trade checking, existing trade scanning, loss calculation,
and alert notification triggering.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any

from models.trade import Trade, TradeType, TradeStatus
from models.risk_alert import RiskAlertConfig, AlertTriggerEvent, AlertStatus
from services.database import DatabaseService
from services.market_data import MarketDataService, get_market_data_service
from ui.notifications import NotificationService

logger = logging.getLogger(__name__)


class RiskAlertMonitor:
    """
    Monitors trades against configured risk alerts.
    
    This service checks trades (both existing and new) against active risk alert
    criteria and triggers notifications to Portfolio Managers when matches are found.
    It handles real-time monitoring of new trades and on-demand scanning of
    existing positions.
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        notification_service: NotificationService,
        market_data_service: Optional[MarketDataService] = None
    ):
        """
        Initialize the risk alert monitor.
        
        Args:
            db_service: Database service instance
            notification_service: Notification service instance
            market_data_service: Market data service (optional, will create if not provided)
        """
        self.db = db_service
        self.notifications = notification_service
        self.market_data = market_data_service
        self.logger = logging.getLogger(__name__)
        
        # Cache for VIX data to avoid excessive API calls
        self._vix_cache: Optional[Tuple[Decimal, datetime]] = None
        self._vix_cache_ttl = 300  # 5 minutes
        
        self.logger.info("RiskAlertMonitor initialized")
    
    async def initialize(self) -> None:
        """Initialize async resources."""
        if self.market_data is None:
            self.market_data = await get_market_data_service()
        
        self.logger.info("RiskAlertMonitor initialization complete")
    
    async def check_trade_against_alerts(self, trade: Trade) -> None:
        """
        Check if a trade matches any active alert criteria.
        
        This is called when a new trade is executed to see if it should
        trigger any manager alerts.
        
        Args:
            trade: Newly executed trade to check
        """
        try:
            self.logger.info(f"Checking trade {trade.trade_id} against active alerts")
            
            # Get current VIX level
            current_vix = await self._get_current_vix()
            if current_vix is None:
                self.logger.warning("Unable to get VIX data, skipping alert check")
                return
            
            # Calculate trade metrics
            trade_size = trade.quantity * trade.price
            
            # Get current market price for loss calculation
            current_price = await self._get_current_price(trade.symbol)
            if current_price is None:
                self.logger.warning(f"Unable to get current price for {trade.symbol}")
                current_price = trade.price  # Fallback to trade price
            
            # Calculate loss percentage
            loss_percent = self._calculate_loss_percent(
                trade.price,
                current_price,
                trade.trade_type
            )
            
            # Get all active alerts
            active_alerts = await self.db.get_active_alerts()
            
            self.logger.info(
                f"Trade metrics: size=${trade_size}, loss={loss_percent}%, VIX={current_vix}"
            )
            
            # Check each alert
            triggered_count = 0
            for alert in active_alerts:
                if alert.notify_on_new and self._matches_criteria(
                    trade_size, loss_percent, current_vix, alert
                ):
                    await self._send_alert_notification(
                        alert=alert,
                        trade=trade,
                        metrics={
                            'trade_size': trade_size,
                            'loss_percent': loss_percent,
                            'vix_level': current_vix,
                            'current_price': current_price
                        }
                    )
                    triggered_count += 1
            
            if triggered_count > 0:
                self.logger.info(
                    f"Trade {trade.trade_id} triggered {triggered_count} alert(s)"
                )
            else:
                self.logger.debug(f"Trade {trade.trade_id} did not match any alerts")
                
        except Exception as e:
            self.logger.error(f"Error checking trade against alerts: {str(e)}", exc_info=True)
            # Don't raise - we don't want alert checking to break trade execution
    
    async def scan_existing_trades(
        self,
        alert: RiskAlertConfig
    ) -> List[Trade]:
        """
        Scan existing trades for matches when a new alert is created.
        
        Args:
            alert: The newly created alert configuration
            
        Returns:
            List of trades that match the alert criteria
        """
        try:
            self.logger.info(f"Scanning existing trades for alert {alert.alert_id}")
            
            # Get current VIX
            current_vix = await self._get_current_vix()
            if current_vix is None:
                self.logger.warning("Unable to get VIX data for scanning")
                return []
            
            # Check if VIX meets threshold first
            if current_vix < alert.vix_threshold:
                self.logger.info(
                    f"Current VIX ({current_vix}) below threshold ({alert.vix_threshold}), "
                    "no existing trades match"
                )
                return []
            
            # Query trades matching basic criteria
            candidate_trades = await self.db.get_trades_matching_criteria(
                trade_size_min=alert.trade_size_threshold,
                loss_percent=alert.loss_percent_threshold,
                current_vix=current_vix,
                limit=100
            )
            
            if not candidate_trades:
                self.logger.info("No trades found matching basic criteria")
                return []
            
            # Check each trade with real-time pricing
            matching_trades = []
            
            for trade in candidate_trades:
                try:
                    trade_size = trade.quantity * trade.price
                    
                    # Get current price
                    current_price = await self._get_current_price(trade.symbol)
                    if current_price is None:
                        continue
                    
                    # Calculate loss
                    loss_percent = self._calculate_loss_percent(
                        trade.price,
                        current_price,
                        trade.trade_type
                    )
                    
                    # Check if it matches all criteria
                    if self._matches_criteria(trade_size, loss_percent, current_vix, alert):
                        matching_trades.append(trade)
                        
                        # Store metrics in trade for notification
                        trade.market_data = {
                            'trade_size': float(trade_size),
                            'loss_percent': float(loss_percent),
                            'current_price': float(current_price),
                            'vix_level': float(current_vix)
                        }
                        
                except Exception as e:
                    self.logger.warning(
                        f"Error processing trade {trade.trade_id}: {str(e)}"
                    )
                    continue
            
            self.logger.info(
                f"Found {len(matching_trades)} existing trades matching alert criteria"
            )
            
            return matching_trades
            
        except Exception as e:
            self.logger.error(f"Error scanning existing trades: {str(e)}", exc_info=True)
            return []
    
    def _matches_criteria(
        self,
        trade_size: Decimal,
        loss_percent: Decimal,
        vix: Decimal,
        alert: RiskAlertConfig
    ) -> bool:
        """
        Check if trade metrics match alert criteria.
        
        Args:
            trade_size: Trade size in dollars
            loss_percent: Loss percentage (can be negative for gains)
            vix: Current VIX level
            alert: Alert configuration
            
        Returns:
            True if all criteria are met
        """
        matches = (
            trade_size >= alert.trade_size_threshold and
            abs(loss_percent) >= alert.loss_percent_threshold and
            vix >= alert.vix_threshold
        )
        
        if matches:
            self.logger.debug(
                f"Trade matches alert {alert.alert_id}: "
                f"size=${trade_size} >= ${alert.trade_size_threshold}, "
                f"loss={abs(loss_percent)}% >= {alert.loss_percent_threshold}%, "
                f"VIX={vix} >= {alert.vix_threshold}"
            )
        
        return matches
    
    async def _send_alert_notification(
        self,
        alert: RiskAlertConfig,
        trade: Trade,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Send notification to manager about matching trade.
        
        Args:
            alert: Alert configuration
            trade: Trade that triggered the alert
            metrics: Trade metrics (size, loss, VIX, etc.)
        """
        try:
            self.logger.info(
                f"Sending alert notification for trade {trade.trade_id} "
                f"to manager {alert.manager_id}"
            )
            
            # Create trigger event for audit trail
            trigger_event = AlertTriggerEvent(
                alert_id=alert.alert_id,
                trade_id=trade.trade_id,
                manager_id=alert.manager_id,
                trade_size=metrics['trade_size'],
                loss_percent=metrics['loss_percent'],
                vix_level=metrics['vix_level']
            )
            
            # Save trigger event
            await self.db.save_alert_trigger_event(trigger_event)
            
            # Record trigger on alert
            await self.db.record_alert_trigger(alert.alert_id)
            
            # Send notification through notification service
            await self.notifications.send_single_trade_alert(
                manager_id=alert.manager_id,
                alert=alert,
                trade=trade,
                metrics=metrics
            )
            
            trigger_event.notification_sent = True
            trigger_event.notification_sent_at = datetime.now(timezone.utc)
            await self.db.save_alert_trigger_event(trigger_event)
            
            self.logger.info(f"Alert notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {str(e)}", exc_info=True)
    
    async def _get_current_vix(self) -> Optional[Decimal]:
        """
        Get current VIX level with caching.
        
        Returns:
            Current VIX level or None if unavailable
        """
        try:
            # Check cache
            if self._vix_cache is not None:
                vix_value, cache_time = self._vix_cache
                age = (datetime.now(timezone.utc) - cache_time).total_seconds()
                
                if age < self._vix_cache_ttl:
                    self.logger.debug(f"Using cached VIX value: {vix_value}")
                    return vix_value
            
            # Fetch fresh VIX data
            if self.market_data is None:
                self.logger.warning("Market data service not initialized")
                return None
            
            vix_quote = await self.market_data.get_quote("^VIX")
            
            if vix_quote and vix_quote.current_price:
                vix_value = vix_quote.current_price
                self._vix_cache = (vix_value, datetime.now(timezone.utc))
                self.logger.debug(f"Fetched current VIX: {vix_value}")
                return vix_value
            
            self.logger.warning("VIX quote unavailable")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching VIX: {str(e)}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if unavailable
        """
        try:
            if self.market_data is None:
                return None
            
            quote = await self.market_data.get_quote(symbol)
            
            if quote and quote.current_price:
                return quote.current_price
            
            self.logger.warning(f"Unable to get current price for {symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    def _calculate_loss_percent(
        self,
        entry_price: Decimal,
        current_price: Decimal,
        trade_type: TradeType
    ) -> Decimal:
        """
        Calculate loss percentage for a trade.
        
        Args:
            entry_price: Price at which trade was entered
            current_price: Current market price
            trade_type: Type of trade (BUY or SELL)
            
        Returns:
            Loss percentage (negative if profitable, positive if losing)
        """
        if entry_price == 0:
            return Decimal('0')
        
        if trade_type == TradeType.BUY:
            # For long positions: loss = (entry - current) / entry * 100
            loss_percent = ((entry_price - current_price) / entry_price) * Decimal('100')
        else:
            # For short positions: loss = (current - entry) / entry * 100
            loss_percent = ((current_price - entry_price) / entry_price) * Decimal('100')
        
        return loss_percent
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._vix_cache = None
        self.logger.info("RiskAlertMonitor cleanup complete")


# Singleton instance for service container
_alert_monitor_instance: Optional[RiskAlertMonitor] = None


def get_alert_monitor(
    db_service: DatabaseService,
    notification_service: NotificationService,
    market_data_service: Optional[MarketDataService] = None
) -> RiskAlertMonitor:
    """
    Get or create the alert monitor singleton instance.
    
    Args:
        db_service: Database service instance
        notification_service: Notification service instance
        market_data_service: Market data service (optional)
        
    Returns:
        RiskAlertMonitor instance
    """
    global _alert_monitor_instance
    
    if _alert_monitor_instance is None:
        _alert_monitor_instance = RiskAlertMonitor(
            db_service=db_service,
            notification_service=notification_service,
            market_data_service=market_data_service
        )
    
    return _alert_monitor_instance

