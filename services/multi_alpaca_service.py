"""
Multi-Alpaca Service for Managing Multiple Alpaca Accounts

This service manages multiple Alpaca trading accounts, allowing for
user isolation, load balancing, and account-specific operations.
"""

import logging
import os
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError

logger = logging.getLogger(__name__)


@dataclass
class AlpacaAccountConfig:
    """Configuration for a single Alpaca account."""
    account_id: str
    account_name: str
    api_key: str
    secret_key: str
    base_url: str
    is_paper: bool = True
    is_active: bool = True
    max_users: int = 50


class MultiAlpacaService:
    """
    Service for managing multiple Alpaca trading accounts.
    
    Features:
    - Multiple account management
    - User-to-account assignment
    - Load balancing across accounts
    - Account health monitoring
    - Isolated trading operations
    """
    
    def __init__(self):
        self.accounts: Dict[str, AlpacaAccountConfig] = {}
        self.api_clients: Dict[str, tradeapi.REST] = {}
        self.account_status: Dict[str, Dict[str, Any]] = {}
        
        self._load_account_configurations()
        self._initialize_api_clients()
        
        logger.info(f"MultiAlpacaService initialized with {len(self.accounts)} accounts")
    
    def _load_account_configurations(self) -> None:
        """Load Alpaca account configurations from environment variables."""
        try:
            # Primary account (existing configuration)
            primary_config = self._load_account_config("primary", "")
            if primary_config:
                self.accounts["primary"] = primary_config
            
            # Additional accounts (numbered 1, 2, 3, etc.)
            account_number = 1
            while True:
                suffix = f"_{account_number}"
                account_config = self._load_account_config(f"account_{account_number}", suffix)
                
                if not account_config:
                    break
                
                self.accounts[f"account_{account_number}"] = account_config
                account_number += 1
            
            logger.info(f"Loaded {len(self.accounts)} Alpaca account configurations")
            
        except Exception as e:
            logger.error(f"Error loading account configurations: {e}")
    
    def _load_account_config(self, account_id: str, suffix: str) -> Optional[AlpacaAccountConfig]:
        """
        Load configuration for a single account.
        
        Args:
            account_id: Account identifier
            suffix: Environment variable suffix (e.g., "_1", "_2")
            
        Returns:
            Optional[AlpacaAccountConfig]: Account configuration if valid
        """
        try:
            api_key = os.getenv(f"ALPACA_PAPER_API_KEY{suffix}")
            secret_key = os.getenv(f"ALPACA_PAPER_SECRET_KEY{suffix}")
            base_url = os.getenv(f"ALPACA_PAPER_BASE_URL{suffix}", "https://paper-api.alpaca.markets")
            
            if not api_key or not secret_key:
                if suffix == "":  # Primary account
                    logger.warning("Primary Alpaca account credentials not found")
                return None
            
            # Validate that these are paper trading keys
            if not api_key.startswith('PK'):
                logger.warning(f"Account {account_id}: API key doesn't appear to be a paper trading key")
                return None
            
            return AlpacaAccountConfig(
                account_id=account_id,
                account_name=f"Alpaca Account {account_id.replace('_', ' ').title()}",
                api_key=api_key,
                secret_key=secret_key,
                base_url=base_url,
                is_paper=True,
                is_active=True
            )
            
        except Exception as e:
            logger.error(f"Error loading config for account {account_id}: {e}")
            return None
    
    def _initialize_api_clients(self) -> None:
        """Initialize API clients for all configured accounts."""
        for account_id, config in self.accounts.items():
            try:
                if config.is_active:
                    api_client = tradeapi.REST(
                        key_id=config.api_key,
                        secret_key=config.secret_key,
                        base_url=config.base_url,
                        api_version='v2'
                    )
                    
                    # Test the connection
                    account_info = api_client.get_account()
                    
                    self.api_clients[account_id] = api_client
                    self.account_status[account_id] = {
                        'is_active': True,
                        'account_name': config.account_name,
                        'account_number': account_info.account_number,
                        'status': account_info.status,
                        'cash': float(account_info.cash),
                        'portfolio_value': float(account_info.portfolio_value),
                        'buying_power': float(account_info.buying_power),
                        'day_trading_buying_power': float(getattr(account_info, 'day_trading_buying_power', account_info.buying_power)),
                        'assigned_users': 0,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }
                    
                    logger.info(f"✅ Account {account_id} initialized successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize account {account_id}: {e}")
                self.account_status[account_id] = {
                    'is_active': False,
                    'account_name': config.account_name,
                    'error': str(e),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
    
    def is_available(self) -> bool:
        """Check if the multi-Alpaca service is available."""
        return len(self.api_clients) > 0
    
    def get_available_accounts(self) -> Dict[str, AlpacaAccountConfig]:
        """Get all available and active accounts."""
        return {
            account_id: config
            for account_id, config in self.accounts.items()
            if config.is_active and account_id in self.api_clients
        }
    
    def get_account_client(self, account_id: str) -> Optional[tradeapi.REST]:
        """
        Get API client for a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Optional[tradeapi.REST]: API client if available
        """
        return self.api_clients.get(account_id)
    
    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get account information for a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Optional[Dict[str, Any]]: Account information if available
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                return None
            
            account_info = client.get_account()
            
            return {
                'account_name': self.accounts[account_id].account_name,
                'account_number': account_info.account_number,
                'status': account_info.status,
                'cash': float(account_info.cash),
                'portfolio_value': float(account_info.portfolio_value),
                'buying_power': float(account_info.buying_power),
                'day_trading_buying_power': float(getattr(account_info, 'day_trading_buying_power', account_info.buying_power)),
                'equity': float(account_info.equity),
                'last_equity': float(account_info.last_equity),
                'multiplier': int(account_info.multiplier),
                'currency': account_info.currency,
                'pattern_day_trader': getattr(account_info, 'pattern_day_trader', False),
                'trading_blocked': getattr(account_info, 'trading_blocked', False),
                'transfers_blocked': getattr(account_info, 'transfers_blocked', False),
                'account_blocked': getattr(account_info, 'account_blocked', False),
                'created_at': getattr(account_info, 'created_at', None),
                'trade_suspended_by_user': getattr(account_info, 'trade_suspended_by_user', False),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account info for {account_id}: {e}")
            return None
    
    def get_all_accounts_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured accounts.
        
        Returns:
            Dict[str, Dict[str, Any]]: Status information for all accounts
        """
        # Update account status
        for account_id in self.accounts.keys():
            if account_id in self.api_clients:
                account_info = self.get_account_info(account_id)
                if account_info:
                    self.account_status[account_id].update(account_info)
        
        return self.account_status.copy()
    
    async def execute_trade(self, account_id: str, symbol: str, qty: int, 
                          side: str, order_type: str = 'market', 
                          time_in_force: str = 'day', **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute a trade on a specific account.
        
        Args:
            account_id: Account to execute trade on
            symbol: Stock symbol
            qty: Quantity to trade
            side: 'buy' or 'sell'
            order_type: Order type ('market', 'limit', etc.)
            time_in_force: Time in force ('day', 'gtc', etc.)
            **kwargs: Additional order parameters
            
        Returns:
            Optional[Dict[str, Any]]: Order information if successful
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                logger.error(f"No API client available for account {account_id}")
                return None
            
            # Submit order
            order = client.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                **kwargs
            )
            
            logger.info(f"✅ Trade executed on {account_id}: {side} {qty} {symbol}")
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': int(order.qty),
                'side': order.side,
                'order_type': order.order_type,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'account_id': account_id
            }
            
        except APIError as e:
            logger.error(f"Alpaca API error executing trade on {account_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error executing trade on {account_id}: {e}")
            return None
    
    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get positions for a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            List[Dict[str, Any]]: List of positions
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                return []
            
            positions = client.list_positions()
            
            return [
                {
                    'symbol': pos.symbol,
                    'qty': int(pos.qty),
                    'side': pos.side,
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price) if pos.current_price else None,
                    'lastday_price': float(pos.lastday_price) if pos.lastday_price else None,
                    'change_today': float(pos.change_today) if pos.change_today else None,
                    'account_id': account_id
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"Error getting positions for {account_id}: {e}")
            return []
    
    def get_orders(self, account_id: str, status: str = 'all', 
                  limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get orders for a specific account.
        
        Args:
            account_id: Account identifier
            status: Order status filter
            limit: Maximum number of orders to return
            
        Returns:
            List[Dict[str, Any]]: List of orders
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                return []
            
            orders = client.list_orders(status=status, limit=limit)
            
            return [
                {
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'qty': int(order.qty),
                    'side': order.side,
                    'order_type': order.order_type,
                    'status': order.status,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'time_in_force': order.time_in_force,
                    'account_id': account_id
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Error getting orders for {account_id}: {e}")
            return []
    
    def get_portfolio_history(self, account_id: str, period: str = '1D', 
                            timeframe: str = '1Min') -> Optional[Dict[str, Any]]:
        """
        Get portfolio history for a specific account.
        
        Args:
            account_id: Account identifier
            period: Time period ('1D', '1W', '1M', etc.)
            timeframe: Data timeframe ('1Min', '5Min', '15Min', etc.)
            
        Returns:
            Optional[Dict[str, Any]]: Portfolio history data
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                return None
            
            portfolio_history = client.get_portfolio_history(
                period=period,
                timeframe=timeframe
            )
            
            return {
                'timestamp': portfolio_history.timestamp,
                'equity': portfolio_history.equity,
                'profit_loss': portfolio_history.profit_loss,
                'profit_loss_pct': portfolio_history.profit_loss_pct,
                'base_value': portfolio_history.base_value,
                'timeframe': timeframe,
                'account_id': account_id
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio history for {account_id}: {e}")
            return None
    
    def cancel_order(self, account_id: str, order_id: str) -> bool:
        """
        Cancel an order on a specific account.
        
        Args:
            account_id: Account identifier
            order_id: Order ID to cancel
            
        Returns:
            bool: True if cancellation successful
        """
        try:
            client = self.get_account_client(account_id)
            if not client:
                return False
            
            client.cancel_order(order_id)
            logger.info(f"✅ Order {order_id} cancelled on account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} on {account_id}: {e}")
            return False
    
    def get_account_summary(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a comprehensive summary of an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Optional[Dict[str, Any]]: Account summary
        """
        try:
            account_info = self.get_account_info(account_id)
            if not account_info:
                return None
            
            positions = self.get_positions(account_id)
            recent_orders = self.get_orders(account_id, status='all', limit=10)
            
            return {
                'account_info': account_info,
                'positions': positions,
                'recent_orders': recent_orders,
                'position_count': len(positions),
                'total_position_value': sum(pos['market_value'] for pos in positions),
                'total_unrealized_pl': sum(pos['unrealized_pl'] for pos in positions),
                'account_id': account_id,
                'summary_generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating account summary for {account_id}: {e}")
            return None