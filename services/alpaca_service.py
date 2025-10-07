"""
Alpaca Paper Trading Service with Safety Checks
IMPORTANT: This service ONLY works with paper trading - NO REAL MONEY
"""

import os
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError

logger = logging.getLogger(__name__)


class AlpacaSafetyError(Exception):
    """Raised when safety checks fail."""
    pass


class AlpacaService:
    """
    Alpaca Paper Trading Service with comprehensive safety checks.
    
    This service ONLY allows paper trading and includes multiple safety
    mechanisms to prevent accidental live trading.
    """
    
    def __init__(self):
        """Initialize Alpaca Paper Trading service with safety checks."""
        self.alpaca = None
        self.is_initialized = False
        self.account_info = None
        
        logger.info("Initializing AlpacaService...")
        
    async def initialize(self) -> None:
        """Initialize and validate Alpaca connection with safety checks."""
        try:
            # Get configuration from environment
            api_key = os.getenv('ALPACA_PAPER_API_KEY')
            secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')
            base_url = os.getenv('ALPACA_PAPER_BASE_URL', 'https://paper-api.alpaca.markets')
            enabled = os.getenv('ALPACA_PAPER_ENABLED', 'false').lower() == 'true'
            
            # Check if Alpaca is enabled
            if not enabled:
                logger.info("⚠️  Alpaca Paper Trading is DISABLED (set ALPACA_PAPER_ENABLED=true to enable)")
                logger.info("   Bot will use mock trading instead")
                return
            
            # Validate configuration
            if not api_key or api_key == 'YOUR_PAPER_API_KEY_HERE':
                logger.warning("⚠️  Alpaca API key not configured - using mock trading")
                logger.info("   Get keys from: https://alpaca.markets/ (Paper Trading section)")
                return
            
            if not secret_key or secret_key == 'YOUR_PAPER_SECRET_KEY_HERE':
                logger.warning("⚠️  Alpaca secret key not configured - using mock trading")
                return
            
            # ========== SAFETY CHECK 1: Verify Paper Trading URL ==========
            if 'paper' not in base_url.lower():
                raise AlpacaSafetyError(
                    "❌ SAFETY VIOLATION: Base URL does not contain 'paper'! "
                    f"URL: {base_url}"
                )
            logger.info(f"✅ Safety Check 1: Paper Trading URL verified ({base_url})")
            
            # ========== SAFETY CHECK 2: Verify Paper Key Format ==========
            if not api_key.startswith('PK'):
                raise AlpacaSafetyError(
                    "❌ SAFETY VIOLATION: API key does not start with 'PK' (Paper Key)! "
                    f"Key starts with: {api_key[:2]}"
                )
            logger.info(f"✅ Safety Check 2: Paper API key format verified (PK...)")
            
            # ========== SAFETY CHECK 3: Verify Environment ==========
            environment = os.getenv('ENVIRONMENT', 'development')
            if environment == 'production':
                raise AlpacaSafetyError(
                    "❌ SAFETY VIOLATION: Cannot use paper trading in production! "
                    "Use live trading API for production."
                )
            logger.info(f"✅ Safety Check 3: Environment verified ({environment})")
            
            # Initialize Alpaca client
            logger.info("🔌 Connecting to Alpaca Paper Trading API...")
            self.alpaca = tradeapi.REST(
                api_key,
                secret_key,
                base_url,
                api_version='v2'
            )
            
            # ========== SAFETY CHECK 4: Verify Account is Paper ==========
            self.account_info = self.alpaca.get_account()
            
            if not self.account_info.account_number.startswith('P'):
                raise AlpacaSafetyError(
                    "❌ SAFETY VIOLATION: Account number does not start with 'P' (Paper Account)! "
                    f"Account: {self.account_info.account_number}"
                )
            logger.info(f"✅ Safety Check 4: Paper account verified (Account: {self.account_info.account_number})")
            
            # ========== SAFETY CHECK 5: Verify Account Status ==========
            if self.account_info.status != 'ACTIVE':
                logger.warning(f"⚠️  Account status: {self.account_info.status}")
            
            # Display account information
            logger.info("="*70)
            logger.info("🧪 ALPACA PAPER TRADING - SIMULATION MODE")
            logger.info("="*70)
            logger.info(f"   Account Number: {self.account_info.account_number}")
            logger.info(f"   Cash Available: ${float(self.account_info.cash):,.2f}")
            logger.info(f"   Buying Power: ${float(self.account_info.buying_power):,.2f}")
            logger.info(f"   Portfolio Value: ${float(self.account_info.portfolio_value):,.2f}")
            logger.info(f"   Account Status: {self.account_info.status}")
            logger.info("   ⚠️  THIS IS SIMULATED TRADING - NO REAL MONEY")
            logger.info("="*70)
            
            self.is_initialized = True
            logger.info("✅ AlpacaService initialized successfully - Paper Trading ACTIVE")
            
        except AlpacaSafetyError as e:
            logger.error(str(e))
            logger.error("🛑 ALPACA INITIALIZATION BLOCKED FOR SAFETY")
            raise
            
        except APIError as e:
            logger.error(f"❌ Alpaca API Error: {e}")
            logger.warning("⚠️  Falling back to mock trading")
            self.is_initialized = False
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpaca: {e}")
            logger.warning("⚠️  Falling back to mock trading")
            self.is_initialized = False
    
    def is_available(self) -> bool:
        """Check if Alpaca service is initialized and available."""
        return self.is_initialized and self.alpaca is not None
    
    async def get_account(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        if not self.is_available():
            return None
        
        try:
            account = self.alpaca.get_account()
            return {
                'account_number': account.account_number,
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'status': account.status
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    async def submit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,  # 'buy' or 'sell'
        order_type: str = 'market',
        time_in_force: str = 'day'
    ) -> Optional[Dict[str, Any]]:
        """
        Submit an order to Alpaca Paper Trading.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            quantity: Number of shares
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
        
        Returns:
            Order details or None if failed
        """
        if not self.is_available():
            logger.warning("Alpaca not available - cannot submit order")
            return None
        
        try:
            logger.info(f"📤 Submitting {side.upper()} order: {quantity} {symbol} ({order_type})")
            
            order = self.alpaca.submit_order(
                symbol=symbol.upper(),
                qty=quantity,
                side=side.lower(),
                type=order_type.lower(),
                time_in_force=time_in_force.lower()
            )
            
            logger.info(f"✅ Order submitted successfully - Order ID: {order.id}")
            logger.info(f"   Status: {order.status}")
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except APIError as e:
            logger.error(f"❌ Alpaca API Error submitting order: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error submitting order: {e}")
            return None
    
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position for a symbol."""
        if not self.is_available():
            return None
        
        try:
            position = self.alpaca.get_position(symbol.upper())
            return {
                'symbol': position.symbol,
                'quantity': int(position.qty),
                'avg_entry_price': float(position.avg_entry_price),
                'current_price': float(position.current_price),
                'market_value': float(position.market_value),
                'cost_basis': float(position.cost_basis),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc),
                'side': position.side
            }
        except APIError as e:
            if 'position does not exist' in str(e).lower():
                return None
            logger.error(f"Error getting position: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all current positions."""
        if not self.is_available():
            return []
        
        try:
            positions = self.alpaca.list_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'quantity': int(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'side': pos.side
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status."""
        if not self.is_available():
            return None
        
        try:
            order = self.alpaca.get_order(order_id)
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0
            }
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.alpaca:
            logger.info("Closing Alpaca connection")
            self.alpaca = None
        self.is_initialized = False
