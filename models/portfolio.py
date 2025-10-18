"""
Portfolio and Position models with P&L calculations, risk metrics, and portfolio analytics.

This module provides comprehensive portfolio management models with position tracking,
P&L calculations, risk metrics, and advanced portfolio analytics for the Slack Trading Bot.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import statistics
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)


class PositionType(Enum):
    """Enumeration for position types."""
    LONG = "long"
    SHORT = "short"


class PortfolioStatus(Enum):
    """Enumeration for portfolio status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    LIQUIDATING = "liquidating"


class RiskMetricType(Enum):
    """Enumeration for risk metric types."""
    VALUE_AT_RISK = "value_at_risk"
    BETA = "beta"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"


class PortfolioValidationError(Exception):
    """Custom exception for portfolio validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


@dataclass
class Position:
    """
    Individual position within a portfolio with comprehensive tracking and analytics.
    
    This class represents a single position (holding) in a security with full
    tracking of cost basis, current value, P&L calculations, and risk metrics.
    
    Attributes:
        user_id: Owner of the position
        symbol: Stock symbol
        quantity: Number of shares (positive for long, negative for short)
        average_cost: Average cost basis per share
        current_price: Current market price per share
        position_type: Long or short position
        opened_date: When position was first opened
        last_updated: Last update timestamp
        realized_pnl: Realized profit/loss from closed portions
        unrealized_pnl: Current unrealized profit/loss
        total_cost: Total cost basis of position
        current_value: Current market value of position
        day_change: Change in value since previous day
        day_change_percent: Percentage change since previous day
        trade_history: List of trade IDs that contributed to this position
        dividends_received: Total dividends received
        commission_paid: Total commission paid on this position
        risk_metrics: Dictionary of calculated risk metrics
        notes: Additional notes about the position
    """
    
    # Required fields
    user_id: str
    symbol: str
    quantity: int
    average_cost: Decimal
    current_price: Decimal
    
    # Position details
    position_type: PositionType = field(default=PositionType.LONG)
    opened_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # P&L tracking
    realized_pnl: Decimal = field(default_factory=lambda: Decimal('0.00'))
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal('0.00'))
    total_cost: Decimal = field(default_factory=lambda: Decimal('0.00'))
    current_value: Decimal = field(default_factory=lambda: Decimal('0.00'))
    
    # Daily tracking
    day_change: Decimal = field(default_factory=lambda: Decimal('0.00'))
    day_change_percent: Decimal = field(default_factory=lambda: Decimal('0.00'))
    
    # Additional tracking
    trade_history: List[str] = field(default_factory=list)
    dividends_received: Decimal = field(default_factory=lambda: Decimal('0.00'))
    commission_paid: Decimal = field(default_factory=lambda: Decimal('0.00'))
    risk_metrics: Dict[str, Decimal] = field(default_factory=dict)
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization calculations and validation."""
        try:
            self.validate()
            self.calculate_values()
            logger.debug(f"Position created for {self.symbol}: {self.quantity} shares")
        except PortfolioValidationError as e:
            logger.error(f"Position validation failed: {e.message}")
            raise
    
    def validate(self) -> None:
        """
        Validate position data.
        
        Raises:
            PortfolioValidationError: If validation fails
        """
        if not self.user_id or not isinstance(self.user_id, str):
            raise PortfolioValidationError("User ID must be a non-empty string", "user_id")
        
        if not self.symbol or not isinstance(self.symbol, str):
            raise PortfolioValidationError("Symbol must be a non-empty string", "symbol")
        
        self.symbol = self.symbol.strip().upper()
        
        if not isinstance(self.quantity, int):
            raise PortfolioValidationError("Quantity must be an integer", "quantity")
        
        if self.quantity == 0:
            raise PortfolioValidationError("Quantity cannot be zero", "quantity")
        
        # Set position type based on quantity
        self.position_type = PositionType.LONG if self.quantity > 0 else PositionType.SHORT
        
        # Validate prices
        for field_name, value in [("average_cost", self.average_cost), ("current_price", self.current_price)]:
            if not isinstance(value, Decimal):
                try:
                    setattr(self, field_name, Decimal(str(value)))
                except:
                    raise PortfolioValidationError(f"{field_name} must be a valid decimal", field_name)
            
            if getattr(self, field_name) <= 0:
                raise PortfolioValidationError(f"{field_name} must be positive", field_name)
    
    def calculate_values(self) -> None:
        """Calculate all derived values for the position."""
        abs_quantity = abs(self.quantity)
        
        # Calculate total cost and current value
        self.total_cost = self.average_cost * Decimal(str(abs_quantity))
        self.current_value = self.current_price * Decimal(str(abs_quantity))
        
        # Calculate unrealized P&L
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = self.current_value - self.total_cost
        else:  # SHORT position
            self.unrealized_pnl = self.total_cost - self.current_value
        
        # Update timestamp
        self.last_updated = datetime.now(timezone.utc)
    
    def update_price(self, new_price: Decimal, previous_price: Optional[Decimal] = None) -> None:
        """
        Update current price and recalculate values.
        
        Args:
            new_price: New market price
            previous_price: Previous price for day change calculation
        """
        if previous_price is None:
            previous_price = self.current_price
        
        self.current_price = new_price
        
        # Calculate day change
        if previous_price > 0:
            abs_quantity = abs(self.quantity)
            old_value = previous_price * Decimal(str(abs_quantity))
            new_value = new_price * Decimal(str(abs_quantity))
            
            self.day_change = new_value - old_value
            self.day_change_percent = (self.day_change / old_value * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        self.calculate_values()
    
    def add_trade(self, trade_id: str, quantity: int, price: Decimal, commission: Decimal = Decimal('0.00')) -> None:
        """
        Add a trade to this position and update cost basis.
        
        Args:
            trade_id: ID of the trade
            quantity: Quantity traded (positive for buy, negative for sell)
            price: Trade price per share
            commission: Commission paid
        """
        self.trade_history.append(trade_id)
        self.commission_paid += commission
        
        old_quantity = self.quantity
        new_quantity = old_quantity + quantity
        
        if old_quantity == 0:
            # Opening new position
            self.quantity = new_quantity
            self.average_cost = price
            self.opened_date = datetime.now(timezone.utc)
        elif (old_quantity > 0 and quantity > 0) or (old_quantity < 0 and quantity < 0):
            # Adding to existing position
            old_cost_basis = self.average_cost * Decimal(str(abs(old_quantity)))
            new_cost_basis = price * Decimal(str(abs(quantity)))
            total_cost_basis = old_cost_basis + new_cost_basis
            
            self.quantity = new_quantity
            if new_quantity != 0:
                self.average_cost = total_cost_basis / Decimal(str(abs(new_quantity)))
        else:
            # Reducing or closing position
            if abs(quantity) >= abs(old_quantity):
                # Closing entire position or reversing
                realized_pnl_per_share = price - self.average_cost
                if old_quantity < 0:  # Short position
                    realized_pnl_per_share = self.average_cost - price
                
                self.realized_pnl += realized_pnl_per_share * Decimal(str(abs(old_quantity)))
                
                if abs(quantity) > abs(old_quantity):
                    # Reversing position
                    remaining_quantity = quantity + old_quantity
                    self.quantity = remaining_quantity
                    self.average_cost = price
                else:
                    # Closing position
                    self.quantity = 0
            else:
                # Partial close
                close_quantity = abs(quantity)
                realized_pnl_per_share = price - self.average_cost
                if old_quantity < 0:  # Short position
                    realized_pnl_per_share = self.average_cost - price
                
                self.realized_pnl += realized_pnl_per_share * Decimal(str(close_quantity))
                self.quantity = new_quantity
        
        self.calculate_values()
        logger.info(f"Trade {trade_id} added to position {self.symbol}: {quantity} shares at ${price}")
    
    def get_total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    def get_pnl_percentage(self) -> Decimal:
        """Get P&L as percentage of cost basis."""
        if self.total_cost == 0:
            return Decimal('0.00')
        
        return (self.get_total_pnl() / self.total_cost * Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        return self.get_total_pnl() > 0
    
    def is_closed(self) -> bool:
        """Check if position is closed (quantity = 0)."""
        return self.quantity == 0
    
    def get_holding_period_days(self) -> int:
        """Get number of days position has been held."""
        return (datetime.now(timezone.utc) - self.opened_date).days
    
    def calculate_risk_metrics(self, market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Decimal]:
        """
        Calculate risk metrics for the position.
        
        Args:
            market_data: Optional market data for calculations
            
        Returns:
            Dictionary of risk metrics
        """
        metrics = {}
        
        # Position size as percentage of portfolio (would need portfolio value)
        if market_data and 'portfolio_value' in market_data:
            portfolio_value = Decimal(str(market_data['portfolio_value']))
            if portfolio_value > 0:
                metrics['position_weight'] = (abs(self.current_value) / portfolio_value * Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
        
        # Volatility estimate (simplified)
        if market_data and 'price_history' in market_data:
            price_history = [Decimal(str(p)) for p in market_data['price_history']]
            if len(price_history) > 1:
                returns = []
                for i in range(1, len(price_history)):
                    ret = (price_history[i] - price_history[i-1]) / price_history[i-1]
                    returns.append(float(ret))
                
                if returns:
                    volatility = Decimal(str(statistics.stdev(returns) * 100)).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    metrics['volatility'] = volatility
        
        self.risk_metrics.update(metrics)
        return metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary."""
        data = asdict(self)
        
        # Convert enums and decimals
        data['position_type'] = self.position_type.value
        
        # Convert Decimal fields to strings
        decimal_fields = ['average_cost', 'current_price', 'realized_pnl', 'unrealized_pnl',
                         'total_cost', 'current_value', 'day_change', 'day_change_percent',
                         'dividends_received', 'commission_paid']
        
        for field in decimal_fields:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Convert risk metrics
        if 'risk_metrics' in data:
            data['risk_metrics'] = {k: str(v) for k, v in data['risk_metrics'].items()}
        
        # Convert datetime fields
        datetime_fields = ['opened_date', 'last_updated']
        for field in datetime_fields:
            if field in data and data[field] is not None:
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """
        Create Position instance from dictionary.
        
        Args:
            data: Dictionary containing position data
            
        Returns:
            Position instance
            
        Raises:
            PortfolioValidationError: If data is invalid
        """
        try:
            # Convert enums back
            if 'position_type' in data and isinstance(data['position_type'], str):
                data['position_type'] = PositionType(data['position_type'])
            
            # Convert quantity to int if it's a string
            if 'quantity' in data and data['quantity'] is not None:
                data['quantity'] = int(data['quantity'])
            
            # Convert Decimal fields back
            decimal_fields = ['average_cost', 'current_price', 'realized_pnl', 'unrealized_pnl',
                             'total_cost', 'current_value', 'day_change', 'day_change_percent',
                             'dividends_received', 'commission_paid']
            
            for field in decimal_fields:
                if field in data and data[field] is not None:
                    data[field] = Decimal(str(data[field]))
            
            # Convert risk metrics back
            if 'risk_metrics' in data:
                data['risk_metrics'] = {k: Decimal(str(v)) for k, v in data['risk_metrics'].items()}
            
            # Convert datetime fields back
            datetime_fields = ['opened_date', 'last_updated']
            for field in datetime_fields:
                if field in data and data[field] is not None:
                    if isinstance(data[field], str):
                        data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            
            return cls(**data)
            
        except (ValueError, TypeError, KeyError) as e:
            raise PortfolioValidationError(f"Failed to create Position from dict: {str(e)}")


@dataclass
class Portfolio:
    """
    Comprehensive portfolio with positions, analytics, and risk management.
    
    This class represents a complete portfolio with position tracking, P&L calculations,
    risk metrics, performance analytics, and portfolio management capabilities.
    
    Attributes:
        user_id: Portfolio owner
        portfolio_id: Unique portfolio identifier
        name: Portfolio name
        status: Current portfolio status
        positions: Dictionary of positions by symbol
        cash_balance: Available cash balance
        total_value: Total portfolio value (positions + cash)
        total_cost_basis: Total cost basis of all positions
        total_pnl: Total profit/loss (realized + unrealized)
        day_change: Portfolio change since previous day
        day_change_percent: Percentage change since previous day
        inception_date: When portfolio was created
        last_updated: Last update timestamp
        performance_history: Historical performance data
        risk_metrics: Portfolio-level risk metrics
        benchmark_symbol: Benchmark for comparison (e.g., 'SPY')
        settings: Portfolio settings and preferences
        metadata: Additional portfolio metadata
    """
    
    # Required fields
    user_id: str
    portfolio_id: str
    name: str
    
    # Portfolio status and positions
    status: PortfolioStatus = field(default=PortfolioStatus.ACTIVE)
    positions: Dict[str, Position] = field(default_factory=dict)
    
    # Financial data
    cash_balance: Decimal = field(default_factory=lambda: Decimal('100000.00'))  # Default $100k
    total_value: Decimal = field(default_factory=lambda: Decimal('0.00'))
    total_cost_basis: Decimal = field(default_factory=lambda: Decimal('0.00'))
    total_pnl: Decimal = field(default_factory=lambda: Decimal('0.00'))
    
    # Daily tracking
    day_change: Decimal = field(default_factory=lambda: Decimal('0.00'))
    day_change_percent: Decimal = field(default_factory=lambda: Decimal('0.00'))
    
    # Timestamps
    inception_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Analytics and history
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    risk_metrics: Dict[str, Decimal] = field(default_factory=dict)
    benchmark_symbol: str = "SPY"
    
    # Settings and metadata
    settings: Dict[str, Any] = field(default_factory=lambda: {
        "auto_rebalance": False,
        "risk_tolerance": "medium",
        "max_position_size": "10.0",  # Percentage
        "stop_loss_enabled": False,
        "take_profit_enabled": False
    })
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and calculations."""
        try:
            self.validate()
            self.calculate_portfolio_values()
            logger.info(f"Portfolio {self.portfolio_id} created for user {self.user_id}")
        except PortfolioValidationError as e:
            logger.error(f"Portfolio validation failed: {e.message}")
            raise
    
    def validate(self) -> None:
        """Validate portfolio data."""
        if not self.user_id or not isinstance(self.user_id, str):
            raise PortfolioValidationError("User ID must be a non-empty string", "user_id")
        
        if not self.portfolio_id or not isinstance(self.portfolio_id, str):
            raise PortfolioValidationError("Portfolio ID must be a non-empty string", "portfolio_id")
        
        if not self.name or not isinstance(self.name, str):
            raise PortfolioValidationError("Portfolio name must be a non-empty string", "name")
        
        if not isinstance(self.cash_balance, Decimal):
            try:
                self.cash_balance = Decimal(str(self.cash_balance))
            except:
                raise PortfolioValidationError("Cash balance must be a valid decimal", "cash_balance")
    
    def calculate_portfolio_values(self) -> None:
        """Calculate all portfolio-level values and metrics."""
        total_position_value = Decimal('0.00')
        total_position_cost = Decimal('0.00')
        total_realized_pnl = Decimal('0.00')
        total_unrealized_pnl = Decimal('0.00')
        
        for position in self.positions.values():
            if not position.is_closed():
                total_position_value += abs(position.current_value)
                total_position_cost += abs(position.total_cost)
            
            total_realized_pnl += position.realized_pnl
            total_unrealized_pnl += position.unrealized_pnl
        
        self.total_value = self.cash_balance + total_position_value
        self.total_cost_basis = total_position_cost
        self.total_pnl = total_realized_pnl + total_unrealized_pnl
        self.last_updated = datetime.now(timezone.utc)
    
    def add_position(self, position: Position) -> None:
        """
        Add a position to the portfolio.
        
        Args:
            position: Position to add
        """
        if position.user_id != self.user_id:
            raise PortfolioValidationError("Position user_id must match portfolio user_id")
        
        self.positions[position.symbol] = position
        self.calculate_portfolio_values()
        logger.info(f"Position {position.symbol} added to portfolio {self.portfolio_id}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position by symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position or None if not found
        """
        return self.positions.get(symbol.upper())
    
    def has_position(self, symbol: str) -> bool:
        """Check if portfolio has a position in symbol."""
        position = self.get_position(symbol)
        return position is not None and not position.is_closed()
    
    def update_position_price(self, symbol: str, new_price: Decimal, previous_price: Optional[Decimal] = None) -> None:
        """
        Update price for a specific position.
        
        Args:
            symbol: Stock symbol
            new_price: New market price
            previous_price: Previous price for day change calculation
        """
        position = self.get_position(symbol)
        if position:
            position.update_price(new_price, previous_price)
            self.calculate_portfolio_values()
    
    def update_all_prices(self, price_data: Dict[str, Decimal], previous_prices: Optional[Dict[str, Decimal]] = None) -> None:
        """
        Update prices for all positions.
        
        Args:
            price_data: Dictionary of symbol -> price
            previous_prices: Dictionary of symbol -> previous price
        """
        for symbol, new_price in price_data.items():
            previous_price = previous_prices.get(symbol) if previous_prices else None
            self.update_position_price(symbol, new_price, previous_price)
    
    def execute_trade(self, symbol: str, quantity: int, price: Decimal, trade_id: str, 
                     commission: Decimal = Decimal('0.00')) -> None:
        """
        Execute a trade and update portfolio.
        
        Args:
            symbol: Stock symbol
            quantity: Quantity to trade (positive for buy, negative for sell)
            price: Trade price
            trade_id: Trade identifier
            commission: Commission paid
        """
        symbol = symbol.upper()
        trade_value = abs(quantity) * price + commission
        
        # Check cash balance for buy orders
        if quantity > 0 and trade_value > self.cash_balance:
            raise PortfolioValidationError(f"Insufficient cash balance: ${self.cash_balance} < ${trade_value}")
        
        # Get or create position
        position = self.get_position(symbol)
        if position is None:
            # Create new position
            position = Position(
                user_id=self.user_id,
                symbol=symbol,
                quantity=0,
                average_cost=price,
                current_price=price
            )
            self.positions[symbol] = position
        
        # Update cash balance
        if quantity > 0:  # Buy
            self.cash_balance -= trade_value
        else:  # Sell
            self.cash_balance += trade_value - commission
        
        # Add trade to position
        position.add_trade(trade_id, quantity, price, commission)
        
        # Remove position if closed
        if position.is_closed():
            del self.positions[symbol]
        
        self.calculate_portfolio_values()
        logger.info(f"Trade executed: {quantity} shares of {symbol} at ${price}")
    
    def get_active_positions(self) -> List[Position]:
        """Get list of active (non-zero) positions."""
        return [pos for pos in self.positions.values() if not pos.is_closed()]
    
    def get_top_positions(self, limit: int = 10) -> List[Position]:
        """
        Get top positions by value.
        
        Args:
            limit: Maximum number of positions to return
            
        Returns:
            List of positions sorted by value (descending)
        """
        active_positions = self.get_active_positions()
        return sorted(active_positions, key=lambda p: abs(p.current_value), reverse=True)[:limit]
    
    def get_portfolio_allocation(self) -> Dict[str, Decimal]:
        """
        Get portfolio allocation by symbol.
        
        Returns:
            Dictionary of symbol -> percentage allocation
        """
        allocation = {}
        total_position_value = sum(abs(pos.current_value) for pos in self.get_active_positions())
        
        if total_position_value > 0:
            for position in self.get_active_positions():
                allocation[position.symbol] = (
                    abs(position.current_value) / total_position_value * Decimal('100')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return allocation
    
    def calculate_portfolio_risk_metrics(self) -> Dict[str, Decimal]:
        """Calculate comprehensive portfolio risk metrics."""
        metrics = {}
        active_positions = self.get_active_positions()
        
        if not active_positions:
            return metrics
        
        # Portfolio concentration (largest position percentage)
        allocations = list(self.get_portfolio_allocation().values())
        if allocations:
            metrics['max_position_weight'] = max(allocations)
            metrics['portfolio_concentration'] = sum(sorted(allocations, reverse=True)[:5])  # Top 5 positions
        
        # Number of positions
        metrics['position_count'] = Decimal(str(len(active_positions)))
        
        # Cash allocation
        if self.total_value > 0:
            metrics['cash_allocation'] = (self.cash_balance / self.total_value * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        # P&L metrics
        if self.total_cost_basis > 0:
            metrics['total_return_pct'] = (self.total_pnl / self.total_cost_basis * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        # Profitable positions ratio
        profitable_positions = sum(1 for pos in active_positions if pos.is_profitable())
        metrics['profitable_positions_pct'] = (
            Decimal(str(profitable_positions)) / Decimal(str(len(active_positions))) * Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        self.risk_metrics.update(metrics)
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            'total_value': float(self.total_value),
            'cash_balance': float(self.cash_balance),
            'total_pnl': float(self.total_pnl),
            'total_pnl_pct': float(self.total_pnl / self.total_cost_basis * 100) if self.total_cost_basis > 0 else 0.0,
            'day_change': float(self.day_change),
            'day_change_pct': float(self.day_change_percent),
            'position_count': len(self.get_active_positions()),
            'largest_position': max((abs(pos.current_value) for pos in self.get_active_positions()), default=0.0),
            'inception_date': self.inception_date.isoformat(),
            'days_active': (datetime.now(timezone.utc) - self.inception_date).days
        }
    
    def record_daily_snapshot(self) -> None:
        """Record daily portfolio snapshot for performance tracking."""
        snapshot = {
            'date': datetime.now(timezone.utc).date().isoformat(),
            'total_value': float(self.total_value),
            'cash_balance': float(self.cash_balance),
            'total_pnl': float(self.total_pnl),
            'position_count': len(self.get_active_positions()),
            'risk_metrics': {k: float(v) for k, v in self.risk_metrics.items()}
        }
        
        self.performance_history.append(snapshot)
        
        # Keep only last 365 days
        if len(self.performance_history) > 365:
            self.performance_history = self.performance_history[-365:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert portfolio to dictionary."""
        data = asdict(self)
        
        # Convert enums
        data['status'] = self.status.value
        
        # Convert positions
        data['positions'] = {symbol: pos.to_dict() for symbol, pos in self.positions.items()}
        
        # Convert Decimal fields
        decimal_fields = ['cash_balance', 'total_value', 'total_cost_basis', 'total_pnl',
                         'day_change', 'day_change_percent']
        
        for field in decimal_fields:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Convert risk metrics
        if 'risk_metrics' in data:
            data['risk_metrics'] = {k: str(v) for k, v in data['risk_metrics'].items()}
        
        # Convert datetime fields
        datetime_fields = ['inception_date', 'last_updated']
        for field in datetime_fields:
            if field in data and data[field] is not None:
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Portfolio':
        """Create Portfolio from dictionary."""
        try:
            # Convert positions back
            if 'positions' in data:
                positions = {}
                for symbol, pos_data in data['positions'].items():
                    positions[symbol] = Position.from_dict(pos_data)
                data['positions'] = positions
            
            # Convert enums back
            if 'status' in data and isinstance(data['status'], str):
                data['status'] = PortfolioStatus(data['status'])
            
            # Convert Decimal fields back
            decimal_fields = ['cash_balance', 'total_value', 'total_cost_basis', 'total_pnl',
                             'day_change', 'day_change_percent']
            
            for field in decimal_fields:
                if field in data and data[field] is not None:
                    data[field] = Decimal(str(data[field]))
            
            # Convert risk metrics back
            if 'risk_metrics' in data:
                data['risk_metrics'] = {k: Decimal(str(v)) for k, v in data['risk_metrics'].items()}
            
            # Convert datetime fields back
            datetime_fields = ['inception_date', 'last_updated']
            for field in datetime_fields:
                if field in data and data[field] is not None:
                    if isinstance(data[field], str):
                        data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            
            return cls(**data)
            
        except (ValueError, TypeError, KeyError) as e:
            raise PortfolioValidationError(f"Failed to create Portfolio from dict: {str(e)}")
    
    def __str__(self) -> str:
        """String representation of portfolio."""
        return f"Portfolio({self.name}): ${self.total_value:,.2f} ({len(self.get_active_positions())} positions)"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Portfolio(portfolio_id='{self.portfolio_id}', user_id='{self.user_id}', "
                f"name='{self.name}', total_value={self.total_value}, "
                f"positions={len(self.positions)}, status={self.status})")