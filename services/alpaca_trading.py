"""
Alpaca Trading Platform Integration Service

Integrates Slack Trading Bot with Alpaca's brokerage API to execute real trades.
Supports both paper trading and live trading environments.
"""

import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
import structlog

from models.trade import Trade, TradeStatus, TradeType
from services.trading_api import ExecutionReport, OrderStatus, OrderFill, ExecutionVenue, OrderType
from config.settings import get_config


logger = structlog.get_logger(__name__)


class AlpacaOrderType(Enum):
    """Alpaca order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class AlpacaTimeInForce(Enum):
    """Alpaca time in force values"""
    DAY = "day"
    GTC = "gtc"  # Good til canceled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


@dataclass
class AlpacaConfig:
    """Alpaca API configuration"""
    api_key: str
    secret_key: str
    base_url: str  # Paper: https://paper-api.alpaca.markets, Live: https://api.alpaca.markets
    is_paper_trading: bool = True


class AlpacaTradingService:
    """
    Alpaca trading platform integration service.
    
    Handles real trade execution via Alpaca's API, replacing mock execution
    for production trading scenarios.
    """
    
    def __init__(self, config: Optional[AlpacaConfig] = None):
        """Initialize Alpaca trading service"""
        self.config = config or self._load_config()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Alpaca API client
        self.api = tradeapi.REST(
            key_id=self.config.api_key,
            secret_key=self.config.secret_key,
            base_url=self.config.base_url,
            api_version='v2'
        )
        
        # Verify connection
        try:
            account = self.api.get_account()
            self.logger.info(
                "Alpaca trading service initialized",
                account_number=account.account_number,
                trading_blocked=account.trading_blocked,
                paper_trading=self.config.is_paper_trading
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca API: {e}")
            raise
    
    def _load_config(self) -> AlpacaConfig:
        """Load Alpaca configuration from environment"""
        app_config = get_config()
        
        return AlpacaConfig(
            api_key=app_config.alpaca.api_key,
            secret_key=app_config.alpaca.secret_key,
            base_url=app_config.alpaca.base_url,
            is_paper_trading=app_config.alpaca.paper_trading
        )
    
    async def execute_trade(self, trade: Trade) -> ExecutionReport:
        """
        Execute trade via Alpaca API
        
        Args:
            trade: Trade object from Slack input
            
        Returns:
            ExecutionReport with execution details
            
        Raises:
            Exception if trade execution fails
        """
        self.logger.info(
            "Executing trade via Alpaca",
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            quantity=trade.quantity,
            trade_type=trade.trade_type.value
        )
        
        try:
            # Pre-execution validation
            await self._validate_trade_conditions(trade)
            
            # Submit order to Alpaca
            alpaca_order = await self._submit_order(trade)
            
            # Wait for order to be processed
            filled_order = await self._wait_for_fill(alpaca_order.id, timeout=30)
            
            # Convert Alpaca order to ExecutionReport
            execution_report = self._convert_to_execution_report(
                trade, 
                filled_order
            )
            
            # Update trade status
            if filled_order.status == 'filled':
                trade.status = TradeStatus.EXECUTED
                trade.execution_id = filled_order.id
                trade.executed_price = Decimal(str(filled_order.filled_avg_price))
                trade.executed_at = datetime.fromisoformat(
                    filled_order.filled_at.replace('Z', '+00:00')
                )
            elif filled_order.status == 'partially_filled':
                trade.status = TradeStatus.PARTIALLY_FILLED
                trade.execution_id = filled_order.id
                trade.executed_price = Decimal(str(filled_order.filled_avg_price))
            else:
                trade.status = TradeStatus.FAILED
            
            self.logger.info(
                "Trade executed successfully via Alpaca",
                trade_id=trade.trade_id,
                alpaca_order_id=filled_order.id,
                status=filled_order.status,
                filled_qty=filled_order.filled_qty,
                filled_price=filled_order.filled_avg_price
            )
            
            return execution_report
            
        except APIError as e:
            self.logger.error(
                "Alpaca API error during trade execution",
                trade_id=trade.trade_id,
                error_code=e.code if hasattr(e, 'code') else None,
                error_message=str(e)
            )
            trade.status = TradeStatus.FAILED
            raise Exception(f"Alpaca API error: {e}")
            
        except Exception as e:
            self.logger.error(
                "Unexpected error during trade execution",
                trade_id=trade.trade_id,
                error=str(e)
            )
            trade.status = TradeStatus.FAILED
            raise
    
    async def _validate_trade_conditions(self, trade: Trade) -> None:
        """
        Validate trading conditions before submission
        
        Args:
            trade: Trade to validate
            
        Raises:
            Exception if validation fails
        """
        # Check if market is open (for market orders)
        loop = asyncio.get_event_loop()
        clock = await loop.run_in_executor(None, self.api.get_clock)
        
        if not clock.is_open:
            self.logger.warning(
                "Market is currently closed",
                trade_id=trade.trade_id,
                next_open=clock.next_open
            )
            # You can choose to reject or queue for next open
            # For now, we'll allow it (will be queued until market opens)
        
        # Verify symbol is tradable
        try:
            asset = await loop.run_in_executor(None, lambda: self.api.get_asset(trade.symbol))
            if not asset.tradable:
                raise Exception(f"Symbol {trade.symbol} is not tradable")
            if not asset.shortable and trade.trade_type == TradeType.SELL:
                raise Exception(f"Symbol {trade.symbol} is not shortable")
        except APIError as e:
            raise Exception(f"Invalid symbol {trade.symbol}: {e}")
        
        # Check account buying power
        account = await loop.run_in_executor(None, self.api.get_account)
        estimated_cost = float(trade.price) * trade.quantity
        
        if trade.trade_type == TradeType.BUY:
            buying_power = float(account.buying_power)
            if estimated_cost > buying_power:
                raise Exception(
                    f"Insufficient buying power. Required: ${estimated_cost:,.2f}, "
                    f"Available: ${buying_power:,.2f}"
                )
        
        self.logger.info("Trade validation passed", trade_id=trade.trade_id)
    
    async def _submit_order(self, trade: Trade) -> Any:
        """
        Submit order to Alpaca
        
        Args:
            trade: Trade to submit
            
        Returns:
            Alpaca order object
        """
        # Prepare order parameters
        order_params = {
            'symbol': trade.symbol,
            'qty': trade.quantity,
            'side': 'buy' if trade.trade_type == TradeType.BUY else 'sell',
            'type': 'market',  # Can be configured based on trade.order_type
            'time_in_force': 'day',
            'client_order_id': trade.trade_id  # Use our trade_id for tracking
        }
        
        # Add limit price if it's a limit order
        # if trade has specific order type, you can add:
        # if order_type == 'limit':
        #     order_params['limit_price'] = float(trade.price)
        
        self.logger.info(
            "Submitting order to Alpaca",
            trade_id=trade.trade_id,
            order_params=order_params
        )
        
        # Submit order (synchronous call, we'll wrap in executor for async)
        loop = asyncio.get_event_loop()
        order = await loop.run_in_executor(
            None,
            lambda: self.api.submit_order(**order_params)
        )
        
        return order
    
    async def _wait_for_fill(self, order_id: str, timeout: int = 30) -> Any:
        """
        Wait for order to be filled
        
        Args:
            order_id: Alpaca order ID
            timeout: Maximum seconds to wait
            
        Returns:
            Filled Alpaca order object
        """
        start_time = datetime.now(timezone.utc)
        
        while True:
            # Get order status
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: self.api.get_order(order_id)
            )
            
            # Check if order is in final state
            if order.status in ['filled', 'partially_filled', 'canceled', 'rejected']:
                return order
            
            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > timeout:
                self.logger.warning(
                    "Order fill timeout",
                    order_id=order_id,
                    status=order.status,
                    elapsed_seconds=elapsed
                )
                return order
            
            # Wait before next check
            await asyncio.sleep(0.5)
    
    def _convert_to_execution_report(
        self, 
        trade: Trade, 
        alpaca_order: Any
    ) -> ExecutionReport:
        """
        Convert Alpaca order to ExecutionReport
        
        Args:
            trade: Original trade object
            alpaca_order: Alpaca order response
            
        Returns:
            ExecutionReport object
        """
        # Map Alpaca status to our OrderStatus
        status_mapping = {
            'filled': OrderStatus.FILLED,
            'partially_filled': OrderStatus.PARTIALLY_FILLED,
            'canceled': OrderStatus.CANCELLED,
            'rejected': OrderStatus.REJECTED,
            'pending_new': OrderStatus.PENDING,
            'new': OrderStatus.PENDING,
            'accepted': OrderStatus.PENDING
        }
        
        status = status_mapping.get(alpaca_order.status, OrderStatus.PENDING)
        
        # Create execution report
        execution_report = ExecutionReport(
            execution_id=str(uuid.uuid4()),
            trade_id=trade.trade_id,
            order_id=alpaca_order.id,
            symbol=trade.symbol,
            trade_type=trade.trade_type.value,
            requested_quantity=trade.quantity,
            requested_price=trade.price,
            order_type=OrderType.MARKET,
            status=status,
            filled_quantity=int(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            remaining_quantity=trade.quantity - int(alpaca_order.filled_qty or 0),
            average_fill_price=Decimal(str(alpaca_order.filled_avg_price)) if alpaca_order.filled_avg_price else None,
            order_received_at=datetime.fromisoformat(alpaca_order.created_at.replace('Z', '+00:00')),
            execution_completed_at=datetime.fromisoformat(alpaca_order.filled_at.replace('Z', '+00:00')) if alpaca_order.filled_at else None,
            compliance_checked=True
        )
        
        # Add fill information
        if alpaca_order.filled_qty and alpaca_order.filled_avg_price:
            fill = OrderFill(
                fill_id=str(uuid.uuid4()),
                order_id=alpaca_order.id,
                symbol=trade.symbol,
                quantity=int(alpaca_order.filled_qty),
                price=Decimal(str(alpaca_order.filled_avg_price)),
                venue=ExecutionVenue.NYSE,  # Alpaca routes to various venues
                timestamp=datetime.fromisoformat(alpaca_order.filled_at.replace('Z', '+00:00')) if alpaca_order.filled_at else datetime.now(timezone.utc),
                commission=Decimal('0.00')  # Alpaca is commission-free
            )
            execution_report.add_fill(fill)
        
        return execution_report
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Alpaca account information"""
        loop = asyncio.get_event_loop()
        account = await loop.run_in_executor(None, self.api.get_account)
        
        return {
            'account_number': account.account_number,
            'status': account.status,
            'currency': account.currency,
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'equity': float(account.equity),
            'last_equity': float(account.last_equity),
            'multiplier': int(account.multiplier),
            'trading_blocked': account.trading_blocked,
            'pattern_day_trader': account.pattern_day_trader
        }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from Alpaca"""
        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(None, self.api.list_positions)
        
        return [
            {
                'symbol': pos.symbol,
                'quantity': int(pos.qty),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'current_price': float(pos.current_price),
                'avg_entry_price': float(pos.avg_entry_price)
            }
            for pos in positions
        ]
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Alpaca"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.api.cancel_order(order_id)
            )
            self.logger.info("Order cancelled successfully", order_id=order_id)
            return True
        except APIError as e:
            self.logger.error(f"Failed to cancel order: {e}", order_id=order_id)
            return False


# Global service instance
_alpaca_service: Optional[AlpacaTradingService] = None


async def get_alpaca_trading_service() -> AlpacaTradingService:
    """Get or create global Alpaca trading service instance"""
    global _alpaca_service
    
    if _alpaca_service is None:
        _alpaca_service = AlpacaTradingService()
    
    return _alpaca_service


async def cleanup_alpaca_trading_service() -> None:
    """Clean up the global AlpacaTradingService instance"""
    global _alpaca_service
    
    if _alpaca_service:
        _alpaca_service = None

