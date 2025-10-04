"""
Mock Services for Integration Testing

This module provides mock implementations of all external services used by the
Slack Trading Bot for comprehensive integration testing without external dependencies.
Includes realistic behavior simulation and configurable responses.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock
import uuid

from models.user import User, UserRole, UserStatus
from models.trade import Trade, TradeStatus, TradeType, RiskLevel
from models.portfolio import Position, Portfolio
from services.market_data import MarketQuote, MarketDataError
from services.risk_analysis import RiskAnalysis, RiskAnalysisError
from services.trading_api import TradeExecution, TradingError
from services.database import DatabaseError, NotFoundError
from tests.fixtures.test_data import (
    create_test_market_quote,
    create_test_risk_analysis,
    create_test_trade_execution_result
)


class MockSlackClient:
    """
    Mock Slack WebClient for testing Slack API interactions.
    
    Simulates all Slack API methods used by the bot with realistic
    responses and error conditions for comprehensive testing.
    """
    
    def __init__(self):
        self.reset_mock()
    
    def reset_mock(self):
        """Reset all mock call tracking."""
        self.method_calls = []
        self.views_open = MagicMock()
        self.views_update = MagicMock()
        self.views_publish = MagicMock()
        self.chat_postMessage = MagicMock()
        self.chat_postEphemeral = MagicMock()
        self.users_info = MagicMock()
        self.conversations_info = MagicMock()
        
        # Configure default responses
        self.views_open.return_value = {'ok': True, 'view': {'id': 'V1234567890'}}
        self.views_update.return_value = {'ok': True, 'view': {'id': 'V1234567890'}}
        self.views_publish.return_value = {'ok': True}
        self.chat_postMessage.return_value = {'ok': True, 'ts': '1234567890.123456'}
        self.chat_postEphemeral.return_value = {'ok': True, 'ts': '1234567890.123456'}
        
        self.users_info.return_value = {
            'ok': True,
            'user': {
                'id': 'U1234567890',
                'name': 'test.user',
                'real_name': 'Test User',
                'profile': {
                    'email': 'test.user@jainglobal.com',
                    'display_name': 'Test User'
                }
            }
        }
        
        self.conversations_info.return_value = {
            'ok': True,
            'channel': {
                'id': 'C1234567890',
                'name': 'trading-private',
                'is_private': True
            }
        }
    
    def simulate_api_error(self, method: str, error: str = 'api_error'):
        """Simulate API error for specific method."""
        mock_method = getattr(self, method)
        mock_method.side_effect = Exception(f"Slack API Error: {error}")
    
    def simulate_rate_limit(self, method: str, retry_after: int = 30):
        """Simulate rate limiting for specific method."""
        mock_method = getattr(self, method)
        mock_method.side_effect = Exception(f"Rate limited, retry after {retry_after}s")


class MockDatabaseService:
    """
    Mock database service for testing database operations.
    
    Provides in-memory storage and realistic database behavior
    including error conditions and data persistence simulation.
    """
    
    def __init__(self):
        self.reset_data()
        self.simulate_errors = False
        self.error_probability = 0.0
    
    def reset_data(self):
        """Reset all stored data."""
        self.users = {}
        self.trades = {}
        self.positions = {}
        self.portfolios = {}
        self.channels = {}
        self.audit_logs = []
        self.call_log = []
    
    def enable_error_simulation(self, probability: float = 0.1):
        """Enable random error simulation."""
        self.simulate_errors = True
        self.error_probability = probability
    
    def _maybe_raise_error(self, operation: str):
        """Randomly raise database error based on probability."""
        if self.simulate_errors:
            import random
            if random.random() < self.error_probability:
                raise DatabaseError(f"Simulated database error in {operation}", "SIMULATED_ERROR")
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        self.call_log.append(('get_user', user_id))
        self._maybe_raise_error('get_user')
        return self.users.get(user_id)
    
    async def create_user(self, user: User) -> bool:
        """Create new user."""
        self.call_log.append(('create_user', user.user_id))
        self._maybe_raise_error('create_user')
        self.users[user.user_id] = user
        return True
    
    async def update_user(self, user: User) -> bool:
        """Update existing user."""
        self.call_log.append(('update_user', user.user_id))
        self._maybe_raise_error('update_user')
        if user.user_id not in self.users:
            raise NotFoundError(f"User {user.user_id} not found", "USER_NOT_FOUND")
        self.users[user.user_id] = user
        return True
    
    async def log_trade(self, trade: Trade) -> bool:
        """Log a trade."""
        self.call_log.append(('log_trade', trade.trade_id))
        self._maybe_raise_error('log_trade')
        key = f"{trade.user_id}:{trade.trade_id}"
        self.trades[key] = trade
        return True
    
    async def get_trade(self, user_id: str, trade_id: str) -> Optional[Trade]:
        """Get trade by user and trade ID."""
        self.call_log.append(('get_trade', user_id, trade_id))
        self._maybe_raise_error('get_trade')
        key = f"{user_id}:{trade_id}"
        return self.trades.get(key)
    
    async def get_user_trades(self, user_id: str, limit: int = 50, **kwargs) -> List[Trade]:
        """Get trades for a user."""
        self.call_log.append(('get_user_trades', user_id, limit))
        self._maybe_raise_error('get_user_trades')
        
        user_trades = [
            trade for key, trade in self.trades.items()
            if key.startswith(f"{user_id}:")
        ]
        
        # Sort by timestamp, most recent first
        user_trades.sort(key=lambda t: t.timestamp, reverse=True)
        return user_trades[:limit]
    
    async def update_trade_status(self, user_id: str, trade_id: str, 
                                status: TradeStatus, execution_details: Optional[Dict[str, Any]] = None) -> bool:
        """Update trade status."""
        self.call_log.append(('update_trade_status', user_id, trade_id, status))
        self._maybe_raise_error('update_trade_status')
        
        key = f"{user_id}:{trade_id}"
        if key not in self.trades:
            raise NotFoundError(f"Trade {trade_id} not found", "TRADE_NOT_FOUND")
        
        trade = self.trades[key]
        trade.status = status
        if execution_details:
            trade.execution_id = execution_details.get('execution_id')
            if 'execution_price' in execution_details:
                trade.price = Decimal(str(execution_details['execution_price']))
        
        return True
    
    async def get_user_positions(self, user_id: str, active_only: bool = True) -> List[Position]:
        """Get positions for a user."""
        self.call_log.append(('get_user_positions', user_id, active_only))
        self._maybe_raise_error('get_user_positions')
        
        user_positions = [
            pos for key, pos in self.positions.items()
            if key.startswith(f"{user_id}:")
        ]
        
        if active_only:
            user_positions = [pos for pos in user_positions if pos.quantity != 0]
        
        return user_positions
    
    async def update_position(self, user_id: str, symbol: str, quantity: int, 
                            price: Decimal, trade_id: str, commission: Decimal = Decimal('0.00')) -> bool:
        """Update position."""
        self.call_log.append(('update_position', user_id, symbol, quantity, price, trade_id))
        self._maybe_raise_error('update_position')
        
        key = f"{user_id}:{symbol}"
        
        if key in self.positions:
            # Update existing position
            position = self.positions[key]
            old_quantity = position.quantity
            old_cost_basis = position.cost_basis
            
            new_quantity = old_quantity + quantity
            new_cost_basis = old_cost_basis + (price * quantity)
            
            if new_quantity != 0:
                position.quantity = new_quantity
                position.cost_basis = new_cost_basis
                position.average_cost = new_cost_basis / new_quantity
            else:
                # Position closed
                position.quantity = 0
                position.cost_basis = Decimal('0.00')
                position.average_cost = Decimal('0.00')
        else:
            # Create new position
            from tests.fixtures.test_data import create_test_position
            position = create_test_position(
                symbol=symbol,
                quantity=quantity,
                average_cost=price,
                user_id=user_id
            )
            self.positions[key] = position
        
        position.last_updated = datetime.now(timezone.utc)
        return True
    
    async def is_channel_approved(self, channel_id: str) -> bool:
        """Check if channel is approved."""
        self.call_log.append(('is_channel_approved', channel_id))
        self._maybe_raise_error('is_channel_approved')
        
        # Default approved channels for testing
        approved_channels = ['C1234567890', 'C0987654321', 'CTEST123456']
        return channel_id in approved_channels or channel_id in self.channels
    
    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information."""
        self.call_log.append(('get_channel_info', channel_id))
        self._maybe_raise_error('get_channel_info')
        return self.channels.get(channel_id)


class MockMarketDataService:
    """
    Mock market data service for testing market data operations.
    
    Provides realistic market data with configurable responses
    and error conditions for comprehensive testing.
    """
    
    def __init__(self):
        self.call_log = []
        self.simulate_errors = False
        self.error_probability = 0.0
        self.response_delay = 0.0
        
        # Default market data
        self.market_data = {
            'AAPL': create_test_market_quote('AAPL', Decimal('150.00')),
            'GOOGL': create_test_market_quote('GOOGL', Decimal('2500.00')),
            'MSFT': create_test_market_quote('MSFT', Decimal('300.00')),
            'AMZN': create_test_market_quote('AMZN', Decimal('3200.00')),
            'TSLA': create_test_market_quote('TSLA', Decimal('800.00'))
        }
    
    def enable_error_simulation(self, probability: float = 0.1):
        """Enable random error simulation."""
        self.simulate_errors = True
        self.error_probability = probability
    
    def set_response_delay(self, delay: float):
        """Set artificial delay for responses."""
        self.response_delay = delay
    
    def _maybe_raise_error(self, operation: str):
        """Randomly raise market data error."""
        if self.simulate_errors:
            import random
            if random.random() < self.error_probability:
                raise MarketDataError(f"Simulated market data error in {operation}", "SIMULATED_ERROR")
    
    async def get_quote(self, symbol: str) -> MarketQuote:
        """Get market quote for symbol."""
        self.call_log.append(('get_quote', symbol))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('get_quote')
        
        symbol = symbol.upper()
        if symbol in self.market_data:
            return self.market_data[symbol]
        else:
            # Generate random quote for unknown symbols
            return create_test_market_quote(symbol, Decimal('100.00'))
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, MarketQuote]:
        """Get quotes for multiple symbols."""
        self.call_log.append(('get_multiple_quotes', symbols))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('get_multiple_quotes')
        
        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = await self.get_quote(symbol)
            except MarketDataError:
                continue  # Skip failed quotes
        
        return quotes
    
    def set_quote(self, symbol: str, quote: MarketQuote):
        """Set specific quote for testing."""
        self.market_data[symbol.upper()] = quote


class MockRiskAnalysisService:
    """
    Mock risk analysis service for testing AI-powered risk analysis.
    
    Provides configurable risk analysis responses with realistic
    behavior and error simulation capabilities.
    """
    
    def __init__(self):
        self.call_log = []
        self.simulate_errors = False
        self.error_probability = 0.0
        self.response_delay = 0.0
        self.default_risk_level = RiskLevel.LOW
    
    def enable_error_simulation(self, probability: float = 0.1):
        """Enable random error simulation."""
        self.simulate_errors = True
        self.error_probability = probability
    
    def set_response_delay(self, delay: float):
        """Set artificial delay for responses."""
        self.response_delay = delay
    
    def set_default_risk_level(self, risk_level: RiskLevel):
        """Set default risk level for responses."""
        self.default_risk_level = risk_level
    
    def _maybe_raise_error(self, operation: str):
        """Randomly raise risk analysis error."""
        if self.simulate_errors:
            import random
            if random.random() < self.error_probability:
                raise RiskAnalysisError(f"Simulated risk analysis error in {operation}", "SIMULATED_ERROR")
    
    async def analyze_trade_risk(self, trade: Trade, positions: List[Position]) -> RiskAnalysis:
        """Analyze trade risk."""
        self.call_log.append(('analyze_trade_risk', trade.trade_id, len(positions)))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('analyze_trade_risk')
        
        # Determine risk level based on trade characteristics
        risk_level = self.default_risk_level
        risk_score = 0.3
        is_high_risk = False
        
        # Simple risk logic for testing
        if trade.quantity > 500:  # Large quantity
            risk_level = RiskLevel.MEDIUM
            risk_score = 0.6
        
        if trade.quantity > 1000:  # Very large quantity
            risk_level = RiskLevel.HIGH
            risk_score = 0.8
            is_high_risk = True
        
        # Check for concentration risk
        total_symbol_quantity = sum(
            pos.quantity for pos in positions 
            if pos.symbol == trade.symbol
        )
        
        if total_symbol_quantity + trade.quantity > 1000:
            risk_level = RiskLevel.HIGH
            risk_score = 0.9
            is_high_risk = True
        
        return create_test_risk_analysis(
            risk_level=risk_level,
            risk_score=risk_score,
            is_high_risk=is_high_risk
        )
    
    async def analyze_portfolio_risk(self, portfolio: Portfolio) -> RiskAnalysis:
        """Analyze portfolio risk."""
        self.call_log.append(('analyze_portfolio_risk', portfolio.user_id))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('analyze_portfolio_risk')
        
        # Simple portfolio risk analysis
        total_value = portfolio.total_value
        risk_level = RiskLevel.LOW
        risk_score = 0.3
        
        if total_value > Decimal('100000'):  # Large portfolio
            risk_level = RiskLevel.MEDIUM
            risk_score = 0.5
        
        if total_value > Decimal('500000'):  # Very large portfolio
            risk_level = RiskLevel.HIGH
            risk_score = 0.7
        
        return create_test_risk_analysis(
            risk_level=risk_level,
            risk_score=risk_score,
            is_high_risk=risk_level == RiskLevel.HIGH
        )


class MockTradingAPIService:
    """
    Mock trading API service for testing trade execution.
    
    Provides realistic trade execution simulation with configurable
    success/failure rates and execution details.
    """
    
    def __init__(self):
        self.call_log = []
        self.simulate_errors = False
        self.error_probability = 0.0
        self.response_delay = 0.0
        self.success_rate = 1.0  # 100% success by default
    
    def enable_error_simulation(self, probability: float = 0.1):
        """Enable random error simulation."""
        self.simulate_errors = True
        self.error_probability = probability
    
    def set_response_delay(self, delay: float):
        """Set artificial delay for responses."""
        self.response_delay = delay
    
    def set_success_rate(self, rate: float):
        """Set trade execution success rate (0.0 to 1.0)."""
        self.success_rate = max(0.0, min(1.0, rate))
    
    def _maybe_raise_error(self, operation: str):
        """Randomly raise trading error."""
        if self.simulate_errors:
            import random
            if random.random() < self.error_probability:
                raise TradingError(f"Simulated trading error in {operation}", "SIMULATED_ERROR")
    
    async def execute_trade(self, trade: Trade) -> TradeExecution:
        """Execute a trade."""
        self.call_log.append(('execute_trade', trade.trade_id, trade.symbol, trade.quantity))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('execute_trade')
        
        # Determine if trade should succeed
        import random
        success = random.random() < self.success_rate
        
        if success:
            # Simulate slight price variation
            price_variation = Decimal(str(random.uniform(-0.02, 0.02)))  # ±2%
            execution_price = trade.price * (1 + price_variation)
            
            return TradeExecution(
                success=True,
                execution_id=f"exec_{uuid.uuid4().hex[:8]}",
                execution_price=execution_price,
                execution_timestamp=datetime.now(timezone.utc),
                error_message=None
            )
        else:
            error_messages = [
                "Insufficient liquidity",
                "Market closed",
                "Trading halted for symbol",
                "System temporarily unavailable",
                "Order rejected by exchange"
            ]
            
            return TradeExecution(
                success=False,
                execution_id=None,
                execution_price=None,
                execution_timestamp=None,
                error_message=random.choice(error_messages)
            )
    
    async def cancel_trade(self, execution_id: str) -> bool:
        """Cancel a trade."""
        self.call_log.append(('cancel_trade', execution_id))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('cancel_trade')
        
        # Simulate cancellation success/failure
        import random
        return random.random() < 0.9  # 90% success rate
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status."""
        self.call_log.append(('get_execution_status', execution_id))
        
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        self._maybe_raise_error('get_execution_status')
        
        return {
            'execution_id': execution_id,
            'status': 'executed',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': 'Trade executed successfully'
        }