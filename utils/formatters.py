"""
Comprehensive formatting utilities for the Slack Trading Bot.

This module provides extensive formatting functions for currency, dates, times,
Slack messages, and other display formats with internationalization support
and extensive customization options.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
import json
import re
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class CurrencyFormat(Enum):
    """Currency formatting styles."""
    STANDARD = "standard"  # $1,234.56
    COMPACT = "compact"    # $1.2K
    ACCOUNTING = "accounting"  # ($1,234.56) for negative
    MINIMAL = "minimal"    # 1234.56


class DateFormat(Enum):
    """Date formatting styles."""
    SHORT = "short"        # 12/31/23
    MEDIUM = "medium"      # Dec 31, 2023
    LONG = "long"          # December 31, 2023
    ISO = "iso"            # 2023-12-31
    RELATIVE = "relative"  # 2 days ago
    SLACK = "slack"        # <!date^1234567890^{date_short}|Dec 31, 2023>


class MessageFormat(Enum):
    """Slack message formatting styles."""
    PLAIN = "plain"
    RICH = "rich"
    BLOCKS = "blocks"
    MODAL = "modal"


class FormattingError(Exception):
    """Custom exception for formatting errors."""
    
    def __init__(self, message: str, value: Any = None):
        self.message = message
        self.value = value
        super().__init__(self.message)


class CurrencyFormatter:
    """Comprehensive currency formatting utilities."""
    
    # Currency symbols and configurations
    CURRENCY_CONFIGS = {
        'USD': {'symbol': '$', 'decimal_places': 2, 'position': 'before'},
        'EUR': {'symbol': '€', 'decimal_places': 2, 'position': 'after'},
        'GBP': {'symbol': '£', 'decimal_places': 2, 'position': 'before'},
        'JPY': {'symbol': '¥', 'decimal_places': 0, 'position': 'before'},
        'CAD': {'symbol': 'C$', 'decimal_places': 2, 'position': 'before'},
        'AUD': {'symbol': 'A$', 'decimal_places': 2, 'position': 'before'},
    }
    
    # Compact formatting thresholds
    COMPACT_THRESHOLDS = [
        (1_000_000_000_000, 'T'),  # Trillion
        (1_000_000_000, 'B'),      # Billion
        (1_000_000, 'M'),          # Million
        (1_000, 'K'),              # Thousand
    ]
    
    @classmethod
    def format_currency(cls, amount: Union[Decimal, float, int], 
                       currency: str = 'USD',
                       format_style: CurrencyFormat = CurrencyFormat.STANDARD,
                       show_cents: Optional[bool] = None,
                       color_negative: bool = False) -> str:
        """
        Format currency amount with various styling options.
        
        Args:
            amount: Amount to format
            currency: Currency code (USD, EUR, etc.)
            format_style: Formatting style
            show_cents: Whether to show decimal places (auto-detect if None)
            color_negative: Whether to color negative amounts red
            
        Returns:
            Formatted currency string
            
        Raises:
            FormattingError: If formatting fails
        """
        try:
            # Convert to Decimal for precise calculations
            if isinstance(amount, (int, float)):
                decimal_amount = Decimal(str(amount))
            elif isinstance(amount, Decimal):
                decimal_amount = amount
            else:
                raise FormattingError(f"Invalid amount type: {type(amount)}", amount)
            
            # Get currency configuration
            config = cls.CURRENCY_CONFIGS.get(currency.upper(), cls.CURRENCY_CONFIGS['USD'])
            symbol = config['symbol']
            default_decimals = config['decimal_places']
            symbol_position = config['position']
            
            # Determine decimal places
            if show_cents is None:
                # Auto-detect: show cents if amount has fractional part or is small
                show_decimals = (decimal_amount % 1 != 0) or (abs(decimal_amount) < 1000)
            else:
                show_decimals = show_cents
            
            decimal_places = default_decimals if show_decimals else 0
            
            # Handle different formatting styles
            if format_style == CurrencyFormat.COMPACT:
                return cls._format_compact_currency(decimal_amount, symbol, symbol_position)
            elif format_style == CurrencyFormat.ACCOUNTING:
                return cls._format_accounting_currency(decimal_amount, symbol, symbol_position, decimal_places)
            elif format_style == CurrencyFormat.MINIMAL:
                return cls._format_minimal_currency(decimal_amount, decimal_places)
            else:  # STANDARD
                return cls._format_standard_currency(decimal_amount, symbol, symbol_position, 
                                                   decimal_places, color_negative)
        
        except Exception as e:
            logger.error(f"Currency formatting error: {str(e)}")
            raise FormattingError(f"Failed to format currency: {str(e)}", amount)
    
    @classmethod
    def _format_standard_currency(cls, amount: Decimal, symbol: str, position: str,
                                 decimal_places: int, color_negative: bool) -> str:
        """Format currency in standard style."""
        is_negative = amount < 0
        abs_amount = abs(amount)
        
        # Format with commas and decimal places
        if decimal_places > 0:
            formatted_number = f"{abs_amount:,.{decimal_places}f}"
        else:
            formatted_number = f"{abs_amount:,.0f}"
        
        # Add currency symbol
        if position == 'before':
            formatted = f"{symbol}{formatted_number}"
        else:
            formatted = f"{formatted_number}{symbol}"
        
        # Handle negative values
        if is_negative:
            if color_negative:
                formatted = f":red_circle: -{formatted}"
            else:
                formatted = f"-{formatted}"
        elif color_negative and amount > 0:
            formatted = f":green_circle: {formatted}"
        
        return formatted
    
    @classmethod
    def _format_compact_currency(cls, amount: Decimal, symbol: str, position: str) -> str:
        """Format currency in compact style (e.g., $1.2M)."""
        abs_amount = abs(amount)
        is_negative = amount < 0
        
        # Find appropriate threshold
        for threshold, suffix in cls.COMPACT_THRESHOLDS:
            if abs_amount >= threshold:
                compact_value = abs_amount / Decimal(str(threshold))
                
                # Format with 1 decimal place if needed
                if compact_value % 1 == 0:
                    formatted_number = f"{compact_value:.0f}{suffix}"
                else:
                    formatted_number = f"{compact_value:.1f}{suffix}"
                
                break
        else:
            # Less than 1K, use standard formatting
            formatted_number = f"{abs_amount:,.0f}"
        
        # Add currency symbol and negative sign
        if position == 'before':
            result = f"{symbol}{formatted_number}"
        else:
            result = f"{formatted_number}{symbol}"
        
        if is_negative:
            result = f"-{result}"
        
        return result
    
    @classmethod
    def _format_accounting_currency(cls, amount: Decimal, symbol: str, position: str,
                                   decimal_places: int) -> str:
        """Format currency in accounting style (parentheses for negative)."""
        is_negative = amount < 0
        abs_amount = abs(amount)
        
        # Format number
        if decimal_places > 0:
            formatted_number = f"{abs_amount:,.{decimal_places}f}"
        else:
            formatted_number = f"{abs_amount:,.0f}"
        
        # Add currency symbol
        if position == 'before':
            formatted = f"{symbol}{formatted_number}"
        else:
            formatted = f"{formatted_number}{symbol}"
        
        # Use parentheses for negative values
        if is_negative:
            formatted = f"({formatted})"
        
        return formatted
    
    @classmethod
    def _format_minimal_currency(cls, amount: Decimal, decimal_places: int) -> str:
        """Format currency without symbol or commas."""
        if decimal_places > 0:
            return f"{amount:.{decimal_places}f}"
        else:
            return f"{amount:.0f}"
    
    @classmethod
    def format_percentage(cls, value: Union[Decimal, float], decimal_places: int = 2,
                         show_sign: bool = True, color_code: bool = False) -> str:
        """
        Format percentage values.
        
        Args:
            value: Percentage value (e.g., 0.15 for 15%)
            decimal_places: Number of decimal places
            show_sign: Whether to show + for positive values
            color_code: Whether to add color indicators
            
        Returns:
            Formatted percentage string
        """
        try:
            if isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            elif isinstance(value, Decimal):
                decimal_value = value
            else:
                raise FormattingError(f"Invalid percentage type: {type(value)}", value)
            
            # Convert to percentage (multiply by 100)
            percentage = decimal_value * Decimal('100')
            
            # Format with specified decimal places
            formatted = f"{percentage:.{decimal_places}f}%"
            
            # Add sign for positive values
            if show_sign and percentage > 0:
                formatted = f"+{formatted}"
            
            # Add color coding
            if color_code:
                if percentage > 0:
                    formatted = f":green_circle: {formatted}"
                elif percentage < 0:
                    formatted = f":red_circle: {formatted}"
                else:
                    formatted = f":white_circle: {formatted}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Percentage formatting error: {str(e)}")
            raise FormattingError(f"Failed to format percentage: {str(e)}", value)
    
    @classmethod
    def format_change(cls, current: Union[Decimal, float], previous: Union[Decimal, float],
                     format_style: str = 'both') -> str:
        """
        Format change between two values.
        
        Args:
            current: Current value
            previous: Previous value
            format_style: 'absolute', 'percentage', or 'both'
            
        Returns:
            Formatted change string
        """
        try:
            current_decimal = Decimal(str(current))
            previous_decimal = Decimal(str(previous))
            
            if previous_decimal == 0:
                return "N/A"
            
            absolute_change = current_decimal - previous_decimal
            percentage_change = (absolute_change / previous_decimal) * Decimal('100')
            
            if format_style == 'absolute':
                return cls.format_currency(absolute_change, show_cents=True, color_negative=True)
            elif format_style == 'percentage':
                return cls.format_percentage(percentage_change / Decimal('100'), 
                                           show_sign=True, color_code=True)
            else:  # both
                abs_formatted = cls.format_currency(absolute_change, show_cents=True)
                pct_formatted = cls.format_percentage(percentage_change / Decimal('100'), 
                                                    show_sign=True, color_code=True)
                return f"{abs_formatted} ({pct_formatted})"
                
        except Exception as e:
            logger.error(f"Change formatting error: {str(e)}")
            return "N/A"


class DateTimeFormatter:
    """Comprehensive date and time formatting utilities."""
    
    # Timezone mappings
    TIMEZONE_MAPPINGS = {
        'EST': 'America/New_York',
        'PST': 'America/Los_Angeles',
        'GMT': 'Europe/London',
        'UTC': 'UTC'
    }
    
    @classmethod
    def format_datetime(cls, dt: datetime, format_style: DateFormat = DateFormat.MEDIUM,
                       timezone_name: Optional[str] = None,
                       relative_threshold: timedelta = timedelta(days=7)) -> str:
        """
        Format datetime with various styling options.
        
        Args:
            dt: Datetime to format
            format_style: Formatting style
            timezone_name: Target timezone for display
            relative_threshold: Threshold for relative formatting
            
        Returns:
            Formatted datetime string
        """
        try:
            # Ensure datetime is timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Convert to target timezone if specified
            if timezone_name:
                # This is simplified - in production, use pytz or zoneinfo
                pass  # Would implement timezone conversion here
            
            now = datetime.now(timezone.utc)
            
            if format_style == DateFormat.RELATIVE:
                return cls._format_relative_datetime(dt, now, relative_threshold)
            elif format_style == DateFormat.SLACK:
                return cls._format_slack_datetime(dt)
            elif format_style == DateFormat.ISO:
                return dt.isoformat()
            elif format_style == DateFormat.SHORT:
                return dt.strftime("%m/%d/%y")
            elif format_style == DateFormat.LONG:
                return dt.strftime("%B %d, %Y at %I:%M %p")
            else:  # MEDIUM
                return dt.strftime("%b %d, %Y %I:%M %p")
                
        except Exception as e:
            logger.error(f"DateTime formatting error: {str(e)}")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    @classmethod
    def _format_relative_datetime(cls, dt: datetime, now: datetime, 
                                 threshold: timedelta) -> str:
        """Format datetime relative to current time."""
        diff = now - dt
        
        if diff < timedelta(0):
            # Future date
            future_diff = dt - now
            if future_diff < timedelta(minutes=1):
                return "in a few seconds"
            elif future_diff < timedelta(hours=1):
                minutes = int(future_diff.total_seconds() / 60)
                return f"in {minutes} minute{'s' if minutes != 1 else ''}"
            elif future_diff < timedelta(days=1):
                hours = int(future_diff.total_seconds() / 3600)
                return f"in {hours} hour{'s' if hours != 1 else ''}"
            else:
                days = future_diff.days
                return f"in {days} day{'s' if days != 1 else ''}"
        
        # Past date
        if diff > threshold:
            return dt.strftime("%b %d, %Y")
        
        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    @classmethod
    def _format_slack_datetime(cls, dt: datetime) -> str:
        """Format datetime for Slack using timestamp formatting."""
        timestamp = int(dt.timestamp())
        return f"<!date^{timestamp}^{{date_short}} at {{time}}|{dt.strftime('%b %d, %Y at %I:%M %p')}>"
    
    @classmethod
    def format_duration(cls, seconds: Union[int, float]) -> str:
        """
        Format duration in human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        try:
            total_seconds = int(seconds)
            
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                remaining_seconds = total_seconds % 60
                if remaining_seconds == 0:
                    return f"{minutes}m"
                else:
                    return f"{minutes}m {remaining_seconds}s"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                remaining_minutes = (total_seconds % 3600) // 60
                if remaining_minutes == 0:
                    return f"{hours}h"
                else:
                    return f"{hours}h {remaining_minutes}m"
            else:
                days = total_seconds // 86400
                remaining_hours = (total_seconds % 86400) // 3600
                if remaining_hours == 0:
                    return f"{days}d"
                else:
                    return f"{days}d {remaining_hours}h"
                    
        except Exception as e:
            logger.error(f"Duration formatting error: {str(e)}")
            return f"{seconds}s"


class SlackMessageFormatter:
    """Comprehensive Slack message formatting utilities."""
    
    # Slack formatting characters
    SLACK_FORMATS = {
        'bold': '*',
        'italic': '_',
        'strikethrough': '~',
        'code': '`',
        'code_block': '```'
    }
    
    # Emoji mappings for common indicators
    STATUS_EMOJIS = {
        'success': ':white_check_mark:',
        'error': ':x:',
        'warning': ':warning:',
        'info': ':information_source:',
        'pending': ':hourglass_flowing_sand:',
        'money': ':moneybag:',
        'chart_up': ':chart_with_upwards_trend:',
        'chart_down': ':chart_with_downwards_trend:'
    }
    
    @classmethod
    def format_trade_summary(cls, trade_data: Dict[str, Any], 
                           format_style: MessageFormat = MessageFormat.RICH) -> str:
        """
        Format trade information for Slack display.
        
        Args:
            trade_data: Dictionary containing trade information
            format_style: Formatting style for the message
            
        Returns:
            Formatted trade summary string
        """
        try:
            symbol = trade_data.get('symbol', 'N/A')
            quantity = trade_data.get('quantity', 0)
            price = trade_data.get('price', Decimal('0'))
            trade_type = trade_data.get('trade_type', 'unknown')
            status = trade_data.get('status', 'unknown')
            
            # Format basic trade info
            action = "Buy" if trade_type.lower() == 'buy' else "Sell"
            price_formatted = CurrencyFormatter.format_currency(price)
            total_value = CurrencyFormatter.format_currency(Decimal(str(quantity)) * price)
            
            if format_style == MessageFormat.PLAIN:
                return f"{action} {quantity:,} shares of {symbol} at {price_formatted} (Total: {total_value})"
            
            elif format_style == MessageFormat.RICH:
                status_emoji = cls.STATUS_EMOJIS.get(status, ':question:')
                action_emoji = ':arrow_up:' if trade_type.lower() == 'buy' else ':arrow_down:'
                
                message = f"{status_emoji} *{action} Order* {action_emoji}\n"
                message += f"• Symbol: *{symbol}*\n"
                message += f"• Quantity: {quantity:,} shares\n"
                message += f"• Price: {price_formatted}\n"
                message += f"• Total Value: {total_value}\n"
                message += f"• Status: _{status.title()}_"
                
                return message
            
            elif format_style == MessageFormat.BLOCKS:
                return cls._format_trade_blocks(trade_data)
            
            else:  # MODAL
                return cls._format_trade_modal(trade_data)
                
        except Exception as e:
            logger.error(f"Trade summary formatting error: {str(e)}")
            return f"Trade: {trade_data.get('symbol', 'N/A')} - Error formatting details"
    
    @classmethod
    def format_portfolio_summary(cls, portfolio_data: Dict[str, Any],
                                format_style: MessageFormat = MessageFormat.RICH) -> str:
        """
        Format portfolio information for Slack display.
        
        Args:
            portfolio_data: Dictionary containing portfolio information
            format_style: Formatting style for the message
            
        Returns:
            Formatted portfolio summary string
        """
        try:
            total_value = portfolio_data.get('total_value', 0)
            cash_balance = portfolio_data.get('cash_balance', 0)
            total_pnl = portfolio_data.get('total_pnl', 0)
            day_change = portfolio_data.get('day_change', 0)
            position_count = portfolio_data.get('position_count', 0)
            
            # Format values
            value_formatted = CurrencyFormatter.format_currency(total_value)
            cash_formatted = CurrencyFormatter.format_currency(cash_balance)
            pnl_formatted = CurrencyFormatter.format_currency(total_pnl, color_negative=True)
            change_formatted = CurrencyFormatter.format_currency(day_change, color_negative=True)
            
            if format_style == MessageFormat.PLAIN:
                return (f"Portfolio Value: {value_formatted} | "
                       f"Cash: {cash_formatted} | "
                       f"P&L: {pnl_formatted} | "
                       f"Positions: {position_count}")
            
            elif format_style == MessageFormat.RICH:
                pnl_emoji = ':chart_with_upwards_trend:' if total_pnl >= 0 else ':chart_with_downwards_trend:'
                
                message = f":moneybag: *Portfolio Summary*\n"
                message += f"• Total Value: *{value_formatted}*\n"
                message += f"• Cash Balance: {cash_formatted}\n"
                message += f"• Total P&L: {pnl_formatted} {pnl_emoji}\n"
                message += f"• Day Change: {change_formatted}\n"
                message += f"• Active Positions: {position_count}"
                
                return message
            
            else:
                return cls._format_portfolio_blocks(portfolio_data)
                
        except Exception as e:
            logger.error(f"Portfolio summary formatting error: {str(e)}")
            return "Portfolio Summary - Error formatting details"
    
    @classmethod
    def format_risk_analysis(cls, risk_data: Dict[str, Any]) -> str:
        """
        Format risk analysis information for Slack display.
        
        Args:
            risk_data: Dictionary containing risk analysis data
            
        Returns:
            Formatted risk analysis string
        """
        try:
            risk_level = risk_data.get('risk_level', 'unknown')
            risk_score = risk_data.get('risk_score', 0)
            analysis_summary = risk_data.get('analysis_summary', 'No analysis available')
            recommendations = risk_data.get('recommendations', [])
            
            # Choose emoji based on risk level
            risk_emojis = {
                'low': ':green_circle:',
                'medium': ':yellow_circle:',
                'high': ':red_circle:',
                'critical': ':rotating_light:'
            }
            
            risk_emoji = risk_emojis.get(risk_level.lower(), ':question:')
            
            message = f"{risk_emoji} *Risk Analysis* - {risk_level.title()} Risk\n"
            message += f"• Risk Score: {risk_score:.1f}/10\n\n"
            message += f"*Analysis:*\n{analysis_summary}\n"
            
            if recommendations:
                message += f"\n*Recommendations:*\n"
                for i, rec in enumerate(recommendations[:3], 1):  # Limit to 3 recommendations
                    message += f"{i}. {rec}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Risk analysis formatting error: {str(e)}")
            return ":warning: Risk Analysis - Error formatting details"
    
    @classmethod
    def format_error_message(cls, error_message: str, error_code: Optional[str] = None,
                           suggestions: Optional[List[str]] = None) -> str:
        """
        Format error messages for user-friendly display.
        
        Args:
            error_message: Main error message
            error_code: Optional error code
            suggestions: Optional list of suggestions
            
        Returns:
            Formatted error message string
        """
        message = f":x: *Error*\n{error_message}"
        
        if error_code:
            message += f"\n_Error Code: {error_code}_"
        
        if suggestions:
            message += f"\n\n*Suggestions:*\n"
            for suggestion in suggestions[:3]:  # Limit to 3 suggestions
                message += f"• {suggestion}\n"
        
        return message
    
    @classmethod
    def _format_trade_blocks(cls, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format trade data as Slack Block Kit blocks."""
        # This would return Block Kit JSON structure
        # Simplified implementation for demonstration
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": cls.format_trade_summary(trade_data, MessageFormat.RICH)
            }
        }
    
    @classmethod
    def _format_trade_modal(cls, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format trade data for modal display."""
        # This would return modal Block Kit JSON structure
        # Simplified implementation for demonstration
        return {
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Trade Details"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": cls.format_trade_summary(trade_data, MessageFormat.RICH)
                    }
                }
            ]
        }
    
    @classmethod
    def _format_portfolio_blocks(cls, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format portfolio data as Slack Block Kit blocks."""
        # This would return Block Kit JSON structure
        # Simplified implementation for demonstration
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": cls.format_portfolio_summary(portfolio_data, MessageFormat.RICH)
            }
        }
    
    @classmethod
    def escape_slack_text(cls, text: str) -> str:
        """
        Escape special characters for Slack text formatting.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for Slack
        """
        # Escape Slack special characters
        escape_chars = ['&', '<', '>']
        escaped_text = text
        
        for char in escape_chars:
            if char == '&':
                escaped_text = escaped_text.replace(char, '&amp;')
            elif char == '<':
                escaped_text = escaped_text.replace(char, '&lt;')
            elif char == '>':
                escaped_text = escaped_text.replace(char, '&gt;')
        
        return escaped_text
    
    @classmethod
    def create_progress_bar(cls, current: int, total: int, width: int = 10) -> str:
        """
        Create a text-based progress bar.
        
        Args:
            current: Current progress value
            total: Total/maximum value
            width: Width of progress bar in characters
            
        Returns:
            Text progress bar string
        """
        if total <= 0:
            return "█" * width
        
        progress = min(current / total, 1.0)
        filled = int(progress * width)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        percentage = f"{progress:.0%}"
        
        return f"{bar} {percentage}"


# Convenience functions for common formatting operations
def format_money(amount: Union[Decimal, float, int], **kwargs) -> str:
    """Convenience function for formatting currency."""
    return CurrencyFormatter.format_currency(amount, **kwargs)


def format_percent(value: Union[Decimal, float], **kwargs) -> str:
    """Convenience function for formatting percentages."""
    return CurrencyFormatter.format_percentage(value, **kwargs)


def format_date(dt: datetime, **kwargs) -> str:
    """Convenience function for formatting dates."""
    return DateTimeFormatter.format_datetime(dt, **kwargs)


def format_trade_message(trade_data: Dict[str, Any], **kwargs) -> str:
    """Convenience function for formatting trade messages."""
    return SlackMessageFormatter.format_trade_summary(trade_data, **kwargs)


def format_portfolio_message(portfolio_data: Dict[str, Any], **kwargs) -> str:
    """Convenience function for formatting portfolio messages."""
    return SlackMessageFormatter.format_portfolio_summary(portfolio_data, **kwargs)

def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive data for display purposes.
    
    Args:
        data: Dictionary containing sensitive data
        
    Returns:
        Dictionary with sensitive data masked
    """
    from utils.validators import identify_pii_fields
    
    masked_data = data.copy()
    pii_fields = identify_pii_fields(data)
    
    for field in pii_fields:
        if field in masked_data and isinstance(masked_data[field], str):
            masked_data[field] = mask_pii_data({field: masked_data[field]})[field]
    
    return masked_data


def mask_pii_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask PII data for safe display.
    
    Args:
        data: Dictionary containing PII data
        
    Returns:
        Dictionary with PII data masked
    """
    masked_data = {}
    
    for field, value in data.items():
        if not isinstance(value, str):
            masked_data[field] = value
            continue
            
        field_lower = field.lower()
        
        if 'email' in field_lower:
            # Mask email: john.doe@example.com -> j***@example.com
            if '@' in value:
                local, domain = value.split('@', 1)
                if len(local) > 1:
                    masked_local = local[0] + '*' * (len(local) - 1)
                else:
                    masked_local = '*'
                masked_data[field] = f"{masked_local}@{domain}"
            else:
                masked_data[field] = '*' * len(value)
                
        elif 'phone' in field_lower:
            # Mask phone: +1-555-123-4567 -> +1-555-***-4567
            if len(value) >= 4:
                masked_data[field] = value[:-4].replace(value[-8:-4], '***') + value[-4:]
            else:
                masked_data[field] = '*' * len(value)
                
        elif 'ssn' in field_lower or 'social' in field_lower:
            # Mask SSN: 123-45-6789 -> ***-**-6789
            if len(value) >= 4:
                masked_data[field] = 'xxx-xx-' + value[-4:]
            else:
                masked_data[field] = '*' * len(value)
                
        elif 'credit' in field_lower or 'card' in field_lower:
            # Mask credit card: 4532-1234-5678-9012 -> ****-****-****-9012
            if len(value) >= 4:
                masked_data[field] = '*' * (len(value) - 4) + value[-4:]
            else:
                masked_data[field] = '*' * len(value)
                
        elif 'address' in field_lower:
            # Mask address: keep city/state, mask street
            parts = value.split(',')
            if len(parts) > 1:
                masked_parts = ['***'] + parts[1:]
                masked_data[field] = ','.join(masked_parts)
            else:
                masked_data[field] = '***'
                
        else:
            # Generic masking for other PII
            if len(value) > 4:
                masked_data[field] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                masked_data[field] = '*' * len(value)
    
    return masked_data


def sanitize_log_data(log_message: str) -> str:
    """
    Sanitize log data to remove PII.
    
    Args:
        log_message: Log message that may contain PII
        
    Returns:
        Sanitized log message
    """
    # Common PII patterns to remove/mask
    patterns = [
        (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL_REDACTED]'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]'),
        (r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[PHONE_REDACTED]'),
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]')
    ]
    
    sanitized = log_message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)
    
    return sanitized


def format_audit_log(event_type: str, user_id: str, details: Dict[str, Any], 
                    timestamp: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Format audit log entry.
    
    Args:
        event_type: Type of event being logged
        user_id: User ID associated with the event
        details: Event details
        timestamp: Event timestamp
        
    Returns:
        Formatted audit log entry
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Sanitize details to remove PII
    sanitized_details = {}
    for key, value in details.items():
        if isinstance(value, str):
            sanitized_details[key] = sanitize_log_data(value)
        else:
            sanitized_details[key] = value
    
    return {
        'timestamp': timestamp.isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'details': sanitized_details,
        'log_level': 'INFO',
        'source': 'slack_trading_bot'
    }