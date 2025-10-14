"""
Comprehensive input validation utilities for the Slack Trading Bot.

This module provides extensive validation functions for trade parameters,
symbols, security checks, and user input validation with detailed error
handling and logging capabilities.
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timezone
import json

# Configure logging
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)


class ValidationResult:
    """
    Result of a validation operation.
    
    Attributes:
        is_valid: Whether validation passed
        errors: List of validation errors
        warnings: List of validation warnings
        cleaned_value: Cleaned/normalized value if validation passed
        metadata: Additional validation metadata
    """
    
    def __init__(self, is_valid: bool = True, cleaned_value: Any = None):
        self.is_valid = is_valid
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.cleaned_value = cleaned_value
        self.metadata: Dict[str, Any] = {}
    
    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(message, field, code))
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)
    
    def get_error_messages(self) -> List[str]:
        """Get list of error messages."""
        return [error.message for error in self.errors]
    
    def get_first_error(self) -> Optional[ValidationError]:
        """Get the first validation error."""
        return self.errors[0] if self.errors else None


class SymbolValidator:
    """Validator for stock symbols and securities."""
    
    # Common stock exchanges and their symbol patterns
    EXCHANGE_PATTERNS = {
        'NYSE': r'^[A-Z]{1,5}$',
        'NASDAQ': r'^[A-Z]{1,5}$',
        'AMEX': r'^[A-Z]{1,5}$',
        'OTC': r'^[A-Z]{1,5}$',
        'TSX': r'^[A-Z]{1,5}\.TO$',
        'LSE': r'^[A-Z]{1,4}\.L$',
        'XETRA': r'^[A-Z]{1,4}\.DE$'
    }
    
    # Known invalid symbols or reserved words
    INVALID_SYMBOLS = {
        'TEST', 'DEMO', 'SAMPLE', 'NULL', 'NONE', 'UNDEFINED',
        'CASH', 'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD'
    }
    
    # Common symbol suffixes that indicate special securities
    SPECIAL_SUFFIXES = {
        '.PK': 'Pink Sheets',
        '.OB': 'OTC Bulletin Board',
        '.TO': 'Toronto Stock Exchange',
        '.V': 'TSX Venture Exchange',
        '.L': 'London Stock Exchange',
        '.DE': 'XETRA',
        '.PA': 'Euronext Paris',
        '.AS': 'Euronext Amsterdam'
    }
    
    @classmethod
    def validate_symbol(cls, symbol: str, allow_international: bool = True) -> ValidationResult:
        """
        Validate a stock symbol.
        
        Args:
            symbol: Stock symbol to validate
            allow_international: Whether to allow international symbols
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        if not symbol or not isinstance(symbol, str):
            result.add_error("Symbol must be a non-empty string", "symbol", "INVALID_TYPE")
            return result
        
        # Clean and normalize symbol
        cleaned_symbol = symbol.strip().upper()
        
        if not cleaned_symbol:
            result.add_error("Symbol cannot be empty or whitespace", "symbol", "EMPTY_SYMBOL")
            return result
        
        # Check length
        if len(cleaned_symbol) > 12:  # Allow for international symbols with suffixes
            result.add_error("Symbol cannot exceed 12 characters", "symbol", "SYMBOL_TOO_LONG")
            return result
        
        if len(cleaned_symbol) < 1:
            result.add_error("Symbol must be at least 1 character", "symbol", "SYMBOL_TOO_SHORT")
            return result
        
        # Check for invalid symbols
        base_symbol = cleaned_symbol.split('.')[0]  # Remove exchange suffix
        if base_symbol in cls.INVALID_SYMBOLS:
            result.add_error(f"'{base_symbol}' is not a valid trading symbol", "symbol", "INVALID_SYMBOL")
            return result
        
        # Validate format
        is_valid_format = False
        detected_exchange = None
        
        for exchange, pattern in cls.EXCHANGE_PATTERNS.items():
            if re.match(pattern, cleaned_symbol):
                is_valid_format = True
                detected_exchange = exchange
                break
        
        if not is_valid_format:
            # Check if it's an international symbol
            if '.' in cleaned_symbol and allow_international:
                suffix = '.' + cleaned_symbol.split('.', 1)[1]
                if suffix in cls.SPECIAL_SUFFIXES:
                    is_valid_format = True
                    detected_exchange = cls.SPECIAL_SUFFIXES[suffix]
                    result.add_warning(f"International symbol detected: {detected_exchange}")
        
        if not is_valid_format:
            result.add_error(
                f"Symbol '{cleaned_symbol}' does not match any known exchange format",
                "symbol",
                "INVALID_FORMAT"
            )
            return result
        
        # Additional checks for specific patterns
        if re.search(r'[0-9]', base_symbol):
            result.add_warning("Symbol contains numbers, which is unusual for stock symbols")
        
        if len(base_symbol) == 1:
            result.add_warning("Single-character symbols are rare and may indicate special securities")
        
        # Set metadata
        result.metadata = {
            'detected_exchange': detected_exchange,
            'base_symbol': base_symbol,
            'has_suffix': '.' in cleaned_symbol,
            'is_international': '.' in cleaned_symbol and allow_international
        }
        
        result.cleaned_value = cleaned_symbol
        logger.debug(f"Symbol validation passed: {cleaned_symbol} ({detected_exchange})")
        
        return result


class TradeParameterValidator:
    """Validator for trade parameters and constraints."""
    
    # Trading limits and constraints
    MIN_QUANTITY = 1
    MAX_QUANTITY = 1000000
    MIN_PRICE = Decimal('0.01')
    MAX_PRICE = Decimal('100000.00')
    MAX_TRADE_VALUE = Decimal('10000000.00')  # $10M
    
    # Risk thresholds
    HIGH_VALUE_THRESHOLD = Decimal('100000.00')  # $100k
    HIGH_QUANTITY_THRESHOLD = 10000
    UNUSUAL_PRICE_CHANGE_THRESHOLD = Decimal('0.20')  # 20%
    
    @classmethod
    def validate_quantity(cls, quantity: Union[int, str, float]) -> ValidationResult:
        """
        Validate trade quantity.
        
        Args:
            quantity: Quantity to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        # Type conversion and validation
        try:
            if isinstance(quantity, str):
                # Remove commas and whitespace
                quantity_str = quantity.replace(',', '').strip()
                quantity_int = int(float(quantity_str))  # Handle "100.0" format
            elif isinstance(quantity, float):
                if quantity != int(quantity):
                    result.add_error("Quantity must be a whole number", "quantity", "NOT_INTEGER")
                    return result
                quantity_int = int(quantity)
            elif isinstance(quantity, int):
                quantity_int = quantity
            else:
                result.add_error("Quantity must be a number", "quantity", "INVALID_TYPE")
                return result
        except (ValueError, TypeError):
            result.add_error("Quantity must be a valid number", "quantity", "INVALID_NUMBER")
            return result
        
        # Range validation
        if quantity_int <= 0:
            result.add_error("Quantity must be positive", "quantity", "NOT_POSITIVE")
            return result
        
        if quantity_int < cls.MIN_QUANTITY:
            result.add_error(f"Quantity must be at least {cls.MIN_QUANTITY}", "quantity", "BELOW_MINIMUM")
            return result
        
        if quantity_int > cls.MAX_QUANTITY:
            result.add_error(f"Quantity cannot exceed {cls.MAX_QUANTITY:,}", "quantity", "ABOVE_MAXIMUM")
            return result
        
        # Risk warnings
        if quantity_int > cls.HIGH_QUANTITY_THRESHOLD:
            result.add_warning(f"Large quantity trade: {quantity_int:,} shares")
            result.metadata['risk_level'] = 'high'
        elif quantity_int > cls.HIGH_QUANTITY_THRESHOLD // 2:
            result.add_warning(f"Medium quantity trade: {quantity_int:,} shares")
            result.metadata['risk_level'] = 'medium'
        else:
            result.metadata['risk_level'] = 'low'
        
        result.cleaned_value = quantity_int
        logger.debug(f"Quantity validation passed: {quantity_int}")
        
        return result
    
    @classmethod
    def validate_price(cls, price: Union[Decimal, str, float], symbol: Optional[str] = None,
                      market_price: Optional[Decimal] = None) -> ValidationResult:
        """
        Validate trade price.
        
        Args:
            price: Price to validate
            symbol: Stock symbol for context
            market_price: Current market price for comparison
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        # Type conversion and validation
        try:
            if isinstance(price, str):
                # Remove currency symbols and whitespace
                price_str = price.replace('$', '').replace(',', '').strip()
                price_decimal = Decimal(price_str)
            elif isinstance(price, (int, float)):
                price_decimal = Decimal(str(price))
            elif isinstance(price, Decimal):
                price_decimal = price
            else:
                result.add_error("Price must be a number", "price", "INVALID_TYPE")
                return result
        except (InvalidOperation, ValueError, TypeError):
            result.add_error("Price must be a valid decimal number", "price", "INVALID_NUMBER")
            return result
        
        # Range validation
        if price_decimal <= 0:
            result.add_error("Price must be positive", "price", "NOT_POSITIVE")
            return result
        
        if price_decimal < cls.MIN_PRICE:
            result.add_error(f"Price must be at least ${cls.MIN_PRICE}", "price", "BELOW_MINIMUM")
            return result
        
        if price_decimal > cls.MAX_PRICE:
            result.add_error(f"Price cannot exceed ${cls.MAX_PRICE:,}", "price", "ABOVE_MAXIMUM")
            return result
        
        # Market price comparison
        if market_price is not None and market_price > 0:
            price_diff = abs(price_decimal - market_price)
            price_diff_pct = price_diff / market_price
            
            if price_diff_pct > cls.UNUSUAL_PRICE_CHANGE_THRESHOLD:
                result.add_warning(
                    f"Price ${price_decimal} differs significantly from market price ${market_price} "
                    f"({price_diff_pct:.1%} difference)"
                )
                result.metadata['price_deviation'] = float(price_diff_pct)
                result.metadata['risk_level'] = 'high'
            elif price_diff_pct > cls.UNUSUAL_PRICE_CHANGE_THRESHOLD / 2:
                result.add_warning(f"Price differs from market price by {price_diff_pct:.1%}")
                result.metadata['price_deviation'] = float(price_diff_pct)
                result.metadata['risk_level'] = 'medium'
            else:
                result.metadata['risk_level'] = 'low'
        
        # Penny stock warning
        if price_decimal < Decimal('5.00'):
            result.add_warning(f"Low-priced security: ${price_decimal}")
            result.metadata['is_penny_stock'] = True
        
        result.cleaned_value = price_decimal
        logger.debug(f"Price validation passed: ${price_decimal}")
        
        return result
    
    @classmethod
    def validate_trade_type(cls, trade_type: str) -> ValidationResult:
        """
        Validate trade type.
        
        Args:
            trade_type: Trade type to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        if not trade_type or not isinstance(trade_type, str):
            result.add_error("Trade type must be a non-empty string", "trade_type", "INVALID_TYPE")
            return result
        
        cleaned_type = trade_type.strip().lower()
        
        valid_types = ['buy', 'sell', 'long', 'short']
        
        if cleaned_type not in valid_types:
            result.add_error(
                f"Trade type must be one of: {', '.join(valid_types)}",
                "trade_type",
                "INVALID_VALUE"
            )
            return result
        
        # Normalize to standard values
        if cleaned_type in ['long']:
            cleaned_type = 'buy'
        elif cleaned_type in ['short']:
            cleaned_type = 'sell'
        
        result.cleaned_value = cleaned_type
        logger.debug(f"Trade type validation passed: {cleaned_type}")
        
        return result
    
    @classmethod
    def validate_complete_trade(cls, symbol: str, quantity: Union[int, str, float],
                              price: Union[Decimal, str, float], trade_type: str,
                              market_price: Optional[Decimal] = None,
                              user_cash_balance: Optional[Decimal] = None) -> ValidationResult:
        """
        Validate a complete trade with cross-field validation.
        
        Args:
            symbol: Stock symbol
            quantity: Trade quantity
            price: Trade price
            trade_type: Type of trade
            market_price: Current market price
            user_cash_balance: User's available cash
            
        Returns:
            ValidationResult with comprehensive validation
        """
        result = ValidationResult()
        validated_data = {}
        
        # Validate each field individually
        symbol_result = SymbolValidator.validate_symbol(symbol)
        quantity_result = cls.validate_quantity(quantity)
        price_result = cls.validate_price(price, symbol, market_price)
        type_result = cls.validate_trade_type(trade_type)
        
        # Collect all errors
        for field_result in [symbol_result, quantity_result, price_result, type_result]:
            result.errors.extend(field_result.errors)
            result.warnings.extend(field_result.warnings)
            if not field_result.is_valid:
                result.is_valid = False
        
        # If basic validation failed, return early
        if not result.is_valid:
            return result
        
        # Extract validated values
        validated_data['symbol'] = symbol_result.cleaned_value
        validated_data['quantity'] = quantity_result.cleaned_value
        validated_data['price'] = price_result.cleaned_value
        validated_data['trade_type'] = type_result.cleaned_value
        
        # Cross-field validation
        trade_value = validated_data['price'] * Decimal(str(validated_data['quantity']))
        
        # Check maximum trade value
        if trade_value > cls.MAX_TRADE_VALUE:
            result.add_error(
                f"Trade value ${trade_value:,.2f} exceeds maximum allowed ${cls.MAX_TRADE_VALUE:,.2f}",
                "trade_value",
                "TRADE_VALUE_TOO_HIGH"
            )
        
        # Check cash balance for buy orders
        if validated_data['trade_type'] == 'buy' and user_cash_balance is not None:
            if trade_value > user_cash_balance:
                result.add_error(
                    f"Insufficient funds: ${trade_value:,.2f} required, ${user_cash_balance:,.2f} available",
                    "cash_balance",
                    "INSUFFICIENT_FUNDS"
                )
        
        # Risk assessment
        risk_factors = []
        overall_risk = 'low'
        
        if trade_value > cls.HIGH_VALUE_THRESHOLD:
            risk_factors.append(f"High value trade: ${trade_value:,.2f}")
            overall_risk = 'high'
        
        if validated_data['quantity'] > cls.HIGH_QUANTITY_THRESHOLD:
            risk_factors.append(f"Large quantity: {validated_data['quantity']:,} shares")
            overall_risk = 'high'
        
        if price_result.metadata.get('is_penny_stock'):
            risk_factors.append("Penny stock trading")
            if overall_risk == 'low':
                overall_risk = 'medium'
        
        if price_result.metadata.get('price_deviation', 0) > 0.1:
            risk_factors.append("Significant price deviation from market")
            overall_risk = 'high'
        
        # Add risk warnings
        if risk_factors:
            result.add_warning(f"Risk factors identified: {'; '.join(risk_factors)}")
        
        # Set metadata
        result.metadata = {
            'trade_value': float(trade_value),
            'risk_level': overall_risk,
            'risk_factors': risk_factors,
            'requires_confirmation': overall_risk in ['high', 'critical'],
            'symbol_metadata': symbol_result.metadata,
            'price_metadata': price_result.metadata
        }
        
        result.cleaned_value = validated_data
        logger.info(f"Complete trade validation: {overall_risk} risk, ${trade_value:,.2f} value")
        
        return result


class SecurityValidator:
    """Security-focused validation for preventing malicious input."""
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'eval\s*\(',  # eval() calls
        r'exec\s*\(',  # exec() calls
        r'import\s+',  # Import statements
        r'__\w+__',  # Python dunder methods
        r'\.\./',  # Directory traversal
        r'[;&|`$]',  # Shell injection characters
    ]
    
    # Maximum lengths for different field types
    MAX_LENGTHS = {
        'symbol': 12,
        'user_id': 50,
        'channel_id': 50,
        'notes': 500,
        'reason': 200,
        'name': 100
    }
    
    @classmethod
    def sanitize_input(cls, value: str, field_type: str = 'general') -> ValidationResult:
        """
        Sanitize and validate input for security.
        
        Args:
            value: Input value to sanitize
            field_type: Type of field for specific validation
            
        Returns:
            ValidationResult with sanitized value
        """
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error("Input must be a string", field_type, "INVALID_TYPE")
            return result
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                result.add_error(
                    f"Input contains potentially dangerous content",
                    field_type,
                    "SECURITY_VIOLATION"
                )
                return result
        
        # Check length limits
        max_length = cls.MAX_LENGTHS.get(field_type, 1000)
        if len(value) > max_length:
            result.add_error(
                f"Input exceeds maximum length of {max_length} characters",
                field_type,
                "TOO_LONG"
            )
            return result
        
        # Basic sanitization
        sanitized = value.strip()
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')
        
        # Field-specific sanitization
        if field_type == 'symbol':
            sanitized = re.sub(r'[^A-Z0-9.]', '', sanitized.upper())
        elif field_type in ['user_id', 'channel_id']:
            sanitized = re.sub(r'[^A-Z0-9_-]', '', sanitized.upper())
        elif field_type == 'notes':
            # Allow more characters but remove dangerous ones
            sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        result.cleaned_value = sanitized
        logger.debug(f"Input sanitized for {field_type}: {len(value)} -> {len(sanitized)} chars")
        
        return result
    
    @classmethod
    def validate_slack_user_id(cls, user_id: str) -> ValidationResult:
        """
        Validate Slack user ID format.
        
        Args:
            user_id: Slack user ID to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        if not user_id or not isinstance(user_id, str):
            result.add_error("User ID must be a non-empty string", "user_id", "INVALID_TYPE")
            return result
        
        # Slack user IDs start with 'U' followed by alphanumeric characters
        if not re.match(r'^U[A-Z0-9]{8,10}$', user_id.upper()):
            result.add_error("Invalid Slack user ID format", "user_id", "INVALID_FORMAT")
            return result
        
        result.cleaned_value = user_id.upper()
        return result
    
    @classmethod
    def validate_slack_channel_id(cls, channel_id: str) -> ValidationResult:
        """
        Validate Slack channel ID format.
        
        Args:
            channel_id: Slack channel ID to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        if not channel_id or not isinstance(channel_id, str):
            result.add_error("Channel ID must be a non-empty string", "channel_id", "INVALID_TYPE")
            return result
        
        # Slack channel IDs start with 'C' or 'G' followed by alphanumeric characters
        if not re.match(r'^[CG][A-Z0-9]{8,10}$', channel_id.upper()):
            result.add_error("Invalid Slack channel ID format", "channel_id", "INVALID_FORMAT")
            return result
        
        result.cleaned_value = channel_id.upper()
        return result


class ValidationUtils:
    """Utility functions for validation operations."""
    
    @staticmethod
    def validate_json_input(json_str: str, max_size: int = 10000) -> ValidationResult:
        """
        Validate and parse JSON input.
        
        Args:
            json_str: JSON string to validate
            max_size: Maximum size in characters
            
        Returns:
            ValidationResult with parsed JSON
        """
        result = ValidationResult()
        
        if not isinstance(json_str, str):
            result.add_error("Input must be a string", "json", "INVALID_TYPE")
            return result
        
        if len(json_str) > max_size:
            result.add_error(f"JSON input exceeds maximum size of {max_size} characters", "json", "TOO_LARGE")
            return result
        
        try:
            parsed_json = json.loads(json_str)
            result.cleaned_value = parsed_json
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON format: {str(e)}", "json", "INVALID_JSON")
        
        return result
    
    @staticmethod
    def validate_datetime_string(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> ValidationResult:
        """
        Validate datetime string format.
        
        Args:
            date_str: Date string to validate
            format_str: Expected datetime format
            
        Returns:
            ValidationResult with parsed datetime
        """
        result = ValidationResult()
        
        if not isinstance(date_str, str):
            result.add_error("Date must be a string", "datetime", "INVALID_TYPE")
            return result
        
        try:
            parsed_date = datetime.strptime(date_str.strip(), format_str)
            result.cleaned_value = parsed_date
        except ValueError as e:
            result.add_error(f"Invalid date format: {str(e)}", "datetime", "INVALID_FORMAT")
        
        return result
    
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult()
        
        if not isinstance(email, str):
            result.add_error("Email must be a string", "email", "INVALID_TYPE")
            return result
        
        email = email.strip().lower()
        
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            result.add_error("Invalid email address format", "email", "INVALID_FORMAT")
            return result
        
        if len(email) > 254:  # RFC 5321 limit
            result.add_error("Email address too long", "email", "TOO_LONG")
            return result
        
        result.cleaned_value = email
        return result
    
    @staticmethod
    def create_validation_summary(results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Create a summary of multiple validation results.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            Dictionary with validation summary
        """
        summary = {
            'overall_valid': all(result.is_valid for result in results),
            'total_errors': sum(len(result.errors) for result in results),
            'total_warnings': sum(len(result.warnings) for result in results),
            'error_messages': [],
            'warning_messages': [],
            'field_errors': {}
        }
        
        for result in results:
            summary['error_messages'].extend(result.get_error_messages())
            summary['warning_messages'].extend(result.warnings)
            
            for error in result.errors:
                if error.field:
                    if error.field not in summary['field_errors']:
                        summary['field_errors'][error.field] = []
                    summary['field_errors'][error.field].append(error.message)
        
        return summary


# Convenience functions for common validations
def validate_trade_input(symbol: str, quantity: Union[int, str, float], 
                        price: Union[Decimal, str, float], trade_type: str,
                        **kwargs) -> ValidationResult:
    """
    Convenience function for validating complete trade input.
    
    Args:
        symbol: Stock symbol
        quantity: Trade quantity
        price: Trade price
        trade_type: Type of trade
        **kwargs: Additional validation parameters
        
    Returns:
        ValidationResult with comprehensive validation
    """
    return TradeParameterValidator.validate_complete_trade(
        symbol, quantity, price, trade_type, **kwargs
    )


def validate_symbol(symbol: str, **kwargs) -> ValidationResult:
    """
    Convenience function for validating stock symbols.
    
    Args:
        symbol: Stock symbol to validate
        **kwargs: Additional validation parameters
        
    Returns:
        ValidationResult with validation outcome
    """
    return SymbolValidator.validate_symbol(symbol, **kwargs)


def sanitize_user_input(value: str, field_type: str = 'general') -> ValidationResult:
    """
    Convenience function for sanitizing user input.
    
    Args:
        value: Input value to sanitize
        field_type: Type of field for specific validation
        
    Returns:
        ValidationResult with sanitized value
    """
    return SecurityValidator.sanitize_input(value, field_type)


def validate_channel_id(channel_id: str) -> ValidationResult:
    """
    Validate Slack channel ID format.
    
    Args:
        channel_id: Channel ID to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult()
    
    if not channel_id:
        result.add_error("Channel ID cannot be empty")
        result.is_valid = False
        return result
    
    # Slack channel IDs start with C and are followed by alphanumeric characters
    if not re.match(r'^C[A-Z0-9]{8,}$', channel_id.upper()):
        result.add_error("Invalid channel ID format")
        result.is_valid = False
        return result
    
    result.cleaned_value = channel_id.upper()
    return result


def validate_user_id(user_id: str) -> ValidationResult:
    """
    Validate Slack user ID format.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult()
    
    if not user_id:
        result.add_error("User ID cannot be empty")
        result.is_valid = False
        return result
    
    # Slack user IDs start with U and are followed by alphanumeric characters
    if not re.match(r'^U[A-Z0-9]{8,}$', user_id.upper()):
        result.add_error("Invalid user ID format")
        result.is_valid = False
        return result
    
    result.cleaned_value = user_id.upper()
    return result


def validate_pii_data(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate and identify PII data in a dictionary.
    
    Args:
        data: Dictionary containing potential PII data
        
    Returns:
        ValidationResult with PII validation status
    """
    result = ValidationResult()
    pii_fields = identify_pii_fields(data)
    
    result.metadata['pii_fields'] = pii_fields
    result.metadata['contains_pii'] = len(pii_fields) > 0
    result.cleaned_value = data
    
    if pii_fields:
        result.add_warning(f"PII detected in fields: {', '.join(pii_fields)}")
    
    return result


def identify_pii_fields(data: Dict[str, Any]) -> List[str]:
    """
    Identify fields that contain PII data.
    
    Args:
        data: Dictionary to analyze for PII
        
    Returns:
        List of field names containing PII
    """
    pii_patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'[\+]?[1-9]?[0-9]{7,15}',
        'ssn': r'\d{3}-?\d{2}-?\d{4}',
        'credit_card': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        'ip_address': r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    }
    
    pii_field_names = [
        'email', 'phone', 'phone_number', 'ssn', 'social_security',
        'credit_card', 'card_number', 'address', 'user_address',
        'ip_address', 'device_id', 'passport', 'drivers_license'
    ]
    
    pii_fields = []
    
    for field_name, field_value in data.items():
        if not isinstance(field_value, str):
            continue
            
        # Check field name patterns
        if any(pii_name in field_name.lower() for pii_name in pii_field_names):
            pii_fields.append(field_name)
            continue
            
        # Check field value patterns
        for pii_type, pattern in pii_patterns.items():
            if re.search(pattern, field_value):
                pii_fields.append(field_name)
                break
    
    return pii_fields


def encrypt_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive fields in a dictionary.
    
    Args:
        data: Dictionary containing sensitive data
        
    Returns:
        Dictionary with sensitive fields encrypted
    """
    import base64
    import hashlib
    
    encrypted_data = data.copy()
    pii_fields = identify_pii_fields(data)
    
    for field in pii_fields:
        if field in encrypted_data and isinstance(encrypted_data[field], str):
            # Simple encryption simulation (in production, use proper encryption)
            value = encrypted_data[field]
            encrypted_value = base64.b64encode(
                hashlib.sha256(value.encode()).digest()
            ).decode()[:16] + "..."
            encrypted_data[field] = encrypted_value
    
    return encrypted_data
    return result


def validate_quantity(quantity: Union[int, str, float]) -> ValidationResult:
    """
    Validate trade quantity.
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult()
    
    try:
        qty = int(quantity)
        if qty <= 0:
            result.add_error("Quantity must be positive")
            result.is_valid = False
        elif qty > 1000000:  # Reasonable upper limit
            result.add_error("Quantity too large")
            result.is_valid = False
        else:
            result.cleaned_value = qty
    except (ValueError, TypeError):
        result.add_error("Invalid quantity format")
        result.is_valid = False
    
    return result


def validate_price(price: Union[Decimal, str, float]) -> ValidationResult:
    """
    Validate trade price.
    
    Args:
        price: Price to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult()
    
    try:
        p = float(price)
        if p <= 0:
            result.add_error("Price must be positive")
            result.is_valid = False
        elif p > 1000000:  # Reasonable upper limit
            result.add_error("Price too high")
            result.is_valid = False
        else:
            result.cleaned_value = Decimal(str(p))
    except (ValueError, TypeError):
        result.add_error("Invalid price format")
        result.is_valid = False
    
    return result