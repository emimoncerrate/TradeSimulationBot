"""Microsoft Teams Trading Bot - Main Application Entry Point"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

# Create FastAPI app
app = FastAPI(
    title="Trading Bot API",
    description="API for Microsoft Teams Trading Bot with market data integration",
    version="1.0.0",
)

# Models
class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    order_type: str = "market"
    limit_price: Optional[float] = None

# Routes
@app.get("/")
async def root():
    """Get API status and information."""
    return {
        "name": "Trading Bot API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
import logging
import traceback
from collections import defaultdict, deque

# FastAPI
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Bot Framework
import azure.functions as func
from aiohttp import web
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    TurnContext,
    UserState,
)
from botbuilder.schema import Activity, ActivityTypes

# Create FastAPI app with OpenAPI documentation
app = FastAPI(
    title="Trading Bot API",
    description="""
    API for Microsoft Teams Trading Bot with market data integration.
    Features include:
    * Trade execution
    * Market data
    * Risk analysis
    * Portfolio management
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for API
from pydantic import BaseModel

class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    order_type: str = "market"
    limit_price: Optional[float] = None

class MarketDataRequest(BaseModel):
    symbol: str

# API endpoints
@app.get("/")
async def root():
    """Get API status and information."""
    return {
        "name": "Trading Bot API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/market-data/{symbol}")
async def get_market_data(symbol: str):
    """Get real-time market data for a symbol."""
    try:
        quote = await SERVICES.market_service.get_quote(symbol)
        return {
            "symbol": symbol,
            "price": quote["price"],
            "change": quote["change"],
            "volume": quote["volume"],
            "timestamp": quote["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/trade")
async def create_trade(trade: TradeRequest):
    """Create a new trade order."""
    try:
        order = await SERVICES.trading_service.create_order(
            symbol=trade.symbol,
            quantity=trade.quantity,
            order_type=trade.order_type,
            limit_price=trade.limit_price
        )
        return {
            "order_id": order["id"],
            "status": order["status"],
            "message": "Trade order created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating trade: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio holdings and performance."""
    try:
        portfolio = await SERVICES.trading_service.get_portfolio()
        return {
            "holdings": portfolio["holdings"],
            "total_value": portfolio["total_value"],
            "cash_balance": portfolio["cash_balance"],
            "daily_pnl": portfolio["daily_pnl"]
        }
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Application modules
from config.settings import Settings
from bot.teams_bot import TeamsTradeBot
from bot.middleware.auth_middleware import AuthenticationMiddleware
from bot.middleware.telemetry_middleware import TelemetryMiddleware
from services.service_container import ServiceContainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(settings.app_id, settings.app_password)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create storage
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)

# Create service container
SERVICES = ServiceContainer(settings)

# Create bot
BOT = TeamsTradeBot(CONVERSATION_STATE, USER_STATE, settings, SERVICES)

# Add middleware
ADAPTER.use(AuthenticationMiddleware(SERVICES.auth_service))
ADAPTER.use(TelemetryMiddleware(settings.application_insights_key))

async def init_func(context: func.Context, req: func.HttpRequest) -> func.HttpResponse:
    """Process a request to the bot framework."""
    if "application/json" not in req.headers.get("Content-Type", ""):
        return func.HttpResponse(
            "Unsupported content type",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )

    body = req.get_json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return func.HttpResponse(
            response.body,
            status_code=response.status,
            headers=response.headers.items(),
        )
    return func.HttpResponse(status_code=HTTPStatus.OK)
    
    def record_request(self, endpoint: str, response_time: float, error: Optional[str] = None):
        """Record request metrics."""
        with self._lock:
            self.request_count += 1
            self.response_times.append(response_time)
            
            # Update endpoint metrics
            endpoint_data = self.endpoint_metrics[endpoint]
            endpoint_data['count'] += 1
            
            # Calculate rolling average response time
            current_avg = endpoint_data['avg_time']
            count = endpoint_data['count']
            endpoint_data['avg_time'] = ((current_avg * (count - 1)) + response_time) / count
            
            if error:
                self.error_count += 1
                self.error_types[error] += 1
                endpoint_data['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current application metrics."""
        with self._lock:
            uptime = datetime.now(timezone.utc) - self.start_time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            return {
                'uptime_seconds': uptime.total_seconds(),
                'uptime_human': str(uptime),
                'total_requests': self.request_count,
                'total_errors': self.error_count,
                'error_rate': (self.error_count / self.request_count) if self.request_count > 0 else 0,
                'average_response_time_ms': avg_response_time * 1000,
                'recent_response_times_ms': [t * 1000 for t in list(self.response_times)[-10:]],
                'error_types': dict(self.error_types),
                'endpoint_metrics': dict(self.endpoint_metrics),
                'circuit_breaker_states': dict(self.circuit_breaker_states),
                'health_checks': dict(self.health_checks)
            }
    
    def update_circuit_breaker(self, service: str, state: str, error_rate: float = 0.0):
        """Update circuit breaker state for a service."""
        with self._lock:
            self.circuit_breaker_states[service] = {
                'state': state,
                'error_rate': error_rate,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    def update_health_check(self, service: str, healthy: bool, details: Optional[str] = None):
        """Update health check status for a service."""
        with self._lock:
            self.health_checks[service] = {
                'healthy': healthy,
                'details': details,
                'last_checked': datetime.now(timezone.utc).isoformat()
            }

# Global metrics instance
app_metrics = ApplicationMetrics()

class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker logic."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == 'OPEN':
                    if self._should_attempt_reset():
                        self.state = 'HALF_OPEN'
                        logger.info(f"Circuit breaker for {func.__name__} moved to HALF_OPEN")
                    else:
                        app_metrics.update_circuit_breaker(func.__name__, 'OPEN', 1.0)
                        raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success(func.__name__)
                    return result
                except self.expected_exception as e:
                    self._on_failure(func.__name__)
                    raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self, func_name: str):
        """Handle successful function execution."""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            logger.info(f"Circuit breaker for {func_name} reset to CLOSED")
        app_metrics.update_circuit_breaker(func_name, self.state, 0.0)
    
    def _on_failure(self, func_name: str):
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.error(f"Circuit breaker for {func_name} opened due to {self.failure_count} failures")
        
        error_rate = self.failure_count / self.failure_threshold
        app_metrics.update_circuit_breaker(func_name, self.state, error_rate)

# Application lifecycle management
class ApplicationLifecycle:
    """Manages application startup, shutdown, and resource cleanup."""
    
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.background_tasks = []
        self.cleanup_handlers = []
        self.is_shutting_down = False
    
    def register_cleanup_handler(self, handler: Callable):
        """Register a cleanup handler to be called during shutdown."""
        self.cleanup_handlers.append(handler)
    
    def start_background_task(self, task: Callable, interval: int = 60):
        """Start a background task that runs at specified intervals."""
        def run_task():
            while not self.shutdown_event.is_set():
                try:
                    task()
                except Exception as e:
                    logger.error(f"Background task error: {e}")
                
                # Wait for interval or shutdown signal
                self.shutdown_event.wait(interval)
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        self.background_tasks.append(thread)
        logger.info(f"Started background task: {task.__name__}")
    
    def initiate_shutdown(self, signum=None, frame=None):
        """Initiate graceful shutdown process."""
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self.is_shutting_down = True
        logger.info(f"Initiating graceful shutdown (signal: {signum})")
        
        # Signal all background tasks to stop
        self.shutdown_event.set()
        
        # Run cleanup handlers
        for handler in self.cleanup_handlers:
            try:
                handler()
                logger.info(f"Cleanup handler {handler.__name__} completed")
            except Exception as e:
                logger.error(f"Cleanup handler {handler.__name__} failed: {e}")
        
        # Wait for background tasks to complete
        for task in self.background_tasks:
            task.join(timeout=5)
        
        logger.info("Graceful shutdown completed")

# Global lifecycle manager
lifecycle = ApplicationLifecycle()

# Performance monitoring decorator
def monitor_performance(endpoint_name: str):
    """Decorator to monitor endpoint performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = type(e).__name__
                raise
            finally:
                response_time = time.time() - start_time
                app_metrics.record_request(endpoint_name, response_time, error)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = type(e).__name__
                raise
            finally:
                response_time = time.time() - start_time
                app_metrics.record_request(endpoint_name, response_time, error)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Initialize Slack Bolt app with comprehensive configuration
@CircuitBreaker(failure_threshold=3, recovery_timeout=30)
def create_slack_app() -> App:
    """
    Create and configure the Slack Bolt application with comprehensive middleware,
    error handling, and monitoring capabilities.
    
    Returns:
        App: Configured Slack Bolt application instance
        
    Raises:
        Exception: If Slack app initialization fails
    """
    try:
        logger.info("Initializing Slack Bolt application...")
        
        # Get Slack configuration
        slack_config = config.get_slack_config()
        
        # Create Slack app with configuration
        app = App(
            token=slack_config['token'],
            signing_secret=slack_config['signing_secret'],
            process_before_response=True,  # Important for Lambda
            request_verification_enabled=True
        )
        
        # Register comprehensive middleware stack
        register_middleware(app)
        
        # Register event handlers with error handling and service injection
        try:
            register_command_handlers(app, service_container)
            logger.info("Command handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register command handlers: {e}")
            raise
        
        try:
            register_action_handlers(app, service_container)
            logger.info("Action handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register action handlers: {e}")
            raise
        
        # Register interactive action handlers
        try:
            from listeners.interactive_actions import interactive_handler
            interactive_handler.register_handlers(app)
            logger.info("Interactive action handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register interactive action handlers: {e}")
            raise
        
        try:
            register_event_handlers(app, service_container)
            logger.info("Event handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
            raise
        
        # Register risk alert handlers
        try:
            from services.auth import AuthService
            register_risk_alert_handlers(
                app=app,
                db_service=service_container.get(DatabaseService),
                auth_service=service_container.get(AuthService),
                alert_monitor=alert_monitor,
                notification_service=notification_service
            )
            logger.info("Risk alert handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register risk alert handlers: {e}")
            # Don't raise - alert feature is optional, don't break app startup
        
        # Register global error handler
        @app.error
        def global_error_handler(error, body, logger):
            """Global error handler for unhandled exceptions."""
            error_id = f"error_{int(time.time())}"
            user_id = body.get('user_id', 'unknown')
            channel_id = body.get('channel_id', 'unknown')
            
            logger.error(
                f"Global error {error_id}: {error} | "
                f"User: {user_id} | Channel: {channel_id} | "
                f"Body: {json.dumps(body, default=str)[:500]}"
            )
            
            # Record error metrics
            app_metrics.record_request('global_error', 0, type(error).__name__)
            
            # Return user-friendly error message
            return {
                "response_type": "ephemeral",
                "text": f"⚠️ An unexpected error occurred. Error ID: {error_id}\n"
                       f"Please try again or contact support if the issue persists."
            }
        
        logger.info("Slack Bolt app initialized successfully")
        app_metrics.update_health_check('slack_app', True, 'Initialized successfully')
        return app
        
    except Exception as e:
        logger.error(f"Failed to initialize Slack app: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        app_metrics.update_health_check('slack_app', False, str(e))
        raise

def register_middleware(app: App) -> None:
    """
    Register comprehensive middleware stack for the Slack app including
    request logging, performance monitoring, security validation, and error handling.
    
    Args:
        app: Slack Bolt application instance
    """
    
    @app.middleware
    def request_logging_middleware(body: Dict[str, Any], next):
        """Comprehensive request logging and audit trail middleware."""
        start_time = time.time()
        request_id = body.get('event_id') or body.get('trigger_id') or f"req_{int(time.time())}"
        user_id = body.get('user_id', 'unknown')
        event_type = body.get('type', 'unknown')
        
        # Log request start
        logger.info(
            f"[{request_id}] Request started | "
            f"Type: {event_type} | User: {user_id} | "
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}"
        )
        
        # Log request body for debugging (truncated)
        if config.debug_mode:
            body_str = json.dumps(body, default=str)[:1000]
            logger.debug(f"[{request_id}] Request body: {body_str}")
        
        try:
            # Call next middleware/handler
            response = next()
            
            # Log successful completion
            duration = time.time() - start_time
            logger.info(
                f"[{request_id}] Request completed successfully | "
                f"Duration: {duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] Request failed | "
                f"Duration: {duration:.3f}s | Error: {e}"
            )
            raise
    
    @app.middleware
    def security_validation_middleware(body: Dict[str, Any], next):
        """Security validation middleware for channel restrictions and user authorization."""
        # Skip validation for certain event types
        skip_validation = [
            'url_verification',
            'app_home_opened',
            'tokens_revoked',
            'app_uninstalled'
        ]
        
        event_type = body.get('type')
        if event_type in skip_validation:
            return next()
        
        # Extract channel ID from various possible locations
        channel_id = None
        if 'channel_id' in body:
            channel_id = body['channel_id']
        elif 'event' in body and 'channel' in body['event']:
            channel_id = body['event']['channel']
        elif 'channel' in body:
            channel_id = body['channel']
        elif 'payload' in body and isinstance(body['payload'], dict):
            payload = body['payload']
            if 'channel' in payload and isinstance(payload['channel'], dict):
                channel_id = payload['channel'].get('id')
        
        # Validate channel if present
        if channel_id:
            if not config.is_channel_approved(channel_id):
                logger.warning(
                    f"Request from unapproved channel: {channel_id} | "
                    f"User: {body.get('user_id', 'unknown')} | "
                    f"Type: {event_type}"
                )
                
                # In production, block unapproved channels
                if config.environment.value == 'production':
                    return {
                        "response_type": "ephemeral",
                        "text": "🚫 This bot is not authorized to operate in this channel. "
                               "Please contact your administrator for access."
                    }
        
        # Additional security checks
        user_id = body.get('user_id')
        if user_id:
            # Log user activity for audit trail
            logger.info(f"User activity: {user_id} in channel {channel_id} - {event_type}")
        
        return next()
    
    @app.middleware
    def performance_monitoring_middleware(body: Dict[str, Any], next):
        """Performance monitoring and metrics collection middleware."""
        start_time = time.time()
        event_type = body.get('type', 'unknown')
        
        try:
            response = next()
            
            # Record successful request metrics
            duration = time.time() - start_time
            app_metrics.record_request(f"slack_{event_type}", duration)
            
            # Log slow requests
            if duration > 3.0:  # 3 second threshold
                logger.warning(
                    f"Slow request detected | Type: {event_type} | "
                    f"Duration: {duration:.3f}s | User: {body.get('user_id', 'unknown')}"
                )
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            app_metrics.record_request(f"slack_{event_type}", duration, type(e).__name__)
            raise
    
    @app.middleware
    def rate_limiting_middleware(body: Dict[str, Any], next):
        """Basic rate limiting middleware to prevent abuse."""
        user_id = body.get('user_id')
        if not user_id:
            return next()
        
        # Simple in-memory rate limiting (in production, use Redis or similar)
        current_time = time.time()
        if not hasattr(rate_limiting_middleware, 'user_requests'):
            rate_limiting_middleware.user_requests = defaultdict(list)
        
        user_requests = rate_limiting_middleware.user_requests[user_id]
        
        # Clean old requests (older than 1 minute)
        user_requests[:] = [req_time for req_time in user_requests if current_time - req_time < 60]
        
        # Check rate limit (max 30 requests per minute per user)
        if len(user_requests) >= 30:
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            return {
                "response_type": "ephemeral",
                "text": "⚠️ Rate limit exceeded. Please wait a moment before trying again."
            }
        
        # Record this request
        user_requests.append(current_time)
        
        return next()
    
    logger.info("Middleware stack registered successfully")

# Create Slack app instance with error handling
# Skip auto-creation if SKIP_APP_INIT is set (useful for testing)
if os.getenv('SKIP_APP_INIT', 'false').lower() != 'true':
    try:
        slack_app = create_slack_app()
        logger.info("Slack app instance created successfully")
    except Exception as e:
        logger.critical(f"Failed to create Slack app instance: {e}")
        slack_app = None
else:
    logger.info("Skipping Slack app auto-initialization (SKIP_APP_INIT is set)")
    slack_app = None

# Lambda handler for AWS deployment with comprehensive error handling
@monitor_performance('lambda_handler')
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Slack events with comprehensive error handling,
    performance monitoring, and graceful degradation.
    
    Args:
        event: Lambda event data containing HTTP request information
        context: Lambda context object with runtime information
        
    Returns:
        Dict containing HTTP response with status code and body
        
    Raises:
        Exception: Re-raises critical errors after logging
    """
    request_id = context.aws_request_id if context else f"lambda_{int(time.time())}"
    
    try:
        logger.info(f"[{request_id}] Lambda handler started | Remaining time: {context.get_remaining_time_in_millis() if context else 'unknown'}ms")
        
        # Validate Slack app instance
        if slack_app is None:
            logger.error(f"[{request_id}] Slack app not initialized")
            return {
                'statusCode': 503,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Service temporarily unavailable',
                    'request_id': request_id
                })
            }
        
        # Validate environment on cold start
        if not validate_environment():
            logger.error(f"[{request_id}] Environment validation failed")
            app_metrics.update_health_check('environment', False, 'Validation failed')
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Environment validation failed',
                    'request_id': request_id
                })
            }
        
        # Update health check
        app_metrics.update_health_check('environment', True, 'Validation passed')
        
        # Create Slack request handler with timeout handling
        handler = SlackRequestHandler(app=slack_app)
        
        # Check remaining execution time
        if context and context.get_remaining_time_in_millis() < 5000:  # Less than 5 seconds
            logger.warning(f"[{request_id}] Low remaining execution time: {context.get_remaining_time_in_millis()}ms")
        
        # Process the request
        logger.debug(f"[{request_id}] Processing Slack request")
        response = handler.handle(event, context)
        
        # Validate response
        if not isinstance(response, dict) or 'statusCode' not in response:
            logger.error(f"[{request_id}] Invalid response format from handler")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Invalid response format',
                    'request_id': request_id
                })
            }
        
        status_code = response.get('statusCode', 200)
        logger.info(f"[{request_id}] Lambda request processed successfully | Status: {status_code}")
        
        # Add request ID to response headers
        if 'headers' not in response:
            response['headers'] = {}
        response['headers']['X-Request-ID'] = request_id
        
        return response
        
    except Exception as e:
        logger.error(f"[{request_id}] Lambda handler error: {e}")
        logger.error(f"[{request_id}] Stack trace: {traceback.format_exc()}")
        
        # Update error metrics
        app_metrics.record_request('lambda_handler', 0, type(e).__name__)
        
        # Return error response
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'X-Request-ID': request_id
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'request_id': request_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

# Background tasks for monitoring and maintenance
def health_check_task():
    """Background task to perform periodic health checks."""
    try:
        # Check environment validation
        env_healthy = validate_environment()
        app_metrics.update_health_check('environment', env_healthy)
        
        # Check Slack app health
        slack_healthy = slack_app is not None
        app_metrics.update_health_check('slack_app', slack_healthy)
        
        # Log health status
        if config.debug_mode:
            metrics = app_metrics.get_metrics()
            logger.debug(f"Health check completed | Metrics: {json.dumps(metrics, default=str)[:500]}")
        
    except Exception as e:
        logger.error(f"Health check task error: {e}")

def cleanup_metrics_task():
    """Background task to clean up old metrics data."""
    try:
        # Reset error counts if they're getting too high
        if app_metrics.error_count > 10000:
            logger.info("Resetting error count metrics")
            app_metrics.error_count = 0
            app_metrics.error_types.clear()
        
        # Clean up old endpoint metrics
        current_time = time.time()
        for endpoint in list(app_metrics.endpoint_metrics.keys()):
            # Reset metrics for endpoints not used in last hour
            # This is a simple cleanup - in production, use more sophisticated logic
            pass
        
    except Exception as e:
        logger.error(f"Metrics cleanup task error: {e}")

# FastAPI app for local development with comprehensive configuration
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("FastAPI application starting up...")
    
    try:
        # Initialize and start all services
        logger.info("Starting service container...")
        await service_container.start_all_services()
        logger.info("All services started successfully")
        
        # Start background tasks
        lifecycle.start_background_task(health_check_task, interval=30)
        lifecycle.start_background_task(cleanup_metrics_task, interval=300)  # 5 minutes
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, lifecycle.initiate_shutdown)
        signal.signal(signal.SIGINT, lifecycle.initiate_shutdown)
        
        # Register service container shutdown
        lifecycle.register_cleanup_handler(lambda: asyncio.create_task(service_container.stop_all_services()))
        
        logger.info("FastAPI application startup completed")
        
    except Exception as e:
        logger.error(f"Failed to start application services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("FastAPI application shutting down...")
    
    try:
        # Stop all services
        logger.info("Stopping service container...")
        await service_container.stop_all_services()
        logger.info("All services stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping services: {e}")
    
    lifecycle.initiate_shutdown()

fastapi_app = FastAPI(
    title="Jain Global Slack Trading Bot",
    description="Slack Trading Bot for Jain Global investment management with comprehensive monitoring and error handling",
    version=config.app_version,
    lifespan=lifespan,
    docs_url="/docs" if config.debug_mode else None,
    redoc_url="/redoc" if config.debug_mode else None
)

# Add security middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://slack.com"] if config.environment.value == 'production' else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if config.environment.value == 'production':
    fastapi_app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.amazonaws.com", "*.slack.com"]
    )

@fastapi_app.get("/health")
@monitor_performance('health_check')
async def health_check():
    """
    Comprehensive health check endpoint for monitoring, load balancers, and observability.
    
    Returns detailed health information including service status, metrics, and diagnostics.
    """
    try:
        # Validate environment
        env_valid = validate_environment()
        
        # Get comprehensive metrics
        metrics = app_metrics.get_metrics()
        
        # Determine overall health status
        overall_healthy = (
            env_valid and
            slack_app is not None and
            metrics['error_rate'] < 0.1  # Less than 10% error rate
        )
        
        health_data = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': config.app_version,
            'environment': config.environment.value,
            'uptime_seconds': metrics['uptime_seconds'],
            'config_valid': env_valid,
            'slack_app_initialized': slack_app is not None,
            'metrics': {
                'total_requests': metrics['total_requests'],
                'total_errors': metrics['total_errors'],
                'error_rate': metrics['error_rate'],
                'average_response_time_ms': metrics['average_response_time_ms']
            },
            'health_checks': metrics['health_checks'],
            'circuit_breakers': metrics['circuit_breaker_states']
        }
        
        # Add detailed diagnostics in debug mode
        if config.debug_mode:
            health_data['detailed_metrics'] = metrics
            health_data['config_summary'] = config.to_dict()
        
        return JSONResponse(
            status_code=200 if overall_healthy else 503,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        logger.error(f"Health check stack trace: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': config.app_version
            }
        )

@fastapi_app.get("/metrics")
@monitor_performance('metrics_endpoint')
async def metrics_endpoint():
    """
    Detailed metrics endpoint for monitoring and observability.
    
    Returns comprehensive application metrics including performance data,
    error rates, and service health information.
    """
    try:
        if not config.debug_mode and config.environment.value == 'production':
            # In production, require authentication or restrict access
            raise HTTPException(status_code=404, detail="Not found")
        
        metrics = app_metrics.get_metrics()
        
        return JSONResponse(
            status_code=200,
            content={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'application': {
                    'name': config.app_name,
                    'version': config.app_version,
                    'environment': config.environment.value
                },
                'metrics': metrics,
                'configuration': config.to_dict()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@fastapi_app.get("/ready")
@monitor_performance('readiness_check')
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes and container orchestration.
    
    Returns 200 if the application is ready to serve traffic, 503 otherwise.
    """
    try:
        # Check if all critical components are ready
        ready = (
            slack_app is not None and
            validate_environment() and
            not lifecycle.is_shutting_down
        )
        
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                'ready': ready,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'shutting_down': lifecycle.is_shutting_down
            }
        )
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'ready': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

@fastapi_app.get("/services")
@monitor_performance('services_status')
async def services_status():
    """
    Service status endpoint for monitoring service health and performance.
    
    Returns detailed information about all registered services including
    their current state, health status, uptime, and error counts.
    """
    try:
        if not config.debug_mode and config.environment.value == 'production':
            # In production, require authentication or restrict access
            raise HTTPException(status_code=404, detail="Not found")
        
        service_status = service_container.get_service_status()
        
        return JSONResponse(
            status_code=200,
            content={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service_container': service_status,
                'application': {
                    'name': config.app_name,
                    'version': config.app_version,
                    'environment': config.environment.value
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Services status endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Root endpoint that returns basic API information."""
    return {
        "name": "Trading Bot API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/messages")
async def messages(request: Request):
    """Handle incoming bot messages."""
    if "application/json" not in request.headers["Content-Type"]:
        return Response(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return Response(json.dumps(response.body), status_code=response.status)
    return Response(status_code=HTTPStatus.OK)