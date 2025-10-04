"""
Comprehensive market data service with Finnhub integration for Jain Global Slack Trading Bot.

This module provides real-time market data fetching, symbol validation, market status checking,
and comprehensive caching with rate limiting and error handling. It integrates with the Finnhub
API to provide accurate, up-to-date financial market information for trading decisions.

The service implements sophisticated retry logic, circuit breaker patterns, and fallback
mechanisms to ensure reliable operation even when external APIs are experiencing issues.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

import aiohttp
import redis
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


class MarketStatus(Enum):
    """Market status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    HOLIDAY = "holiday"
    UNKNOWN = "unknown"


class DataQuality(Enum):
    """Data quality indicators."""
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    STALE = "stale"
    CACHED = "cached"
    FALLBACK = "fallback"


@dataclass
class MarketQuote:
    """
    Comprehensive market quote data structure.
    
    Contains all relevant market data for a security including price information,
    volume, market status, and data quality indicators.
    """
    symbol: str
    current_price: Decimal
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    pe_ratio: Optional[Decimal] = None
    
    # Market timing and status
    timestamp: datetime = field(default_factory=datetime.utcnow)
    market_status: MarketStatus = MarketStatus.UNKNOWN
    data_quality: DataQuality = DataQuality.REAL_TIME
    
    # Metadata
    exchange: Optional[str] = None
    currency: str = "USD"
    timezone: str = "America/New_York"
    
    # Data source tracking
    source: str = "finnhub"
    cache_hit: bool = False
    api_latency_ms: Optional[float] = None
    
    def __post_init__(self):
        """Validate quote data after initialization."""
        if self.current_price <= 0:
            raise ValueError(f"Invalid current price for {self.symbol}: {self.current_price}")
        
        if self.volume is not None and self.volume < 0:
            raise ValueError(f"Invalid volume for {self.symbol}: {self.volume}")
    
    @property
    def price_change(self) -> Optional[Decimal]:
        """Calculate price change from previous close."""
        if self.previous_close is None:
            return None
        return self.current_price - self.previous_close
    
    @property
    def price_change_percent(self) -> Optional[Decimal]:
        """Calculate percentage price change from previous close."""
        if self.previous_close is None or self.previous_close == 0:
            return None
        return (self.price_change / self.previous_close) * 100
    
    @property
    def is_stale(self) -> bool:
        """Check if quote data is considered stale (older than 5 minutes)."""
        return datetime.utcnow() - self.timestamp > timedelta(minutes=5)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quote to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'current_price': float(self.current_price),
            'open_price': float(self.open_price) if self.open_price else None,
            'high_price': float(self.high_price) if self.high_price else None,
            'low_price': float(self.low_price) if self.low_price else None,
            'previous_close': float(self.previous_close) if self.previous_close else None,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'pe_ratio': float(self.pe_ratio) if self.pe_ratio else None,
            'timestamp': self.timestamp.isoformat(),
            'market_status': self.market_status.value,
            'data_quality': self.data_quality.value,
            'exchange': self.exchange,
            'currency': self.currency,
            'timezone': self.timezone,
            'source': self.source,
            'cache_hit': self.cache_hit,
            'api_latency_ms': self.api_latency_ms,
            'price_change': float(self.price_change) if self.price_change else None,
            'price_change_percent': float(self.price_change_percent) if self.price_change_percent else None,
            'is_stale': self.is_stale
        }


@dataclass
class SymbolInfo:
    """Symbol information and validation data."""
    symbol: str
    display_symbol: str
    description: str
    type: str  # 'Common Stock', 'ETF', etc.
    exchange: str
    currency: str = "USD"
    is_tradable: bool = True
    market_cap: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol info to dictionary."""
        return {
            'symbol': self.symbol,
            'display_symbol': self.display_symbol,
            'description': self.description,
            'type': self.type,
            'exchange': self.exchange,
            'currency': self.currency,
            'is_tradable': self.is_tradable,
            'market_cap': self.market_cap,
            'sector': self.sector,
            'industry': self.industry
        }


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Implements a token bucket algorithm to ensure API rate limits are respected
    while allowing for burst requests when tokens are available.
    """
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire a token for making a request.
        
        Returns:
            bool: True if token acquired, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = int(elapsed * (self.max_requests / self.time_window))
            
            if tokens_to_add > 0:
                self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
                self.last_refill = now
            
            # Check if we have tokens available
            if self.tokens > 0:
                self.tokens -= 1
                return True
            
            return False
    
    async def wait_for_token(self) -> None:
        """Wait until a token becomes available."""
        while not await self.acquire():
            await asyncio.sleep(0.1)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API resilience.
    
    Prevents cascading failures by temporarily stopping requests to a failing service
    and allowing it time to recover.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half_open"
                else:
                    raise Exception("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as e:
                await self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    async def _on_success(self):
        """Handle successful request."""
        self.failure_count = 0
        self.state = "closed"
    
    async def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class MarketDataService:
    """
    Comprehensive market data service with Finnhub integration.
    
    Provides real-time market data, symbol validation, caching, rate limiting,
    and comprehensive error handling for the Slack trading bot. Implements
    sophisticated retry logic and fallback mechanisms for high availability.
    """
    
    def __init__(self):
        """Initialize market data service with configuration and dependencies."""
        self.config = get_config()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize caching
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Tuple[MarketQuote, datetime]] = {}
        
        # Initialize rate limiting and circuit breaker
        self.rate_limiter = RateLimiter(
            max_requests=self.config.market_data.rate_limit_per_minute,
            time_window=60
        )
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Metrics
        self.request_counter = Counter(
            'market_data_requests_total',
            'Total market data requests',
            ['endpoint', 'status']
        )
        self.request_duration = Histogram(
            'market_data_request_duration_seconds',
            'Market data request duration',
            ['endpoint']
        )
        self.cache_hit_counter = Counter(
            'market_data_cache_hits_total',
            'Cache hits for market data',
            ['cache_type']
        )
        self.api_error_counter = Counter(
            'market_data_api_errors_total',
            'API errors by type',
            ['error_type']
        )
        
        # Symbol cache for validation
        self.symbol_cache: Dict[str, SymbolInfo] = {}
        self.symbol_cache_expiry = datetime.utcnow()
        
        self.logger.info("MarketDataService initialized", 
                        api_key_configured=bool(self.config.market_data.finnhub_api_key),
                        rate_limit=self.config.market_data.rate_limit_per_minute)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize(self) -> None:
        """Initialize async resources."""
        # Initialize HTTP session with proper configuration
        timeout = aiohttp.ClientTimeout(total=self.config.market_data.timeout_seconds)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Jain-Global-Trading-Bot/1.0',
                'Accept': 'application/json'
            }
        )
        
        # Initialize Redis cache if available
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=5
            )
            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.ping
            )
            self.logger.info("Redis cache initialized successfully")
        except Exception as e:
            self.logger.warning("Redis cache not available, using memory cache only", error=str(e))
            self.redis_client = None
        
        self.logger.info("MarketDataService initialization complete")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        self.logger.info("MarketDataService cleanup complete")
    
    async def get_quote(self, symbol: str, use_cache: bool = True) -> MarketQuote:
        """
        Get real-time quote for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            use_cache: Whether to use cached data if available
            
        Returns:
            MarketQuote: Comprehensive quote data
            
        Raises:
            ValueError: If symbol is invalid
            Exception: If API request fails after retries
        """
        symbol = symbol.upper().strip()
        
        if not self._is_valid_symbol_format(symbol):
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        # Check cache first if enabled
        if use_cache:
            cached_quote = await self._get_cached_quote(symbol)
            if cached_quote and not cached_quote.is_stale:
                self.cache_hit_counter.labels(cache_type='hit').inc()
                self.logger.debug("Cache hit for symbol", symbol=symbol)
                return cached_quote
        
        # Fetch from API with circuit breaker protection
        try:
            quote = await self.circuit_breaker.call(self._fetch_quote_from_api, symbol)
            
            # Cache the result
            await self._cache_quote(symbol, quote)
            
            self.logger.info("Quote fetched successfully", 
                           symbol=symbol, 
                           price=float(quote.current_price),
                           data_quality=quote.data_quality.value)
            
            return quote
            
        except Exception as e:
            self.api_error_counter.labels(error_type=type(e).__name__).inc()
            self.logger.error("Failed to fetch quote", symbol=symbol, error=str(e))
            
            # Try to return stale cached data as fallback
            cached_quote = await self._get_cached_quote(symbol)
            if cached_quote:
                cached_quote.data_quality = DataQuality.STALE
                self.logger.warning("Returning stale cached data", symbol=symbol)
                return cached_quote
            
            raise e
    
    async def get_multiple_quotes(self, symbols: List[str], use_cache: bool = True) -> Dict[str, MarketQuote]:
        """
        Get quotes for multiple symbols efficiently.
        
        Args:
            symbols: List of stock symbols
            use_cache: Whether to use cached data if available
            
        Returns:
            Dict mapping symbols to MarketQuote objects
        """
        if not symbols:
            return {}
        
        # Normalize symbols
        symbols = [s.upper().strip() for s in symbols]
        
        # Create tasks for concurrent fetching
        tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._safe_get_quote(symbol, use_cache))
            tasks.append((symbol, task))
        
        # Wait for all tasks to complete
        results = {}
        for symbol, task in tasks:
            try:
                quote = await task
                results[symbol] = quote
            except Exception as e:
                self.logger.error("Failed to fetch quote in batch", symbol=symbol, error=str(e))
                # Continue with other symbols
        
        self.logger.info("Batch quote fetch complete", 
                        requested=len(symbols), 
                        successful=len(results))
        
        return results
    
    async def validate_symbol(self, symbol: str) -> SymbolInfo:
        """
        Validate and get information about a trading symbol.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            SymbolInfo: Symbol information and validation data
            
        Raises:
            ValueError: If symbol is not found or invalid
        """
        symbol = symbol.upper().strip()
        
        # Check symbol cache first
        if symbol in self.symbol_cache and datetime.utcnow() < self.symbol_cache_expiry:
            return self.symbol_cache[symbol]
        
        # Fetch symbol information from API
        try:
            symbol_info = await self.circuit_breaker.call(self._fetch_symbol_info, symbol)
            
            # Cache the result
            self.symbol_cache[symbol] = symbol_info
            
            self.logger.info("Symbol validated successfully", 
                           symbol=symbol, 
                           description=symbol_info.description)
            
            return symbol_info
            
        except Exception as e:
            self.logger.error("Symbol validation failed", symbol=symbol, error=str(e))
            raise ValueError(f"Invalid or unknown symbol: {symbol}")
    
    async def get_market_status(self, exchange: str = "US") -> MarketStatus:
        """
        Get current market status for an exchange.
        
        Args:
            exchange: Exchange code (default: "US")
            
        Returns:
            MarketStatus: Current market status
        """
        try:
            status = await self.circuit_breaker.call(self._fetch_market_status, exchange)
            
            self.logger.debug("Market status fetched", exchange=exchange, status=status.value)
            return status
            
        except Exception as e:
            self.logger.error("Failed to fetch market status", exchange=exchange, error=str(e))
            return MarketStatus.UNKNOWN
    
    async def search_symbols(self, query: str, limit: int = 10) -> List[SymbolInfo]:
        """
        Search for symbols matching a query.
        
        Args:
            query: Search query (company name or symbol)
            limit: Maximum number of results
            
        Returns:
            List of matching SymbolInfo objects
        """
        if not query or len(query.strip()) < 2:
            return []
        
        try:
            results = await self.circuit_breaker.call(self._search_symbols_api, query, limit)
            
            self.logger.info("Symbol search completed", 
                           query=query, 
                           results_count=len(results))
            
            return results
            
        except Exception as e:
            self.logger.error("Symbol search failed", query=query, error=str(e))
            return []
    
    async def _safe_get_quote(self, symbol: str, use_cache: bool = True) -> MarketQuote:
        """Safely get quote with error handling for batch operations."""
        try:
            return await self.get_quote(symbol, use_cache)
        except Exception as e:
            # Return a fallback quote for failed requests
            return MarketQuote(
                symbol=symbol,
                current_price=Decimal('0.00'),
                data_quality=DataQuality.FALLBACK,
                timestamp=datetime.utcnow()
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    async def _fetch_quote_from_api(self, symbol: str) -> MarketQuote:
        """
        Fetch quote data from Finnhub API with retry logic.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            MarketQuote: Quote data from API
            
        Raises:
            Exception: If API request fails
        """
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        # Wait for rate limit token
        await self.rate_limiter.wait_for_token()
        
        start_time = time.time()
        
        try:
            # Fetch real-time quote
            quote_url = f"https://finnhub.io/api/v1/quote"
            quote_params = {
                'symbol': symbol,
                'token': self.config.market_data.finnhub_api_key
            }
            
            async with self.session.get(quote_url, params=quote_params) as response:
                if response.status == 429:
                    self.api_error_counter.labels(error_type='rate_limit').inc()
                    raise Exception("Rate limit exceeded")
                
                if response.status != 200:
                    self.api_error_counter.labels(error_type='http_error').inc()
                    raise Exception(f"API request failed with status {response.status}")
                
                quote_data = await response.json()
            
            # Fetch company profile for additional data
            profile_url = f"https://finnhub.io/api/v1/stock/profile2"
            profile_params = {
                'symbol': symbol,
                'token': self.config.market_data.finnhub_api_key
            }
            
            async with self.session.get(profile_url, params=profile_params) as response:
                profile_data = await response.json() if response.status == 200 else {}
            
            # Calculate API latency
            api_latency = (time.time() - start_time) * 1000
            
            # Build MarketQuote object
            quote = self._build_market_quote(symbol, quote_data, profile_data, api_latency)
            
            self.request_counter.labels(endpoint='quote', status='success').inc()
            self.request_duration.labels(endpoint='quote').observe(time.time() - start_time)
            
            return quote
            
        except Exception as e:
            self.request_counter.labels(endpoint='quote', status='error').inc()
            self.logger.error("API request failed", symbol=symbol, error=str(e))
            raise e
    
    async def _fetch_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        Fetch symbol information from Finnhub API.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            SymbolInfo: Symbol information
        """
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        await self.rate_limiter.wait_for_token()
        
        try:
            # Fetch company profile
            url = f"https://finnhub.io/api/v1/stock/profile2"
            params = {
                'symbol': symbol,
                'token': self.config.market_data.finnhub_api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}")
                
                data = await response.json()
                
                if not data or 'name' not in data:
                    raise ValueError(f"Symbol not found: {symbol}")
                
                return SymbolInfo(
                    symbol=symbol,
                    display_symbol=data.get('ticker', symbol),
                    description=data.get('name', ''),
                    type='Common Stock',  # Default type
                    exchange=data.get('exchange', ''),
                    currency=data.get('currency', 'USD'),
                    is_tradable=True,
                    market_cap=data.get('marketCapitalization'),
                    sector=data.get('finnhubIndustry', ''),
                    industry=data.get('finnhubIndustry', '')
                )
                
        except Exception as e:
            self.logger.error("Failed to fetch symbol info", symbol=symbol, error=str(e))
            raise e
    
    async def _fetch_market_status(self, exchange: str) -> MarketStatus:
        """
        Fetch market status from Finnhub API.
        
        Args:
            exchange: Exchange code
            
        Returns:
            MarketStatus: Current market status
        """
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        await self.rate_limiter.wait_for_token()
        
        try:
            url = f"https://finnhub.io/api/v1/stock/market-status"
            params = {
                'exchange': exchange,
                'token': self.config.market_data.finnhub_api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return MarketStatus.UNKNOWN
                
                data = await response.json()
                
                if data.get('isOpen'):
                    return MarketStatus.OPEN
                else:
                    return MarketStatus.CLOSED
                    
        except Exception as e:
            self.logger.error("Failed to fetch market status", exchange=exchange, error=str(e))
            return MarketStatus.UNKNOWN
    
    async def _search_symbols_api(self, query: str, limit: int) -> List[SymbolInfo]:
        """
        Search symbols using Finnhub API.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of SymbolInfo objects
        """
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        await self.rate_limiter.wait_for_token()
        
        try:
            url = f"https://finnhub.io/api/v1/search"
            params = {
                'q': query,
                'token': self.config.market_data.finnhub_api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                results = []
                
                for item in data.get('result', [])[:limit]:
                    symbol_info = SymbolInfo(
                        symbol=item.get('symbol', ''),
                        display_symbol=item.get('displaySymbol', ''),
                        description=item.get('description', ''),
                        type=item.get('type', ''),
                        exchange='',  # Not provided in search results
                        currency='USD'
                    )
                    results.append(symbol_info)
                
                return results
                
        except Exception as e:
            self.logger.error("Symbol search API failed", query=query, error=str(e))
            return []
    
    def _build_market_quote(self, symbol: str, quote_data: Dict, profile_data: Dict, api_latency: float) -> MarketQuote:
        """
        Build MarketQuote object from API response data.
        
        Args:
            symbol: Stock symbol
            quote_data: Quote data from API
            profile_data: Profile data from API
            api_latency: API request latency in milliseconds
            
        Returns:
            MarketQuote: Constructed quote object
        """
        try:
            current_price = Decimal(str(quote_data.get('c', 0)))
            if current_price <= 0:
                raise ValueError(f"Invalid price data for {symbol}")
            
            return MarketQuote(
                symbol=symbol,
                current_price=current_price,
                open_price=Decimal(str(quote_data.get('o', 0))) if quote_data.get('o') else None,
                high_price=Decimal(str(quote_data.get('h', 0))) if quote_data.get('h') else None,
                low_price=Decimal(str(quote_data.get('l', 0))) if quote_data.get('l') else None,
                previous_close=Decimal(str(quote_data.get('pc', 0))) if quote_data.get('pc') else None,
                volume=None,  # Not provided in basic quote
                market_cap=profile_data.get('marketCapitalization'),
                timestamp=datetime.utcnow(),
                market_status=MarketStatus.UNKNOWN,  # Would need separate call
                data_quality=DataQuality.REAL_TIME,
                exchange=profile_data.get('exchange', ''),
                currency=profile_data.get('currency', 'USD'),
                source='finnhub',
                cache_hit=False,
                api_latency_ms=api_latency
            )
            
        except (ValueError, TypeError, KeyError) as e:
            self.logger.error("Failed to build quote object", symbol=symbol, error=str(e))
            raise ValueError(f"Invalid quote data for {symbol}: {e}")
    
    async def _get_cached_quote(self, symbol: str) -> Optional[MarketQuote]:
        """
        Get cached quote from Redis or memory cache.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Cached MarketQuote or None if not found
        """
        # Try Redis cache first
        if self.redis_client:
            try:
                cached_data = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.get, f"quote:{symbol}"
                )
                
                if cached_data:
                    quote_dict = json.loads(cached_data)
                    quote = self._dict_to_market_quote(quote_dict)
                    quote.cache_hit = True
                    return quote
                    
            except Exception as e:
                self.logger.warning("Redis cache read failed", symbol=symbol, error=str(e))
        
        # Try memory cache
        if symbol in self.memory_cache:
            quote, cached_time = self.memory_cache[symbol]
            
            # Check if cache entry is still valid (5 minutes)
            if datetime.utcnow() - cached_time < timedelta(minutes=5):
                quote.cache_hit = True
                return quote
            else:
                # Remove stale entry
                del self.memory_cache[symbol]
        
        return None
    
    async def _cache_quote(self, symbol: str, quote: MarketQuote) -> None:
        """
        Cache quote in Redis and memory.
        
        Args:
            symbol: Stock symbol
            quote: MarketQuote to cache
        """
        # Cache in Redis with 5-minute expiration
        if self.redis_client:
            try:
                quote_dict = quote.to_dict()
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.redis_client.setex,
                    f"quote:{symbol}",
                    300,  # 5 minutes
                    json.dumps(quote_dict)
                )
            except Exception as e:
                self.logger.warning("Redis cache write failed", symbol=symbol, error=str(e))
        
        # Cache in memory as backup
        self.memory_cache[symbol] = (quote, datetime.utcnow())
        
        # Limit memory cache size
        if len(self.memory_cache) > 1000:
            # Remove oldest entries
            oldest_symbols = sorted(
                self.memory_cache.keys(),
                key=lambda s: self.memory_cache[s][1]
            )[:100]
            
            for old_symbol in oldest_symbols:
                del self.memory_cache[old_symbol]
    
    def _dict_to_market_quote(self, data: Dict) -> MarketQuote:
        """
        Convert dictionary back to MarketQuote object.
        
        Args:
            data: Dictionary representation of MarketQuote
            
        Returns:
            MarketQuote object
        """
        return MarketQuote(
            symbol=data['symbol'],
            current_price=Decimal(str(data['current_price'])),
            open_price=Decimal(str(data['open_price'])) if data.get('open_price') else None,
            high_price=Decimal(str(data['high_price'])) if data.get('high_price') else None,
            low_price=Decimal(str(data['low_price'])) if data.get('low_price') else None,
            previous_close=Decimal(str(data['previous_close'])) if data.get('previous_close') else None,
            volume=data.get('volume'),
            market_cap=data.get('market_cap'),
            pe_ratio=Decimal(str(data['pe_ratio'])) if data.get('pe_ratio') else None,
            timestamp=datetime.fromisoformat(data['timestamp']),
            market_status=MarketStatus(data['market_status']),
            data_quality=DataQuality(data['data_quality']),
            exchange=data.get('exchange', ''),
            currency=data.get('currency', 'USD'),
            timezone=data.get('timezone', 'America/New_York'),
            source=data.get('source', 'finnhub'),
            cache_hit=data.get('cache_hit', False),
            api_latency_ms=data.get('api_latency_ms')
        )
    
    def _is_valid_symbol_format(self, symbol: str) -> bool:
        """
        Validate symbol format.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            bool: True if format is valid
        """
        if not symbol or len(symbol) < 1 or len(symbol) > 10:
            return False
        
        # Allow alphanumeric characters, dots, and hyphens
        import re
        return bool(re.match(r'^[A-Z0-9.-]+$', symbol))
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status for monitoring.
        
        Returns:
            Dict containing health status information
        """
        status = {
            'service': 'MarketDataService',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'circuit_breaker_state': self.circuit_breaker.state,
            'cache_status': {
                'redis_available': self.redis_client is not None,
                'memory_cache_size': len(self.memory_cache)
            },
            'rate_limiter': {
                'tokens_available': self.rate_limiter.tokens,
                'max_requests': self.rate_limiter.max_requests
            }
        }
        
        # Test API connectivity
        try:
            if self.session:
                test_url = "https://finnhub.io/api/v1/quote"
                test_params = {
                    'symbol': 'AAPL',
                    'token': self.config.market_data.finnhub_api_key
                }
                
                async with self.session.get(test_url, params=test_params) as response:
                    status['api_connectivity'] = response.status == 200
            else:
                status['api_connectivity'] = False
                
        except Exception as e:
            status['api_connectivity'] = False
            status['api_error'] = str(e)
        
        return status


# Global service instance
_market_data_service: Optional[MarketDataService] = None


async def get_market_data_service() -> MarketDataService:
    """
    Get or create the global MarketDataService instance.
    
    Returns:
        MarketDataService: Initialized service instance
    """
    global _market_data_service
    
    if _market_data_service is None:
        _market_data_service = MarketDataService()
        await _market_data_service.initialize()
    
    return _market_data_service


async def cleanup_market_data_service() -> None:
    """Clean up the global MarketDataService instance."""
    global _market_data_service
    
    if _market_data_service:
        await _market_data_service.cleanup()
        _market_data_service = None