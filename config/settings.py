"""Settings module for the Teams Trading Bot."""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from dataclasses import dataclass, field
from enum import Enum

class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Configuration settings for the Teams Trading Bot."""
    
    # Bot Framework Configuration
    APP_ID: str = Field(env="MicrosoftAppId", description="Microsoft Teams App ID")
    APP_PASSWORD: str = Field(env="MicrosoftAppPassword", description="Microsoft Teams App Password")
    
    # Azure Configuration
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = Field(None, description="Azure Storage Connection String")
    COSMOS_DB_ENDPOINT: Optional[str] = Field(None, description="Azure Cosmos DB Endpoint")
    COSMOS_DB_KEY: Optional[str] = Field(None, description="Azure Cosmos DB Key")
    
    # Redis Configuration
    REDIS_HOST: str = Field("localhost", description="Redis Cache Host")
    REDIS_PORT: int = Field(6379, description="Redis Cache Port")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis Cache Password")
    
    # Market Data Configuration
    MARKET_DATA_API_KEY: str = Field(env="MARKET_DATA_API_KEY", description="Market Data API Key")
    MARKET_DATA_ENDPOINT: str = Field("https://api.marketdata.com/v1", description="Market Data API Endpoint")
    
    # Trading Configuration
    MAX_POSITION_SIZE: float = Field(1000000.0, description="Maximum Position Size")
    RISK_TOLERANCE: float = Field(0.02, description="Risk Tolerance Level")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@dataclass
class MarketDataConfig:
    """Market data service configuration."""
    finnhub_api_key: str
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    cache_ttl_seconds: int = 60
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 10
    
    def __post_init__(self):
        """Validate market data configuration."""
        if not self.finnhub_api_key:
            raise ValueError("Finnhub API key is required")
        
        if self.rate_limit_per_minute <= 0:
            raise ValueError("Rate limit must be positive")
        
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class AlpacaConfig:
    """Alpaca trading platform configuration."""
    api_key: str = ""
    secret_key: str = ""
    base_url: str = "https://paper-api.alpaca.markets"  # Paper trading by default
    paper_trading: bool = True
    enabled: bool = False
    
    def __post_init__(self):
        """Validate Alpaca configuration."""
        if self.enabled and not self.api_key:
            raise ValueError("Alpaca API key is required when Alpaca is enabled")
        
        if self.enabled and not self.secret_key:
            raise ValueError("Alpaca secret key is required when Alpaca is enabled")


@dataclass
class TradingConfig:
    """Trading system configuration."""
    mock_execution_enabled: bool = True
    execution_delay_seconds: float = 1.0
    max_position_size: int = 10000
    max_trade_value: float = 1000000.0
    use_real_trading: bool = False  # Flag to enable real trading via Alpaca
    supported_symbols: List[str] = field(default_factory=lambda: [
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX"
    ])
    
    def __post_init__(self):
        """Validate trading configuration."""
        if self.execution_delay_seconds < 0:
            raise ValueError("Execution delay cannot be negative")
        
        if self.max_position_size <= 0:
            raise ValueError("Maximum position size must be positive")
        
        if self.max_trade_value <= 0:
            raise ValueError("Maximum trade value must be positive")


@dataclass
class SecurityConfig:
    """Security and compliance configuration."""
    approved_channels: List[str] = field(default_factory=list)
    session_timeout_minutes: int = 480  # 8 hours
    max_failed_attempts: int = 5
    audit_log_retention_days: int = 2555  # 7 years for compliance
    encryption_key_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate security configuration."""
        if self.session_timeout_minutes <= 0:
            raise ValueError("Session timeout must be positive")
        
        if self.max_failed_attempts <= 0:
            raise ValueError("Max failed attempts must be positive")
        
        if self.audit_log_retention_days <= 0:
            raise ValueError("Audit log retention must be positive")


@dataclass
class SlackConfig:
    """Slack configuration settings."""
    bot_token: str = Field(env="SLACK_BOT_TOKEN")
    signing_secret: str = Field(env="SLACK_SIGNING_SECRET")
    app_token: str = Field(env="SLACK_APP_TOKEN")
    channel_id: Optional[str] = Field(None, env="SLACK_CHANNEL_ID")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    oauth_redirect_url: Optional[str] = None
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0


@dataclass
class AWSConfig:
    """AWS configuration settings."""
    access_key_id: str = Field(env="AWS_ACCESS_KEY_ID")
    secret_access_key: str = Field(env="AWS_SECRET_ACCESS_KEY")
    region: str = Field(env="AWS_REGION", default="us-east-1")
    endpoint_url: Optional[str] = Field(None, env="AWS_ENDPOINT_URL")
    dynamodb_table_prefix: str = "jain-trading-bot"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    lambda_function_name: Optional[str] = None
    api_gateway_stage: str = "prod"
    
    def validate_aws_credentials(self) -> bool:
        """
        Validate AWS credentials.
        Returns:
            bool: True if credentials are valid
        """
        try:
            import boto3
            session = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
            # Try to make a simple API call to validate credentials
            sts = session.client('sts')
            sts.get_caller_identity()
            return True
        except Exception:
            return False


@dataclass
class AppConfig:
    """Main application configuration container."""
    environment: Environment
    log_level: LogLevel
    slack: SlackConfig
    aws: AWSConfig
    market_data: MarketDataConfig
    trading: TradingConfig
    security: SecurityConfig
    alpaca: AlpacaConfig
    
    # Application metadata
    app_name: str = "Jain Global Slack Trading Bot"
    app_version: str = "1.0.0"
    debug_mode: bool = False
    
    def __post_init__(self):
        """Perform comprehensive configuration validation."""
        self._validate_environment_consistency()
        self._setup_logging()
    
    def _validate_environment_consistency(self):
        """Ensure configuration is consistent with the deployment environment."""
        if self.environment == Environment.PRODUCTION:
            if self.debug_mode:
                raise ValueError("Debug mode cannot be enabled in production")
            
            if self.log_level == LogLevel.DEBUG:
                logging.warning("Debug logging enabled in production environment")
            
            if not self.aws.validate_aws_credentials():
                raise ValueError("Invalid AWS credentials for production environment")
        
        elif self.environment == Environment.DEVELOPMENT:
            if not self.trading.mock_execution_enabled:
                logging.warning("Real trading execution enabled in development")
    
    def _setup_logging(self):
        """Configure application logging based on environment and settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.value),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'{self.app_name.lower().replace(" ", "_")}.log')
            ]
        )
        
        # Suppress verbose AWS SDK logging in production
        if self.environment == Environment.PRODUCTION:
            logging.getLogger('boto3').setLevel(logging.WARNING)
            logging.getLogger('botocore').setLevel(logging.WARNING)
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get DynamoDB configuration for boto3 client initialization.
        
        Returns:
            Dict containing DynamoDB client configuration
        """
        return {
            'region_name': self.aws.region,
            'table_names': {
                'trades': self.aws.trades_table,
                'positions': self.aws.positions_table,
                'channels': self.aws.channels_table
            }
        }
    
    def get_slack_config(self) -> Dict[str, str]:
        """
        Get Slack configuration for Bolt app initialization.
        
        Returns:
            Dict containing Slack app configuration
        """
        config = {
            'token': self.slack.bot_token,
            'signing_secret': self.slack.signing_secret
        }
        
        if self.slack.app_token:
            config['app_token'] = self.slack.app_token
        
        return config
    
    def is_channel_approved(self, channel_id: str) -> bool:
        """
        Check if a channel is approved for trading operations.
        
        Args:
            channel_id: Slack channel ID to validate
            
        Returns:
            bool: True if channel is approved for trading
        """
        return channel_id in self.security.approved_channels
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for serialization.
        
        Returns:
            Dict representation of configuration (excluding sensitive data)
        """
        return {
            'app_name': self.app_name,
            'app_version': self.app_version,
            'environment': self.environment.value,
            'log_level': self.log_level.value,
            'debug_mode': self.debug_mode,
            'aws_region': self.aws.region,
            'trading_mock_enabled': self.trading.mock_execution_enabled,
            'approved_channels_count': len(self.security.approved_channels)
        }


class ConfigurationManager:
    """
    Centralized configuration management with environment variable loading and validation.
    
    This class handles loading configuration from environment variables, validating
    all settings, and providing a single source of truth for application configuration.
    """
    
    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigurationManager':
        """Implement singleton pattern for configuration manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager if not already initialized."""
        if self._config is None:
            self._config = self._load_configuration()
    
    def _load_configuration(self) -> AppConfig:
        """
        Load and validate configuration from environment variables.
        
        Returns:
            AppConfig: Validated application configuration
            
        Raises:
            ValueError: If required configuration is missing or invalid
            EnvironmentError: If environment setup is incorrect
        """
        try:
            # Load environment settings
            env_name = os.getenv('ENVIRONMENT', 'development').lower()
            environment = Environment(env_name)
            
            log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
            log_level = LogLevel(log_level_name)
            
            debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
            
            # Load Slack configuration
            slack_config = SlackConfig(
                bot_token=self._get_required_env('SLACK_BOT_TOKEN'),
                signing_secret=self._get_required_env('SLACK_SIGNING_SECRET'),
                app_token=os.getenv('SLACK_APP_TOKEN'),
                client_id=os.getenv('SLACK_CLIENT_ID'),
                client_secret=os.getenv('SLACK_CLIENT_SECRET'),
                oauth_redirect_url=os.getenv('SLACK_OAUTH_REDIRECT_URL')
            )
            
            # Load AWS configuration
            aws_config = AWSConfig(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                dynamodb_table_prefix=os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot'),
                bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0'),
                lambda_function_name=os.getenv('AWS_LAMBDA_FUNCTION_NAME'),
                api_gateway_stage=os.getenv('API_GATEWAY_STAGE', 'prod')
            )
            
            # Load market data configuration
            market_data_config = MarketDataConfig(
                finnhub_api_key=self._get_required_env('FINNHUB_API_KEY'),
                finnhub_base_url=os.getenv('FINNHUB_BASE_URL', 'https://finnhub.io/api/v1'),
                cache_ttl_seconds=int(os.getenv('MARKET_DATA_CACHE_TTL', '60')),
                rate_limit_per_minute=int(os.getenv('MARKET_DATA_RATE_LIMIT', '60')),
                timeout_seconds=int(os.getenv('MARKET_DATA_TIMEOUT', '10'))
            )
            
            # Load trading configuration
            supported_symbols = os.getenv('SUPPORTED_SYMBOLS', 'AAPL,GOOGL,MSFT,AMZN,TSLA,META,NVDA,NFLX').split(',')
            trading_config = TradingConfig(
                mock_execution_enabled=os.getenv('MOCK_EXECUTION_ENABLED', 'true').lower() == 'true',
                execution_delay_seconds=float(os.getenv('EXECUTION_DELAY_SECONDS', '1.0')),
                max_position_size=int(os.getenv('MAX_POSITION_SIZE', '10000')),
                max_trade_value=float(os.getenv('MAX_TRADE_VALUE', '1000000.0')),
                use_real_trading=os.getenv('USE_REAL_TRADING', 'false').lower() == 'true',
                supported_symbols=[s.strip().upper() for s in supported_symbols]
            )
            
            # Load Alpaca configuration
            alpaca_config = AlpacaConfig(
                api_key=os.getenv('ALPACA_API_KEY', ''),
                secret_key=os.getenv('ALPACA_SECRET_KEY', ''),
                base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
                paper_trading=os.getenv('ALPACA_PAPER_TRADING', 'true').lower() == 'true',
                enabled=os.getenv('ALPACA_ENABLED', 'false').lower() == 'true'
            )
            
            # Load security configuration
            approved_channels = os.getenv('APPROVED_CHANNELS', '').split(',')
            approved_channels = [ch.strip() for ch in approved_channels if ch.strip()]
            
            security_config = SecurityConfig(
                approved_channels=approved_channels,
                session_timeout_minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', '480')),
                max_failed_attempts=int(os.getenv('MAX_FAILED_ATTEMPTS', '5')),
                audit_log_retention_days=int(os.getenv('AUDIT_LOG_RETENTION_DAYS', '2555')),
                encryption_key_id=os.getenv('ENCRYPTION_KEY_ID')
            )
            
            # Create and return main configuration
            return AppConfig(
                environment=environment,
                log_level=log_level,
                slack=slack_config,
                aws=aws_config,
                market_data=market_data_config,
                trading=trading_config,
                security=security_config,
                alpaca=alpaca_config,
                debug_mode=debug_mode
            )
            
        except (ValueError, KeyError) as e:
            raise ValueError(f"Configuration error: {e}")
        except Exception as e:
            raise EnvironmentError(f"Failed to load configuration: {e}")
    
    def _get_required_env(self, key: str) -> str:
        """
        Get required environment variable with validation.
        
        Args:
            key: Environment variable name
            
        Returns:
            str: Environment variable value
            
        Raises:
            ValueError: If environment variable is not set or empty
        """
        value = os.getenv(key)
        if not value:
            # In development mode, provide mock values for required keys
            env_name = os.getenv('ENVIRONMENT', 'development').lower()
            if env_name == 'development':
                mock_values = {
                    'SLACK_BOT_TOKEN': 'xoxb-mock-development-token',
                    'SLACK_SIGNING_SECRET': 'mock-development-signing-secret-32chars',
                    'FINNHUB_API_KEY': 'mock-development-api-key'
                }
                if key in mock_values:
                    return mock_values[key]
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    @property
    def config(self) -> AppConfig:
        """Get the current application configuration."""
        return self._config
    
    def reload_configuration(self) -> AppConfig:
        """
        Reload configuration from environment variables.
        
        Returns:
            AppConfig: Newly loaded configuration
        """
        self._config = self._load_configuration()
        return self._config
    
    def validate_runtime_environment(self) -> bool:
        """
        Validate that the runtime environment meets all requirements.
        
        Returns:
            bool: True if environment is properly configured
        """
        try:
            # Validate AWS credentials and permissions (skip in development with placeholder credentials)
            aws_key = os.getenv('AWS_ACCESS_KEY_ID', '')
            is_development = self._config.environment.value == 'development'
            has_placeholder_aws = aws_key in ['', 'mock-access-key-id', 'your-aws-access-key']
            
            if not (is_development and has_placeholder_aws):
                if not self._config.aws.validate_aws_credentials():
                    logging.error("AWS credentials validation failed")
                    return False
            else:
                logging.info("Skipping AWS validation in development mode (placeholder credentials detected)")
            
            # Validate Slack configuration
            if not self._config.slack.bot_token or not self._config.slack.signing_secret:
                logging.error("Slack configuration is incomplete")
                return False
            
            # Validate market data access
            if not self._config.market_data.finnhub_api_key:
                logging.error("Market data API key is missing")
                return False
            
            # Environment-specific validations
            if self._config.environment == Environment.PRODUCTION:
                if not self._config.security.approved_channels:
                    logging.error("No approved channels configured for production")
                    return False
                
                if self._config.debug_mode:
                    logging.error("Debug mode enabled in production")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Runtime environment validation failed: {e}")
            return False


# Global configuration instance
config_manager = ConfigurationManager()


def get_config() -> AppConfig:
    """
    Get the global application configuration.
    
    Returns:
        AppConfig: Current application configuration
    """
    return config_manager.config


def reload_config() -> AppConfig:
    """
    Reload configuration from environment variables.
    
    Returns:
        AppConfig: Newly loaded configuration
    """
    return config_manager.reload_configuration()


def validate_environment() -> bool:
    """
    Validate that the runtime environment is properly configured.
    
    Returns:
        bool: True if environment validation passes
    """
    return config_manager.validate_runtime_environment()