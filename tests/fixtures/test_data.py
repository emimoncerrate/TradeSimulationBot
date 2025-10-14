"""
Test Data Fixtures for Integration Testing

This module provides factory functions for creating test data objects including
users, trades, positions, market quotes, and risk analyses with realistic
data for comprehensive testing scenarios.
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from models.user import User, UserRole, UserStatus, Permission, UserProfile
from models.trade import Trade, TradeType, TradeStatus, RiskLevel
from models.portfolio import Position, Portfolio, PortfolioStatus, PositionType
from services.market_data import MarketQuote
from services.risk_analysis import RiskAnalysis


def create_test_user(
    user_id: Optional[str] = None,
    slack_user_id: Optional[str] = None,
    role: UserRole = UserRole.EXECUTION_TRADER,
    status: UserStatus = UserStatus.ACTIVE,
    permissions: Optional[List[Permission]] = None,
    display_name: str = "Test User",
    email: str = "test.user@jainglobal.com"
) -> User:
    """
    Create a test user with specified parameters.
    
    Args:
        user_id: Unique user ID
        slack_user_id: Slack user ID
        role: User role
        status: User status
        permissions: List of permissions
        display_name: Display name
        email: Email address
        
    Returns:
        User object for testing
    """
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    if slack_user_id is None:
        slack_user_id = f"U{uuid.uuid4().hex[:8].upper()}"
    
    if permissions is None:
        # Default permissions based on role
        if role == UserRole.RESEARCH_ANALYST:
            permissions = [
                Permission.EXECUTE_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.VIEW_PORTFOLIO
            ]
        elif role == UserRole.EXECUTION_TRADER:
            permissions = [
                Permission.EXECUTE_TRADES,
                Permission.VIEW_TRADES,
                Permission.VIEW_PORTFOLIO
            ]
        elif role == UserRole.PORTFOLIO_MANAGER:
            permissions = [
                Permission.EXECUTE_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.VIEW_PORTFOLIO,
                Permission.MANAGE_USERS,
                Permission.VIEW_ALL_TRADES
            ]
        else:
            permissions = [Permission.VIEW_PORTFOLIO]
    
    profile = UserProfile(
        display_name=display_name,
        email=email,
        phone="+1-555-0123",
        department="Trading",
        title=role.value.replace('_', ' ').title(),
        manager_id=None,
        hire_date=datetime.now(timezone.utc) - timedelta(days=365),
        preferences={
            'notifications': True,
            'theme': 'light',
            'timezone': 'America/New_York'
        }
    )
    
    return User(
        user_id=user_id,
        slack_user_id=slack_user_id,
        role=role,
        status=status,
        permissions=permissions,
        profile=profile,
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
        last_login=datetime.now(timezone.utc) - timedelta(hours=1),
        session_data={}
    )


def create_test_trade(
    symbol: str = "AAPL",
    quantity: int = 100,
    trade_type: TradeType = TradeType.BUY,
    price: Decimal = Decimal("150.00"),
    status: TradeStatus = TradeStatus.PENDING,
    user_id: Optional[str] = None,
    trade_id: Optional[str] = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    execution_id: Optional[str] = None
) -> Trade:
    """
    Create a test trade with specified parameters.
    
    Args:
        symbol: Stock symbol
        quantity: Number of shares
        trade_type: Buy or sell
        price: Trade price
        status: Trade status
        user_id: User ID who placed the trade
        trade_id: Unique trade ID
        risk_level: Risk level assessment
        execution_id: Execution ID if executed
        
    Returns:
        Trade object for testing
    """
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    if trade_id is None:
        trade_id = f"trade_{uuid.uuid4().hex[:8]}"
    
    return Trade(
        trade_id=trade_id,
        user_id=user_id,
        symbol=symbol.upper(),
        quantity=quantity,
        trade_type=trade_type,
        price=price,
        timestamp=datetime.now(timezone.utc),
        status=status,
        risk_level=risk_level,
        execution_id=execution_id,
        metadata={
            'source': 'slack_bot',
            'channel_id': 'C1234567890',
            'risk_analysis_id': f"risk_{uuid.uuid4().hex[:8]}" if risk_level != RiskLevel.LOW else None
        }
    )


def create_test_position(
    symbol: str = "AAPL",
    quantity: int = 100,
    average_cost: Decimal = Decimal("150.00"),
    current_price: Optional[Decimal] = None,
    user_id: Optional[str] = None,
    position_type: PositionType = PositionType.LONG
) -> Position:
    """
    Create a test position with specified parameters.
    
    Args:
        symbol: Stock symbol
        quantity: Number of shares
        average_cost: Average cost per share
        current_price: Current market price
        user_id: User ID who owns the position
        position_type: Long or short position
        
    Returns:
        Position object for testing
    """
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    if current_price is None:
        # Simulate some price movement
        current_price = average_cost * Decimal("1.05")  # 5% gain
    
    current_value = current_price * quantity
    cost_basis = average_cost * quantity
    unrealized_pnl = current_value - cost_basis
    
    return Position(
        user_id=user_id,
        symbol=symbol.upper(),
        quantity=quantity,
        position_type=position_type,
        average_cost=average_cost,
        current_price=current_price,
        current_value=current_value,
        cost_basis=cost_basis,
        unrealized_pnl=unrealized_pnl,
        realized_pnl=Decimal("0.00"),
        last_updated=datetime.now(timezone.utc),
        metadata={
            'acquisition_date': datetime.now(timezone.utc) - timedelta(days=30),
            'last_trade_id': f"trade_{uuid.uuid4().hex[:8]}"
        }
    )


def create_test_portfolio(
    user_id: Optional[str] = None,
    positions: Optional[List[Position]] = None,
    cash_balance: Decimal = Decimal("10000.00"),
    status: PortfolioStatus = PortfolioStatus.ACTIVE
) -> Portfolio:
    """
    Create a test portfolio with specified parameters.
    
    Args:
        user_id: User ID who owns the portfolio
        positions: List of positions in the portfolio
        cash_balance: Available cash balance
        status: Portfolio status
        
    Returns:
        Portfolio object for testing
    """
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    if positions is None:
        positions = [
            create_test_position("AAPL", 100, Decimal("150.00"), user_id=user_id),
            create_test_position("GOOGL", 50, Decimal("2500.00"), user_id=user_id),
            create_test_position("MSFT", 75, Decimal("300.00"), user_id=user_id)
        ]
    
    # Calculate portfolio metrics
    total_value = cash_balance
    total_cost = Decimal("0.00")
    total_unrealized_pnl = Decimal("0.00")
    
    for position in positions:
        total_value += position.current_value
        total_cost += position.cost_basis
        total_unrealized_pnl += position.unrealized_pnl
    
    return Portfolio(
        user_id=user_id,
        positions=positions,
        cash_balance=cash_balance,
        total_value=total_value,
        total_cost=total_cost,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=Decimal("500.00"),  # Some historical gains
        status=status,
        last_updated=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc) - timedelta(days=90),
        metadata={
            'risk_tolerance': 'moderate',
            'investment_objective': 'growth',
            'benchmark': 'SPY'
        }
    )


def create_test_market_quote(
    symbol: str = "AAPL",
    current_price: Decimal = Decimal("150.00"),
    change: Optional[Decimal] = None,
    change_percent: Optional[Decimal] = None,
    volume: int = 1000000,
    high: Optional[Decimal] = None,
    low: Optional[Decimal] = None,
    open_price: Optional[Decimal] = None
) -> MarketQuote:
    """
    Create a test market quote with specified parameters.
    
    Args:
        symbol: Stock symbol
        current_price: Current market price
        change: Price change from previous close
        change_percent: Percentage change
        volume: Trading volume
        high: Day's high price
        low: Day's low price
        open_price: Opening price
        
    Returns:
        MarketQuote object for testing
    """
    if change is None:
        change = Decimal("2.50")  # Default to $2.50 gain
    
    if change_percent is None:
        previous_close = current_price - change
        change_percent = (change / previous_close) * 100 if previous_close > 0 else Decimal("0.00")
    
    if high is None:
        high = current_price * Decimal("1.02")  # 2% above current
    
    if low is None:
        low = current_price * Decimal("0.98")  # 2% below current
    
    if open_price is None:
        open_price = current_price - (change * Decimal("0.5"))  # Halfway to previous close
    
    return MarketQuote(
        symbol=symbol.upper(),
        current_price=current_price,
        change=change,
        change_percent=change_percent,
        volume=volume,
        high=high,
        low=low,
        open=open_price,
        previous_close=current_price - change,
        market_cap=None,  # Not always available
        pe_ratio=None,    # Not always available
        timestamp=datetime.now(timezone.utc),
        source="test_provider",
        metadata={
            'currency': 'USD',
            'exchange': 'NASDAQ',
            'market_status': 'open'
        }
    )


def create_test_risk_analysis(
    risk_level: RiskLevel = RiskLevel.LOW,
    risk_score: float = 0.3,
    is_high_risk: bool = False,
    recommendations: Optional[List[str]] = None,
    analysis_id: Optional[str] = None
) -> RiskAnalysis:
    """
    Create a test risk analysis with specified parameters.
    
    Args:
        risk_level: Overall risk level
        risk_score: Numerical risk score (0.0 to 1.0)
        is_high_risk: Whether this is flagged as high risk
        recommendations: List of risk recommendations
        analysis_id: Unique analysis ID
        
    Returns:
        RiskAnalysis object for testing
    """
    if analysis_id is None:
        analysis_id = f"risk_{uuid.uuid4().hex[:8]}"
    
    if recommendations is None:
        if risk_level == RiskLevel.LOW:
            recommendations = [
                "Trade appears to be within normal risk parameters",
                "Consider monitoring position size relative to portfolio"
            ]
        elif risk_level == RiskLevel.MEDIUM:
            recommendations = [
                "Monitor market conditions closely",
                "Consider reducing position size if volatility increases",
                "Review correlation with existing positions"
            ]
        else:  # HIGH risk
            recommendations = [
                "Consider reducing position size significantly",
                "Review portfolio impact and concentration risk",
                "Monitor market conditions and news closely",
                "Consider setting stop-loss orders"
            ]
    
    # Generate realistic risk factors based on risk level
    risk_factors = {}
    if risk_level == RiskLevel.LOW:
        risk_factors = {
            'volatility_risk': 0.2,
            'concentration_risk': 0.1,
            'market_risk': 0.3,
            'liquidity_risk': 0.1,
            'correlation_risk': 0.2
        }
    elif risk_level == RiskLevel.MEDIUM:
        risk_factors = {
            'volatility_risk': 0.5,
            'concentration_risk': 0.4,
            'market_risk': 0.6,
            'liquidity_risk': 0.3,
            'correlation_risk': 0.5
        }
    else:  # HIGH risk
        risk_factors = {
            'volatility_risk': 0.8,
            'concentration_risk': 0.9,
            'market_risk': 0.7,
            'liquidity_risk': 0.6,
            'correlation_risk': 0.8
        }
    
    return RiskAnalysis(
        analysis_id=analysis_id,
        overall_risk_level=risk_level,
        overall_risk_score=risk_score,
        is_high_risk=is_high_risk,
        risk_factors=risk_factors,
        portfolio_impact_score=risk_score * 0.8,  # Slightly lower than overall
        market_conditions_score=0.4,  # Neutral market conditions
        recommendations=recommendations,
        analysis_summary=f"Risk analysis indicates {risk_level.value.lower()} risk level with score of {risk_score:.2f}",
        confidence_score=0.85,  # High confidence in analysis
        generated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        metadata={
            'model_version': 'claude-3-sonnet-20240229',
            'analysis_duration_ms': 1500,
            'data_sources': ['market_data', 'portfolio_data', 'risk_models']
        }
    )


def create_test_trade_execution_result(
    success: bool = True,
    execution_id: Optional[str] = None,
    execution_price: Optional[Decimal] = None,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a test trade execution result.
    
    Args:
        success: Whether execution was successful
        execution_id: Execution ID if successful
        execution_price: Actual execution price
        error_message: Error message if failed
        
    Returns:
        Trade execution result dictionary
    """
    if success:
        if execution_id is None:
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        if execution_price is None:
            execution_price = Decimal("150.00")
        
        return {
            'success': True,
            'execution_id': execution_id,
            'execution_price': execution_price,
            'execution_timestamp': datetime.now(timezone.utc),
            'error_message': None,
            'metadata': {
                'execution_venue': 'NASDAQ',
                'execution_type': 'market',
                'commission': Decimal("1.00")
            }
        }
    else:
        if error_message is None:
            error_message = "Trading system temporarily unavailable"
        
        return {
            'success': False,
            'execution_id': None,
            'execution_price': None,
            'execution_timestamp': None,
            'error_message': error_message,
            'metadata': {
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 30
            }
        }


def create_bulk_test_data(
    num_users: int = 3,
    num_trades_per_user: int = 5,
    num_positions_per_user: int = 3
) -> Dict[str, Any]:
    """
    Create bulk test data for performance and load testing.
    
    Args:
        num_users: Number of test users to create
        num_trades_per_user: Number of trades per user
        num_positions_per_user: Number of positions per user
        
    Returns:
        Dictionary containing all test data
    """
    users = []
    trades = []
    positions = []
    portfolios = []
    
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
    roles = [UserRole.RESEARCH_ANALYST, UserRole.EXECUTION_TRADER, UserRole.PORTFOLIO_MANAGER]
    
    for i in range(num_users):
        # Create user
        user = create_test_user(
            user_id=f"bulk_user_{i:03d}",
            role=roles[i % len(roles)],
            display_name=f"Test User {i+1}",
            email=f"test.user.{i+1}@jainglobal.com"
        )
        users.append(user)
        
        # Create trades for user
        user_trades = []
        for j in range(num_trades_per_user):
            trade = create_test_trade(
                symbol=symbols[j % len(symbols)],
                quantity=(j + 1) * 50,  # Varying quantities
                trade_type=TradeType.BUY if j % 2 == 0 else TradeType.SELL,
                price=Decimal(str(100 + (j * 25))),  # Varying prices
                user_id=user.user_id,
                status=TradeStatus.EXECUTED if j < num_trades_per_user - 1 else TradeStatus.PENDING
            )
            user_trades.append(trade)
            trades.append(trade)
        
        # Create positions for user
        user_positions = []
        for k in range(num_positions_per_user):
            position = create_test_position(
                symbol=symbols[k % len(symbols)],
                quantity=(k + 1) * 100,
                average_cost=Decimal(str(150 + (k * 50))),
                user_id=user.user_id
            )
            user_positions.append(position)
            positions.append(position)
        
        # Create portfolio for user
        portfolio = create_test_portfolio(
            user_id=user.user_id,
            positions=user_positions,
            cash_balance=Decimal(str(10000 + (i * 5000)))
        )
        portfolios.append(portfolio)
    
    return {
        'users': users,
        'trades': trades,
        'positions': positions,
        'portfolios': portfolios,
        'summary': {
            'total_users': len(users),
            'total_trades': len(trades),
            'total_positions': len(positions),
            'total_portfolios': len(portfolios)
        }
    }