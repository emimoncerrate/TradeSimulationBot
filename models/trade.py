"""
Trade model with comprehensive validation, serialization, and business logic.

This module provides the Trade data model class with full validation capabilities,
serialization methods, and business logic for trade operations in the Slack Trading Bot.
"""

import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# Configure logging
logger = logging.getLogger(__name__)


class TradeType(Enum):
    """Enumeration for trade types."""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(Enum):
    """Enumeration for trade status."""
    PENDING = "pending"
    EXECUTED = "executed"
    PARTIALLY_FILLED = "partially_filled"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(Enum):
    """Enumeration for risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradeValidationError(Exception):
    """Custom exception for trade validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


@dataclass
class Trade:
    """
    Comprehensive Trade model with validation, serialization, and business logic.
    
    This class represents a trade transaction with full validation capabilities,
    serialization methods for database storage, and business logic methods for
    trade operations and calculations.
    
    Attributes:
        trade_id: Unique identifier for the trade
        user_id: Slack user ID who initiated the trade
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
        quantity: Number of shares to trade (positive integer)
        trade_type: Type of trade (buy/sell)
        price: Price per share in USD
        timestamp: When the trade was created
        status: Current status of the trade
        risk_level: Risk assessment level
        execution_id: ID from the execution system (optional)
        channel_id: Slack channel where trade was initiated
        portfolio_manager_id: ID of assigned portfolio manager (optional)
        market_data: Market data at time of trade (optional)
        risk_analysis: AI risk analysis results (optional)
        execution_timestamp: When trade was executed (optional)
        execution_price: Actual execution price (optional)
        commission: Trading commission charged (optional)
        notes: Additional notes or comments (optional)
    """
    
    # Required fields
    user_id: str
    symbol: str
    quantity: int
    trade_type: TradeType
    price: Decimal
    
    # Auto-generated fields
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: TradeStatus = field(default=TradeStatus.PENDING)
    risk_level: RiskLevel = field(default=RiskLevel.LOW)
    
    # Optional fields
    execution_id: Optional[str] = None
    channel_id: Optional[str] = None
    portfolio_manager_id: Optional[str] = None
    market_data: Optional[Dict[str, Any]] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    execution_timestamp: Optional[datetime] = None
    execution_price: Optional[Decimal] = None
    commission: Optional[Decimal] = field(default_factory=lambda: Decimal('0.00'))
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        try:
            self.validate()
            logger.info(f"Trade {self.trade_id} created successfully for user {self.user_id}")
        except TradeValidationError as e:
            logger.error(f"Trade validation failed: {e.message}")
            raise
    
    def validate(self) -> None:
        """
        Comprehensive validation of trade data.
        
        Raises:
            TradeValidationError: If any validation fails
        """
        # Validate user_id
        if not self.user_id or not isinstance(self.user_id, str):
            raise TradeValidationError("User ID must be a non-empty string", "user_id")
        
        if len(self.user_id.strip()) == 0:
            raise TradeValidationError("User ID cannot be empty or whitespace", "user_id")
        
        # Validate symbol
        if not self.symbol or not isinstance(self.symbol, str):
            raise TradeValidationError("Symbol must be a non-empty string", "symbol")
        
        symbol_clean = self.symbol.strip().upper()
        if len(symbol_clean) == 0:
            raise TradeValidationError("Symbol cannot be empty or whitespace", "symbol")
        
        if len(symbol_clean) > 10:
            raise TradeValidationError("Symbol cannot exceed 10 characters", "symbol")
        
        # Update symbol to cleaned version
        self.symbol = symbol_clean
        
        # Validate quantity
        if not isinstance(self.quantity, int):
            raise TradeValidationError("Quantity must be an integer", "quantity")
        
        if self.quantity <= 0:
            raise TradeValidationError("Quantity must be positive", "quantity")
        
        if self.quantity > 1000000:
            raise TradeValidationError("Quantity cannot exceed 1,000,000 shares", "quantity")
        
        # Validate trade_type
        if not isinstance(self.trade_type, TradeType):
            if isinstance(self.trade_type, str):
                try:
                    self.trade_type = TradeType(self.trade_type.lower())
                except ValueError:
                    raise TradeValidationError(f"Invalid trade type: {self.trade_type}", "trade_type")
            else:
                raise TradeValidationError("Trade type must be TradeType enum or valid string", "trade_type")
        
        # Validate price
        if not isinstance(self.price, Decimal):
            try:
                self.price = Decimal(str(self.price))
            except (InvalidOperation, TypeError):
                raise TradeValidationError("Price must be a valid decimal number", "price")
        
        if self.price <= 0:
            raise TradeValidationError("Price must be positive", "price")
        
        if self.price > Decimal('100000'):
            raise TradeValidationError("Price cannot exceed $100,000 per share", "price")
        
        # Validate optional fields
        if self.execution_price is not None:
            if not isinstance(self.execution_price, Decimal):
                try:
                    self.execution_price = Decimal(str(self.execution_price))
                except (InvalidOperation, TypeError):
                    raise TradeValidationError("Execution price must be a valid decimal", "execution_price")
            
            if self.execution_price <= 0:
                raise TradeValidationError("Execution price must be positive", "execution_price")
        
        if self.commission is not None:
            if not isinstance(self.commission, Decimal):
                try:
                    self.commission = Decimal(str(self.commission))
                except (InvalidOperation, TypeError):
                    raise TradeValidationError("Commission must be a valid decimal", "commission")
            
            if self.commission < 0:
                raise TradeValidationError("Commission cannot be negative", "commission")
        
        # Validate status consistency
        if self.status == TradeStatus.EXECUTED:
            if self.execution_id is None:
                logger.warning(f"Trade {self.trade_id} marked as executed but missing execution_id")
            if self.execution_timestamp is None:
                logger.warning(f"Trade {self.trade_id} marked as executed but missing execution_timestamp")
    
    def calculate_total_value(self) -> Decimal:
        """
        Calculate the total value of the trade.
        
        Returns:
            Total value including commission
        """
        base_value = self.price * Decimal(str(self.quantity))
        total_commission = self.commission or Decimal('0.00')
        return base_value + total_commission
    
    def calculate_execution_value(self) -> Optional[Decimal]:
        """
        Calculate the total execution value if trade is executed.
        
        Returns:
            Total execution value or None if not executed
        """
        if self.execution_price is None:
            return None
        
        base_value = self.execution_price * Decimal(str(self.quantity))
        total_commission = self.commission or Decimal('0.00')
        return base_value + total_commission
    
    def calculate_slippage(self) -> Optional[Decimal]:
        """
        Calculate slippage between expected and execution price.
        
        Returns:
            Slippage amount or None if not executed
        """
        if self.execution_price is None:
            return None
        
        return (self.execution_price - self.price) * Decimal(str(self.quantity))
    
    def is_high_value_trade(self, threshold: Decimal = Decimal('100000')) -> bool:
        """
        Check if this is a high-value trade.
        
        Args:
            threshold: Value threshold for high-value classification
            
        Returns:
            True if trade value exceeds threshold
        """
        return self.calculate_total_value() > threshold
    
    def is_large_quantity_trade(self, threshold: int = 10000) -> bool:
        """
        Check if this is a large quantity trade.
        
        Args:
            threshold: Quantity threshold for large trade classification
            
        Returns:
            True if quantity exceeds threshold
        """
        return self.quantity > threshold
    
    def requires_manager_approval(self) -> bool:
        """
        Determine if trade requires portfolio manager approval.
        
        Returns:
            True if approval is required
        """
        return (
            self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            self.is_high_value_trade() or
            self.is_large_quantity_trade()
        )
    
    def mark_executed(self, execution_id: str, execution_price: Optional[Decimal] = None, 
                     execution_timestamp: Optional[datetime] = None) -> None:
        """
        Mark trade as executed with execution details.
        
        Args:
            execution_id: ID from execution system
            execution_price: Actual execution price
            execution_timestamp: When trade was executed
        """
        self.status = TradeStatus.EXECUTED
        self.execution_id = execution_id
        
        if execution_price is not None:
            self.execution_price = execution_price
        else:
            self.execution_price = self.price
        
        if execution_timestamp is not None:
            self.execution_timestamp = execution_timestamp
        else:
            self.execution_timestamp = datetime.now(timezone.utc)
        
        logger.info(f"Trade {self.trade_id} marked as executed with ID {execution_id}")
    
    def mark_failed(self, reason: Optional[str] = None) -> None:
        """
        Mark trade as failed.
        
        Args:
            reason: Failure reason to add to notes
        """
        self.status = TradeStatus.FAILED
        
        if reason:
            if self.notes:
                self.notes += f" | Failed: {reason}"
            else:
                self.notes = f"Failed: {reason}"
        
        logger.warning(f"Trade {self.trade_id} marked as failed: {reason}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trade to dictionary for serialization.
        
        Returns:
            Dictionary representation of trade
        """
        data = asdict(self)
        
        # Convert enums to string values
        data['trade_type'] = self.trade_type.value
        data['status'] = self.status.value
        data['risk_level'] = self.risk_level.value
        
        # Convert Decimal to string for JSON serialization
        if self.price is not None:
            data['price'] = str(self.price)
        if self.execution_price is not None:
            data['execution_price'] = str(self.execution_price)
        if self.commission is not None:
            data['commission'] = str(self.commission)
        
        # Convert datetime to ISO string
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        if self.execution_timestamp:
            data['execution_timestamp'] = self.execution_timestamp.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """
        Create Trade instance from dictionary.
        
        Args:
            data: Dictionary containing trade data
            
        Returns:
            Trade instance
            
        Raises:
            TradeValidationError: If data is invalid
        """
        try:
            # Convert string values back to appropriate types
            if 'trade_type' in data and isinstance(data['trade_type'], str):
                data['trade_type'] = TradeType(data['trade_type'])
            
            if 'status' in data and isinstance(data['status'], str):
                data['status'] = TradeStatus(data['status'])
            
            if 'risk_level' in data and isinstance(data['risk_level'], str):
                data['risk_level'] = RiskLevel(data['risk_level'])
            
            # Convert string decimals back to Decimal
            for field in ['price', 'execution_price', 'commission']:
                if field in data and data[field] is not None:
                    data[field] = Decimal(str(data[field]))
            
            # Convert ISO strings back to datetime
            for field in ['timestamp', 'execution_timestamp']:
                if field in data and data[field] is not None:
                    if isinstance(data[field], str):
                        data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            
            return cls(**data)
            
        except (ValueError, TypeError, KeyError) as e:
            raise TradeValidationError(f"Failed to create Trade from dict: {str(e)}")
    
    def to_json(self) -> str:
        """
        Convert trade to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Trade':
        """
        Create Trade instance from JSON string.
        
        Args:
            json_str: JSON string containing trade data
            
        Returns:
            Trade instance
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise TradeValidationError(f"Invalid JSON: {str(e)}")
    
    def get_display_summary(self) -> str:
        """
        Get a human-readable summary of the trade.
        
        Returns:
            Formatted trade summary string
        """
        action = "Buy" if self.trade_type == TradeType.BUY else "Sell"
        status_display = self.status.value.title()
        
        summary = f"{action} {self.quantity:,} shares of {self.symbol} at ${self.price:.2f}"
        
        if self.status == TradeStatus.EXECUTED and self.execution_price:
            summary += f" (executed at ${self.execution_price:.2f})"
        
        summary += f" - Status: {status_display}"
        
        if self.risk_level != RiskLevel.LOW:
            summary += f" - Risk: {self.risk_level.value.title()}"
        
        return summary
    
    def __str__(self) -> str:
        """String representation of trade."""
        return f"Trade({self.trade_id[:8]}...): {self.get_display_summary()}"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Trade(trade_id='{self.trade_id}', user_id='{self.user_id}', "
                f"symbol='{self.symbol}', quantity={self.quantity}, "
                f"trade_type={self.trade_type}, price={self.price}, "
                f"status={self.status}, risk_level={self.risk_level})")