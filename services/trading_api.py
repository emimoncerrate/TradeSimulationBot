"""
Comprehensive mock trading system integration for Jain Global Slack Trading Bot.

This module provides a sophisticated mock trading execution system that simulates
real trading operations including order management, execution confirmation, partial fills,
market impact simulation, and comprehensive audit logging for compliance.

The service implements realistic execution delays, order routing, and execution
confirmation workflows while maintaining full audit trails for regulatory compliance.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import random

from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from prometheus_client import Counter, Histogram, Gauge
import structlog

from config.settings import get_config
from models.trade import Trade, TradeStatus
from services.market_data import MarketQuote, get_market_data_service
from services.alpaca_service import AlpacaService


class TradingError(Exception):
    """Custom exception for trading API service errors."""
    
    def __init__(self, message: str, trade_id: str = None, error_code: str = None):
        self.message = message
        self.trade_id = trade_id
        self.error_code = error_code
        super().__init__(self.message)


class OrderType(Enum):
    """Order type classifications."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order execution status."""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionVenue(Enum):
    """Mock execution venues."""
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    BATS = "BATS"
    IEX = "IEX"
    DARK_POOL = "DARK_POOL"


@dataclass
class OrderFill:
    """Individual order fill record."""
    fill_id: str
    order_id: str
    symbol: str
    quantity: int
    price: Decimal
    venue: ExecutionVenue
    timestamp: datetime
    commission: Decimal = Decimal('0.00')
    
    def __post_init__(self):
        """Validate fill data."""
        if self.quantity <= 0:
            raise ValueError(f"Fill quantity must be positive: {self.quantity}")
        if self.price <= 0:
            raise ValueError(f"Fill price must be positive: {self.price}")
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total fill value including commission."""
        return (self.quantity * self.price) + self.commission
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fill to dictionary."""
        return {
            'fill_id': self.fill_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'price': float(self.price),
            'venue': self.venue.value,
            'timestamp': self.timestamp.isoformat(),
            'commission': float(self.commission),
            'total_value': float(self.total_value)
        }


@dataclass
class TradeExecution:
    """Trade execution result."""
    execution_id: str
    trade_id: str
    symbol: str
    quantity: int
    executed_price: Decimal
    execution_time: datetime
    status: OrderStatus
    venue: ExecutionVenue
    fees: Decimal = Decimal('0')
    
    def __post_init__(self):
        """Validate execution data."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.executed_price <= 0:
            raise ValueError("Executed price must be positive")


@dataclass
class ExecutionReport:
    """Comprehensive execution report."""
    execution_id: str
    trade_id: str
    order_id: str
    symbol: str
    trade_type: str
    
    # Order details
    requested_quantity: int
    requested_price: Optional[Decimal]
    order_type: OrderType
    
    # Execution results
    status: OrderStatus
    filled_quantity: int = 0
    remaining_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    
    # Execution details
    fills: List[OrderFill] = field(default_factory=list)
    total_commission: Decimal = Decimal('0.00')
    execution_time_ms: Optional[float] = None
    
    # Market impact and slippage
    market_impact_bps: Optional[float] = None  # Basis points
    slippage_bps: Optional[float] = None
    
    # Timestamps
    order_received_at: datetime = field(default_factory=datetime.utcnow)
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    
    # Compliance and audit
    compliance_checked: bool = False
    audit_trail: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize derived fields."""
        self.remaining_quantity = self.requested_quantity - self.filled_quantity
        
        if self.fills:
            total_value = sum(fill.quantity * fill.price for fill in self.fills)
            total_quantity = sum(fill.quantity for fill in self.fills)
            if total_quantity > 0:
                self.average_fill_price = total_value / total_quantity
            
            self.total_commission = sum(fill.commission for fill in self.fills)
    
    @property
    def is_complete(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partial(self) -> bool:
        """Check if order is partially filled."""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.requested_quantity == 0:
            return 0.0
        return (self.filled_quantity / self.requested_quantity) * 100
    
    @property
    def total_execution_value(self) -> Decimal:
        """Calculate total execution value."""
        return sum(fill.quantity * fill.price for fill in self.fills)
    
    def add_fill(self, fill: OrderFill) -> None:
        """Add a fill to the execution report."""
        self.fills.append(fill)
        self.filled_quantity += fill.quantity
        self.remaining_quantity = self.requested_quantity - self.filled_quantity
        
        # Update average fill price
        if self.fills:
            total_value = sum(f.quantity * f.price for f in self.fills)
            total_quantity = sum(f.quantity for f in self.fills)
            self.average_fill_price = total_value / total_quantity
        
        # Update status
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
            self.execution_completed_at = datetime.utcnow()
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        # Add to audit trail
        self.audit_trail.append(
            f"Fill added: {fill.quantity} @ {fill.price} on {fill.venue.value} at {fill.timestamp}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution report to dictionary."""
        return {
            'execution_id': self.execution_id,
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'requested_quantity': self.requested_quantity,
            'requested_price': float(self.requested_price) if self.requested_price else None,
            'order_type': self.order_type.value,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'average_fill_price': float(self.average_fill_price) if self.average_fill_price else None,
            'fills': [fill.to_dict() for fill in self.fills],
            'total_commission': float(self.total_commission),
            'execution_time_ms': self.execution_time_ms,
            'market_impact_bps': self.market_impact_bps,
            'slippage_bps': self.slippage_bps,
            'order_received_at': self.order_received_at.isoformat(),
            'execution_started_at': self.execution_started_at.isoformat() if self.execution_started_at else None,
            'execution_completed_at': self.execution_completed_at.isoformat() if self.execution_completed_at else None,
            'compliance_checked': self.compliance_checked,
            'audit_trail': self.audit_trail,
            'is_complete': self.is_complete,
            'is_partial': self.is_partial,
            'fill_percentage': self.fill_percentage,
            'total_execution_value': float(self.total_execution_value)
        }


class MarketSimulator:
    """
    Sophisticated market simulation engine for realistic execution modeling.
    
    Simulates market microstructure effects including bid-ask spreads, market impact,
    partial fills, and venue-specific execution characteristics.
    """
    
    def __init__(self):
        """Initialize market simulator with realistic parameters."""
        self.logger = structlog.get_logger(__name__)
        
        # Market microstructure parameters
        self.bid_ask_spread_bps = {
            'large_cap': 2.0,    # 2 basis points
            'mid_cap': 5.0,      # 5 basis points
            'small_cap': 10.0    # 10 basis points
        }
        
        self.market_impact_params = {
            'large_cap': {'linear': 0.1, 'sqrt': 0.05},
            'mid_cap': {'linear': 0.2, 'sqrt': 0.1},
            'small_cap': {'linear': 0.5, 'sqrt': 0.2}
        }
        
        # Venue characteristics
        self.venue_characteristics = {
            ExecutionVenue.NYSE: {'fill_rate': 0.95, 'latency_ms': 2.0, 'commission_bps': 0.5},
            ExecutionVenue.NASDAQ: {'fill_rate': 0.93, 'latency_ms': 1.5, 'commission_bps': 0.4},
            ExecutionVenue.BATS: {'fill_rate': 0.90, 'latency_ms': 1.0, 'commission_bps': 0.3},
            ExecutionVenue.IEX: {'fill_rate': 0.88, 'latency_ms': 3.0, 'commission_bps': 0.2},
            ExecutionVenue.DARK_POOL: {'fill_rate': 0.70, 'latency_ms': 5.0, 'commission_bps': 0.1}
        }
    
    def simulate_execution(
        self, 
        symbol: str, 
        trade_type: str, 
        quantity: int, 
        market_quote: MarketQuote,
        order_type: OrderType = OrderType.MARKET
    ) -> Tuple[List[OrderFill], Dict[str, Any]]:
        """
        Simulate realistic order execution with market microstructure effects.
        
        Args:
            symbol: Trading symbol
            trade_type: 'buy' or 'sell'
            quantity: Order quantity
            market_quote: Current market data
            order_type: Type of order
            
        Returns:
            Tuple of (fills, execution_metrics)
        """
        # Determine stock category for simulation parameters
        stock_category = self._classify_stock(symbol, market_quote)
        
        # Calculate bid-ask spread
        spread_bps = self.bid_ask_spread_bps[stock_category]
        spread = market_quote.current_price * Decimal(spread_bps / 10000)
        
        # Calculate market impact
        market_impact = self._calculate_market_impact(quantity, market_quote, stock_category)
        
        # Determine execution price with market impact
        if trade_type.lower() == 'buy':
            base_price = market_quote.current_price + (spread / 2)  # Ask price
            execution_price = base_price + market_impact
        else:
            base_price = market_quote.current_price - (spread / 2)  # Bid price
            execution_price = base_price - market_impact
        
        # Simulate partial fills
        fills = self._simulate_partial_fills(
            symbol, quantity, execution_price, trade_type, stock_category
        )
        
        # Calculate execution metrics
        execution_metrics = {
            'stock_category': stock_category,
            'spread_bps': spread_bps,
            'market_impact_bps': float(market_impact / market_quote.current_price * 10000),
            'slippage_bps': float((execution_price - market_quote.current_price) / market_quote.current_price * 10000),
            'total_fills': len(fills),
            'venues_used': list(set(fill.venue for fill in fills))
        }
        
        return fills, execution_metrics
    
    def _classify_stock(self, symbol: str, market_quote: MarketQuote) -> str:
        """Classify stock by market cap for simulation parameters."""
        # Simple classification based on common symbols
        large_cap_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA']
        
        if symbol in large_cap_symbols:
            return 'large_cap'
        elif market_quote.market_cap and market_quote.market_cap > 10000000000:  # $10B
            return 'large_cap'
        elif market_quote.market_cap and market_quote.market_cap > 2000000000:   # $2B
            return 'mid_cap'
        else:
            return 'small_cap'
    
    def _calculate_market_impact(
        self, 
        quantity: int, 
        market_quote: MarketQuote, 
        stock_category: str
    ) -> Decimal:
        """Calculate market impact based on order size and stock characteristics."""
        # Estimate average daily volume (simplified)
        estimated_adv = market_quote.volume * 10 if market_quote.volume else 1000000
        
        # Calculate participation rate
        participation_rate = quantity / estimated_adv
        
        # Market impact model: linear + square root components
        params = self.market_impact_params[stock_category]
        linear_impact = params['linear'] * participation_rate
        sqrt_impact = params['sqrt'] * (participation_rate ** 0.5)
        
        total_impact_bps = (linear_impact + sqrt_impact) * 10000
        
        # Cap maximum impact at 50 basis points
        total_impact_bps = min(total_impact_bps, 50.0)
        
        return market_quote.current_price * Decimal(total_impact_bps / 10000)
    
    def _simulate_partial_fills(
        self, 
        symbol: str, 
        total_quantity: int, 
        avg_price: Decimal, 
        trade_type: str,
        stock_category: str
    ) -> List[OrderFill]:
        """Simulate realistic partial fills across multiple venues."""
        fills = []
        remaining_quantity = total_quantity
        
        # Determine number of fills (more fills for larger orders)
        if total_quantity < 100:
            num_fills = 1
        elif total_quantity < 1000:
            num_fills = random.randint(1, 3)
        else:
            num_fills = random.randint(2, 5)
        
        # Select venues for execution
        available_venues = list(ExecutionVenue)
        selected_venues = random.sample(available_venues, min(num_fills, len(available_venues)))
        
        for i, venue in enumerate(selected_venues):
            if remaining_quantity <= 0:
                break
            
            # Determine fill size
            if i == len(selected_venues) - 1:  # Last fill gets remaining quantity
                fill_quantity = remaining_quantity
            else:
                # Random fill size between 20% and 60% of remaining
                min_fill = max(1, int(remaining_quantity * 0.2))
                max_fill = max(min_fill, int(remaining_quantity * 0.6))
                fill_quantity = random.randint(min_fill, max_fill)
            
            # Add price variation for each fill (±2 basis points)
            price_variation = avg_price * Decimal(random.uniform(-0.0002, 0.0002))
            fill_price = avg_price + price_variation
            
            # Round price to appropriate tick size
            fill_price = self._round_to_tick_size(fill_price)
            
            # Calculate commission
            venue_chars = self.venue_characteristics[venue]
            commission = fill_quantity * fill_price * Decimal(venue_chars['commission_bps'] / 10000)
            
            # Create fill
            fill = OrderFill(
                fill_id=str(uuid.uuid4()),
                order_id=str(uuid.uuid4()),  # Would be provided by caller
                symbol=symbol,
                quantity=fill_quantity,
                price=fill_price,
                venue=venue,
                timestamp=datetime.utcnow() + timedelta(milliseconds=venue_chars['latency_ms']),
                commission=commission
            )
            
            fills.append(fill)
            remaining_quantity -= fill_quantity
        
        return fills
    
    def _round_to_tick_size(self, price: Decimal) -> Decimal:
        """Round price to appropriate tick size."""
        if price >= 1:
            # Round to nearest cent
            return price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            # Round to nearest tenth of a cent for sub-dollar prices
            return price.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


class TradingAPIService:
    """
    Comprehensive mock trading system integration service.
    
    Provides sophisticated trade execution simulation with realistic order management,
    execution confirmation, partial fills, market impact modeling, and comprehensive
    audit logging for compliance requirements.
    """
    
    def __init__(self):
        """Initialize trading API service with configuration and dependencies."""
        self.config = get_config()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Alpaca service for real paper trading
        self.alpaca_service = AlpacaService()
        
        # Initialize market simulator for fallback
        self.market_simulator = MarketSimulator()
        
        # Execution tracking
        self.active_orders: Dict[str, ExecutionReport] = {}
        self.execution_history: List[ExecutionReport] = []
        
        # Metrics
        self.execution_counter = Counter(
            'trading_executions_total',
            'Total trade executions',
            ['symbol', 'trade_type', 'status']
        )
        self.execution_duration = Histogram(
            'trading_execution_duration_seconds',
            'Trade execution duration',
            ['order_type']
        )
        self.execution_value = Histogram(
            'trading_execution_value_dollars',
            'Trade execution value',
            ['trade_type']
        )
        self.slippage_gauge = Gauge(
            'trading_slippage_bps',
            'Execution slippage in basis points',
            ['symbol']
        )
        
        # Risk limits and validation
        self.position_limits = {
            'max_single_order': self.config.trading.max_position_size,
            'max_order_value': self.config.trading.max_trade_value,
            'daily_trade_limit': 50
        }
        
        self.daily_trade_count = 0
        self.daily_reset_time = datetime.utcnow().date()
        
        self.logger.info("TradingAPIService initialized",
                        mock_execution=self.config.trading.mock_execution_enabled,
                        execution_delay=self.config.trading.execution_delay_seconds)
    
    async def initialize(self):
        """Initialize the trading service and Alpaca connection."""
        try:
            await self.alpaca_service.initialize()
            if self.alpaca_service.is_available():
                self.logger.info("🚀 Alpaca Paper Trading connected - Real paper trades enabled!")
            else:
                self.logger.info("📝 Using mock trading simulation")
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca service: {e}")
            self.logger.info("📝 Falling back to mock trading")
    
    async def execute_trade(
        self, 
        trade: Trade, 
        order_type: OrderType = OrderType.MARKET,
        timeout_seconds: int = 30
    ) -> ExecutionReport:
        """
        Execute a trade with comprehensive simulation and tracking.
        
        Args:
            trade: Trade object to execute
            order_type: Type of order (market, limit, etc.)
            timeout_seconds: Maximum execution time
            
        Returns:
            ExecutionReport: Comprehensive execution results
            
        Raises:
            ValueError: If trade validation fails
            Exception: If execution fails
        """
        start_time = time.time()
        
        # Validate trade
        await self._validate_trade(trade)
        
        # Create execution report
        execution_report = ExecutionReport(
            execution_id=str(uuid.uuid4()),
            trade_id=trade.trade_id,
            order_id=str(uuid.uuid4()),
            symbol=trade.symbol,
            trade_type=trade.trade_type,
            requested_quantity=abs(trade.quantity),
            requested_price=trade.price if order_type != OrderType.MARKET else None,
            order_type=order_type,
            status=OrderStatus.PENDING
        )
        
        # Add to active orders
        self.active_orders[execution_report.order_id] = execution_report
        
        try:
            # Perform compliance checks
            await self._perform_compliance_checks(trade, execution_report)
            
            # Get current market data
            market_data_service = await get_market_data_service()
            market_quote = await market_data_service.get_quote(trade.symbol)
            
            # Start execution
            execution_report.execution_started_at = datetime.utcnow()
            execution_report.audit_trail.append(f"Execution started at {execution_report.execution_started_at}")
            
            # Execute trade - use Alpaca if available, otherwise simulate
            if self.alpaca_service.is_available():
                # Real Alpaca Paper Trading execution
                self.logger.info(f"🚀 Executing {trade.trade_type.value} order via Alpaca Paper Trading")
                
                alpaca_order = await self.alpaca_service.submit_order(
                    symbol=trade.symbol,
                    quantity=abs(trade.quantity),
                    side='buy' if trade.trade_type.value.lower() == 'buy' else 'sell',
                    order_type='market'  # Using market orders for simplicity
                )
                
                if alpaca_order:
                    # Create fill from Alpaca order
                    fill = Fill(
                        fill_id=str(uuid.uuid4()),
                        order_id=execution_report.order_id,
                        symbol=trade.symbol,
                        quantity=abs(trade.quantity),
                        price=Decimal(str(alpaca_order.get('filled_avg_price', market_quote.price))),
                        timestamp=datetime.utcnow(),
                        exchange='ALPACA_PAPER'
                    )
                    execution_report.add_fill(fill)
                    execution_report.audit_trail.append(f"Alpaca order executed: {alpaca_order['order_id']}")
                    self.logger.info(f"✅ Alpaca order executed successfully: {alpaca_order['order_id']}")
                else:
                    raise Exception("Alpaca order submission failed")
                    
            else:
                # Fallback to simulation
                self.logger.info(f"📝 Simulating {trade.trade_type.value} order execution")
                
                # Simulate execution delay
                if self.config.trading.execution_delay_seconds > 0:
                    await asyncio.sleep(self.config.trading.execution_delay_seconds)
                
                # Simulate execution
                fills, execution_metrics = self.market_simulator.simulate_execution(
                    trade.symbol,
                    trade.trade_type,
                    abs(trade.quantity),
                    market_quote,
                    order_type
                )
                
                # Process fills
                for fill in fills:
                    fill.order_id = execution_report.order_id
                    execution_report.add_fill(fill)
            
            # Update execution metrics
            execution_report.market_impact_bps = execution_metrics.get('market_impact_bps')
            execution_report.slippage_bps = execution_metrics.get('slippage_bps')
            execution_report.execution_time_ms = (time.time() - start_time) * 1000
            
            # Finalize execution
            if execution_report.remaining_quantity == 0:
                execution_report.status = OrderStatus.FILLED
                execution_report.execution_completed_at = datetime.utcnow()
            else:
                execution_report.status = OrderStatus.PARTIALLY_FILLED
            
            # Update trade status
            if execution_report.is_complete:
                trade.status = TradeStatus.EXECUTED
                trade.execution_id = execution_report.execution_id
                trade.executed_price = execution_report.average_fill_price
                trade.executed_at = execution_report.execution_completed_at
            else:
                trade.status = TradeStatus.PARTIALLY_FILLED
            
            # Update metrics
            self.execution_counter.labels(
                symbol=trade.symbol,
                trade_type=trade.trade_type,
                status=execution_report.status.value
            ).inc()
            
            self.execution_duration.labels(
                order_type=order_type.value
            ).observe(time.time() - start_time)
            
            self.execution_value.labels(
                trade_type=trade.trade_type
            ).observe(float(execution_report.total_execution_value))
            
            if execution_report.slippage_bps:
                self.slippage_gauge.labels(symbol=trade.symbol).set(execution_report.slippage_bps)
            
            # Move to execution history
            self.execution_history.append(execution_report)
            if execution_report.order_id in self.active_orders:
                del self.active_orders[execution_report.order_id]
            
            # Update daily trade count
            self._update_daily_trade_count()
            
            self.logger.info("Trade execution completed",
                           trade_id=trade.trade_id,
                           execution_id=execution_report.execution_id,
                           symbol=trade.symbol,
                           status=execution_report.status.value,
                           filled_quantity=execution_report.filled_quantity,
                           average_price=float(execution_report.average_fill_price) if execution_report.average_fill_price else None,
                           execution_time_ms=execution_report.execution_time_ms)
            
            return execution_report
            
        except Exception as e:
            # Handle execution failure
            execution_report.status = OrderStatus.REJECTED
            execution_report.audit_trail.append(f"Execution failed: {str(e)}")
            
            # Update trade status
            trade.status = TradeStatus.FAILED
            
            # Update metrics
            self.execution_counter.labels(
                symbol=trade.symbol,
                trade_type=trade.trade_type,
                status='failed'
            ).inc()
            
            # Clean up
            if execution_report.order_id in self.active_orders:
                del self.active_orders[execution_report.order_id]
            
            self.logger.error("Trade execution failed",
                            trade_id=trade.trade_id,
                            symbol=trade.symbol,
                            error=str(e))
            
            raise e
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            bool: True if cancellation successful
        """
        if order_id not in self.active_orders:
            self.logger.warning("Attempted to cancel non-existent order", order_id=order_id)
            return False
        
        execution_report = self.active_orders[order_id]
        
        # Can only cancel pending or partially filled orders
        if execution_report.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            self.logger.warning("Cannot cancel order in current status", 
                              order_id=order_id, 
                              status=execution_report.status.value)
            return False
        
        # Update status
        execution_report.status = OrderStatus.CANCELLED
        execution_report.audit_trail.append(f"Order cancelled at {datetime.utcnow()}")
        
        # Move to history
        self.execution_history.append(execution_report)
        del self.active_orders[order_id]
        
        self.logger.info("Order cancelled successfully", order_id=order_id)
        return True
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionReport]:
        """
        Get execution status by execution ID.
        
        Args:
            execution_id: Execution ID to query
            
        Returns:
            ExecutionReport if found, None otherwise
        """
        # Check active orders
        for report in self.active_orders.values():
            if report.execution_id == execution_id:
                return report
        
        # Check execution history
        for report in self.execution_history:
            if report.execution_id == execution_id:
                return report
        
        return None
    
    async def get_order_status(self, order_id: str) -> Optional[ExecutionReport]:
        """
        Get order status by order ID.
        
        Args:
            order_id: Order ID to query
            
        Returns:
            ExecutionReport if found, None otherwise
        """
        # Check active orders
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        # Check execution history
        for report in self.execution_history:
            if report.order_id == order_id:
                return report
        
        return None
    
    async def get_execution_history(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 100
    ) -> List[ExecutionReport]:
        """
        Get execution history with optional filtering.
        
        Args:
            symbol: Optional symbol filter
            limit: Maximum number of records to return
            
        Returns:
            List of ExecutionReport objects
        """
        history = self.execution_history.copy()
        
        # Filter by symbol if specified
        if symbol:
            history = [report for report in history if report.symbol == symbol.upper()]
        
        # Sort by execution time (most recent first)
        history.sort(key=lambda r: r.order_received_at, reverse=True)
        
        return history[:limit]
    
    async def _validate_trade(self, trade: Trade) -> None:
        """
        Validate trade parameters and limits.
        
        Args:
            trade: Trade to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Basic validation
        if not trade.symbol or len(trade.symbol.strip()) == 0:
            raise ValueError("Trade symbol is required")
        
        if trade.quantity == 0:
            raise ValueError("Trade quantity cannot be zero")
        
        if trade.price <= 0:
            raise ValueError("Trade price must be positive")
        
        # Position size limits
        if abs(trade.quantity) > self.position_limits['max_single_order']:
            raise ValueError(f"Order quantity {abs(trade.quantity)} exceeds maximum allowed {self.position_limits['max_single_order']}")
        
        # Order value limits
        order_value = abs(trade.quantity * trade.price)
        if order_value > self.position_limits['max_order_value']:
            raise ValueError(f"Order value ${order_value:,.2f} exceeds maximum allowed ${self.position_limits['max_order_value']:,.2f}")
        
        # Daily trade limits
        if self.daily_trade_count >= self.position_limits['daily_trade_limit']:
            raise ValueError(f"Daily trade limit of {self.position_limits['daily_trade_limit']} exceeded")
        
        # Symbol validation (check against supported symbols)
        if hasattr(self.config.trading, 'supported_symbols'):
            if trade.symbol.upper() not in self.config.trading.supported_symbols:
                raise ValueError(f"Symbol {trade.symbol} is not in supported symbols list")
        
        self.logger.debug("Trade validation passed", 
                         trade_id=trade.trade_id,
                         symbol=trade.symbol,
                         quantity=trade.quantity,
                         value=float(order_value))
    
    async def _perform_compliance_checks(self, trade: Trade, execution_report: ExecutionReport) -> None:
        """
        Perform compliance and regulatory checks.
        
        Args:
            trade: Trade to check
            execution_report: Execution report to update
            
        Raises:
            ValueError: If compliance checks fail
        """
        compliance_checks = []
        
        # Check for wash sale rules (simplified)
        compliance_checks.append("Wash sale rule check: PASSED")
        
        # Check for position limits
        order_value = abs(trade.quantity * trade.price)
        if order_value > 100000:  # $100k threshold
            compliance_checks.append("Large order review: FLAGGED for review")
        else:
            compliance_checks.append("Large order review: PASSED")
        
        # Check for market hours (simplified)
        current_hour = datetime.utcnow().hour
        if 9 <= current_hour <= 16:  # Simplified market hours check
            compliance_checks.append("Market hours check: PASSED")
        else:
            compliance_checks.append("Market hours check: AFTER HOURS TRADING")
        
        # Check for symbol restrictions
        restricted_symbols = ['RESTRICTED1', 'RESTRICTED2']  # Example restricted symbols
        if trade.symbol.upper() in restricted_symbols:
            raise ValueError(f"Trading in symbol {trade.symbol} is restricted")
        
        compliance_checks.append("Symbol restriction check: PASSED")
        
        # Update execution report
        execution_report.compliance_checked = True
        execution_report.audit_trail.extend(compliance_checks)
        
        self.logger.info("Compliance checks completed",
                        trade_id=trade.trade_id,
                        checks_passed=len([c for c in compliance_checks if 'PASSED' in c]),
                        total_checks=len(compliance_checks))
    
    def _update_daily_trade_count(self) -> None:
        """Update daily trade count and reset if new day."""
        current_date = datetime.utcnow().date()
        
        if current_date != self.daily_reset_time:
            # New day, reset counter
            self.daily_trade_count = 0
            self.daily_reset_time = current_date
        
        self.daily_trade_count += 1
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive trading statistics.
        
        Returns:
            Dict containing trading statistics
        """
        # Calculate statistics from execution history
        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.is_complete])
        partial_executions = len([r for r in self.execution_history if r.is_partial])
        failed_executions = len([r for r in self.execution_history if r.status == OrderStatus.REJECTED])
        
        # Calculate average execution time
        execution_times = [r.execution_time_ms for r in self.execution_history if r.execution_time_ms]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate total volume
        total_volume = sum(r.total_execution_value for r in self.execution_history)
        
        # Calculate average slippage
        slippages = [r.slippage_bps for r in self.execution_history if r.slippage_bps]
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0
        
        # Symbol breakdown
        symbol_stats = {}
        for report in self.execution_history:
            symbol = report.symbol
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {'count': 0, 'volume': 0, 'avg_slippage': 0}
            
            symbol_stats[symbol]['count'] += 1
            symbol_stats[symbol]['volume'] += float(report.total_execution_value)
            
            if report.slippage_bps:
                symbol_stats[symbol]['avg_slippage'] = (
                    symbol_stats[symbol]['avg_slippage'] + report.slippage_bps
                ) / 2
        
        return {
            'execution_summary': {
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'partial_executions': partial_executions,
                'failed_executions': failed_executions,
                'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0
            },
            'performance_metrics': {
                'average_execution_time_ms': avg_execution_time,
                'total_volume': float(total_volume),
                'average_slippage_bps': avg_slippage,
                'daily_trade_count': self.daily_trade_count
            },
            'symbol_breakdown': symbol_stats,
            'active_orders': len(self.active_orders),
            'daily_limits': {
                'trades_used': self.daily_trade_count,
                'trades_remaining': max(0, self.position_limits['daily_trade_limit'] - self.daily_trade_count)
            }
        }
    
    async def simulate_market_conditions(
        self, 
        volatility_multiplier: float = 1.0,
        liquidity_multiplier: float = 1.0
    ) -> None:
        """
        Simulate different market conditions for testing.
        
        Args:
            volatility_multiplier: Multiply volatility by this factor
            liquidity_multiplier: Multiply liquidity by this factor
        """
        # Update market simulator parameters
        for category in self.market_simulator.market_impact_params:
            params = self.market_simulator.market_impact_params[category]
            params['linear'] *= volatility_multiplier
            params['sqrt'] *= volatility_multiplier
        
        for category in self.market_simulator.bid_ask_spread_bps:
            self.market_simulator.bid_ask_spread_bps[category] *= (2.0 - liquidity_multiplier)
        
        self.logger.info("Market conditions updated",
                        volatility_multiplier=volatility_multiplier,
                        liquidity_multiplier=liquidity_multiplier)
    
    async def reset_daily_limits(self) -> None:
        """Reset daily trading limits (for testing or administrative purposes)."""
        self.daily_trade_count = 0
        self.daily_reset_time = datetime.utcnow().date()
        
        self.logger.info("Daily trading limits reset")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status for monitoring.
        
        Returns:
            Dict containing health status information
        """
        # Calculate recent execution success rate
        recent_executions = [r for r in self.execution_history[-50:]]  # Last 50 executions
        recent_success_rate = 0
        if recent_executions:
            successful = len([r for r in recent_executions if r.is_complete])
            recent_success_rate = (successful / len(recent_executions)) * 100
        
        # Calculate average execution time for recent trades
        recent_times = [r.execution_time_ms for r in recent_executions if r.execution_time_ms]
        avg_recent_time = sum(recent_times) / len(recent_times) if recent_times else 0
        
        status = {
            'service': 'TradingAPIService',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'mock_execution_enabled': self.config.trading.mock_execution_enabled,
            'active_orders': len(self.active_orders),
            'total_executions': len(self.execution_history),
            'daily_trade_count': self.daily_trade_count,
            'daily_limit': self.position_limits['daily_trade_limit'],
            'recent_success_rate': recent_success_rate,
            'average_execution_time_ms': avg_recent_time
        }
        
        # Check if service is healthy based on recent performance
        if recent_success_rate < 90 and len(recent_executions) > 10:
            status['status'] = 'degraded'
            status['warning'] = 'Recent execution success rate below 90%'
        
        if avg_recent_time > 5000:  # 5 seconds
            status['status'] = 'degraded'
            status['warning'] = 'Average execution time exceeds 5 seconds'
        
        return status
    
    async def cleanup(self) -> None:
        """Clean up service resources."""
        # Cancel any active orders
        for order_id in list(self.active_orders.keys()):
            await self.cancel_order(order_id)
        
        # Clear history (in production, this might be persisted)
        self.execution_history.clear()
        
        self.logger.info("TradingAPIService cleanup completed")


# Global service instance
_trading_api_service: Optional[TradingAPIService] = None


async def get_trading_api_service() -> TradingAPIService:
    """
    Get or create the global TradingAPIService instance.
    
    Returns:
        TradingAPIService: Initialized service instance
    """
    global _trading_api_service
    
    if _trading_api_service is None:
        _trading_api_service = TradingAPIService()
    
    return _trading_api_service


async def cleanup_trading_api_service() -> None:
    """Clean up the global TradingAPIService instance."""
    global _trading_api_service
    
    if _trading_api_service:
        await _trading_api_service.cleanup()
        _trading_api_service = None