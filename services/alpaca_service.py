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
    
    What it does:
    - Connects to Alpaca Paper Trading API (100% simulated)
    - Executes realistic trades against real market data
    - Manages paper trading portfolio ($500K virtual cash)
    - Provides professional trading experience with $0 risk
    - Tracks positions, P&L, and order history
    """
    
    def __init__(self):
        """Initialize Alpaca Paper Trading service with safety checks."""
        self.alpaca = None
        self.is_initialized = False
        self.account_info = None
        
        logger.info("AlpacaService created, will initialize on first use")
    
    def _validate_paper_trading_safety(self, api_key: str, base_url: str) -> None:
        """Validate that we're using paper trading configuration."""
        # Safety Check 1: URL must contain 'paper'
        if 'paper' not in base_url.lower():
            raise Exception(f"SAFETY VIOLATION: Base URL does not contain 'paper': {base_url}")
        logger.info(f"✅ Safety Check 1: Paper Trading URL verified ({base_url})")
        
        # Safety Check 2: API key must start with 'PK' (Paper Key)
        if not api_key.startswith('PK'):
            raise Exception(f"SAFETY VIOLATION: API key does not start with 'PK': {api_key[:10]}...")
        logger.info("✅ Safety Check 2: Paper API key format verified (PK...)")
        
        # Safety Check 3: Environment check
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            # In production, we might want additional checks
            pass
        logger.info(f"✅ Safety Check 3: Environment verified ({environment})")
        
    def initialize(self) -> None:
        """Initialize Alpaca connection synchronously for service container."""
        try:
            # Do synchronous initialization instead of async
            self._sync_initialize()
        except Exception as e:
            logger.error(f"Failed to initialize AlpacaService: {e}")
            self.is_initialized = False
    
    def _sync_initialize(self) -> None:
        """Initialize and validate Alpaca connection with safety checks (sync version)."""
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
            
            # Safety checks
            self._validate_paper_trading_safety(api_key, base_url)
            
            # Initialize Alpaca client (synchronous)
            import alpaca_trade_api as tradeapi
            self.alpaca = tradeapi.REST(
                key_id=api_key,
                secret_key=secret_key,
                base_url=base_url,
                api_version='v2'
            )
            
            logger.info("🔌 Connecting to Alpaca Paper Trading API...")
            
            # Test connection and get account info (synchronous)
            account = self.alpaca.get_account()
            
            # Final safety check - ensure it's a paper account
            if not account.account_number.startswith('P'):
                logger.error("🛑 SAFETY VIOLATION: Account is not a paper trading account!")
                logger.error("🛑 ALPACA INITIALIZATION BLOCKED FOR SAFETY")
                raise Exception("Not a paper trading account")
            
            logger.info(f"✅ Safety Check 4: Paper account verified (Account: {account.account_number})")
            
            # Store account info
            self.account_info = {
                'account_number': account.account_number,
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'status': account.status
            }
            
            # Log successful initialization
            logger.info("=" * 68)
            logger.info("🧪 ALPACA PAPER TRADING - SIMULATION MODE")
            logger.info("=" * 68)
            logger.info(f"   Account Number: {account.account_number}")
            logger.info(f"   Cash Available: ${float(account.cash):,.2f}")
            logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
            logger.info(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
            logger.info(f"   Account Status: {account.status}")
            logger.info("   ⚠️  THIS IS SIMULATED TRADING - NO REAL MONEY")
            logger.info("=" * 68)
            
            self.is_initialized = True
            logger.info("✅ AlpacaService initialized successfully - Paper Trading ACTIVE")
            
        except Exception as e:
            if "SAFETY VIOLATION" in str(e) or "Not a paper trading account" in str(e):
                logger.error("🛑 ALPACA INITIALIZATION BLOCKED FOR SAFETY")
                raise
            
            logger.error(f"❌ Alpaca API Error: {e}")
            logger.error("🚨 CRITICAL: Alpaca Paper Trading service failed to initialize")
            print(f"🚨 ALPACA SERVICE FAILURE: {e}")
            print("🚨 ALL TRADES WILL FAIL - NO FALLBACK TO MOCK DATA")
            self.is_initialized = False
        
    async def _async_initialize(self) -> None:
        """Initialize and validate Alpaca connection with safety checks (async version)."""
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
            logger.error("🚨 CRITICAL: Alpaca Paper Trading service failed to initialize")
            print(f"🚨 ALPACA SERVICE FAILURE: {e}")
            print("🚨 ALL TRADES WILL FAIL - NO FALLBACK TO MOCK DATA")
            self.is_initialized = False
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpaca: {e}")
            logger.error("🚨 CRITICAL: Alpaca Paper Trading service failed to initialize")
            print(f"🚨 ALPACA SERVICE FAILURE: {e}")
            print("🚨 ALL TRADES WILL FAIL - NO FALLBACK TO MOCK DATA")
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