"""
Data models package for the Slack Trading Bot.

This package contains comprehensive data models for trades, users, portfolios,
and positions with full validation, serialization, and business logic.
"""

from .trade import (
    Trade,
    TradeType,
    TradeStatus,
    RiskLevel,
    TradeValidationError
)

from .user import (
    User,
    UserProfile,
    UserRole,
    Permission,
    UserStatus,
    UserValidationError
)

from .portfolio import (
    Portfolio,
    Position,
    PositionType,
    PortfolioStatus,
    RiskMetricType,
    PortfolioValidationError
)

__all__ = [
    # Trade models
    'Trade',
    'TradeType',
    'TradeStatus',
    'RiskLevel',
    'TradeValidationError',
    
    # User models
    'User',
    'UserProfile',
    'UserRole',
    'Permission',
    'UserStatus',
    'UserValidationError',
    
    # Portfolio models
    'Portfolio',
    'Position',
    'PositionType',
    'PortfolioStatus',
    'RiskMetricType',
    'PortfolioValidationError'
]