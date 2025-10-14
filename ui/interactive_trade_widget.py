"""
Advanced Interactive Trade Widget for Jain Global Slack Trading Bot.

This module provides sophisticated interactive trading modals with real-time calculations,
multiple order types, dynamic field updates, and enhanced user experience features.
"""

import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json

from models.trade import TradeType
from models.user import User
from services.market_data import MarketQuote
from utils.formatters import format_money

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class InteractiveTradeContext:
    """Context for interactive trade modal."""
    user: User
    channel_id: str
    trigger_id: str
    
    # Trade parameters
    symbol: str = "AAPL"
    trade_side: str = "buy"  # buy or sell
    shares: Optional[int] = None
    gmv: Optional[Decimal] = None  # Gross Market Value
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[Decimal] = None
    
    # Market data
    current_price: Optional[Decimal] = None
    market_quote: Optional[MarketQuote] = None
    
    # UI state
    price_loading: bool = False
    calculation_error: Optional[str] = None


class InteractiveTradeWidget:
    """
    Advanced interactive trade widget with real-time calculations and dynamic updates.
    
    Features:
    - Real-time GMV ↔ Shares calculations
    - Multiple order types (Market, Limit, Stop, Stop Limit)
    - Dynamic field updates as user types
    - Conditional field display based on order type
    - Enhanced user experience with live price updates
    """
    
    def __init__(self):
        """Initialize interactive trade widget."""
        self.logger = logging.getLogger(__name__)
        
        # Default values
        self.default_price = Decimal("150.00")  # Fallback price
        
        self.logger.info("InteractiveTradeWidget initialized")
    
    def create_interactive_modal(self, context: InteractiveTradeContext) -> Dict[str, Any]:
        """
        Create advanced interactive trade modal.
        
        Args:
            context: Interactive trade context
            
        Returns:
            Slack Block Kit modal JSON
        """
        try:
            # Use current price or fallback
            display_price = context.current_price or self.default_price
            
            modal = {
                "type": "modal",
                "callback_id": "stock_trade_modal_interactive",
                "title": {
                    "type": "plain_text",
                    "text": "Place Interactive Trade"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Execute Trade"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "blocks": self._build_interactive_blocks(context, display_price),
                "private_metadata": json.dumps({
                    "user_id": context.user.user_id,
                    "channel_id": context.channel_id,
                    "symbol": context.symbol,
                    "current_price": float(display_price),
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            self.logger.info(
                f"Interactive modal created | User: {context.user.user_id} | "
                f"Symbol: {context.symbol} | Price: ${display_price}"
            )
            
            return modal
            
        except Exception as e:
            self.logger.error(f"Failed to create interactive modal: {e}")
            return self._create_error_modal(str(e))
    
    def _build_interactive_blocks(self, context: InteractiveTradeContext, current_price: Decimal) -> List[Dict[str, Any]]:
        """Build interactive modal blocks."""
        blocks = []
        
        # Symbol input
        blocks.append({
            "type": "input",
            "block_id": "trade_symbol_block",
            "label": {
                "type": "plain_text",
                "text": "Stock Symbol (e.g., AAPL)"
            },
            "element": {
                "type": "plain_text_input",
                "action_id": "symbol_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter the stock ticker"
                },
                "initial_value": context.symbol
            }
        })
        
        # Current price display
        price_text = f"*Current Stock Price:* *${current_price}*"
        if context.price_loading:
            price_text = "*Current Stock Price:* Loading..."
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": price_text
            },
            "block_id": "current_price_display"
        })
        
        blocks.append({"type": "divider"})
        
        # Trade side (Buy/Sell)
        blocks.append({
            "type": "input",
            "block_id": "trade_side_block",
            "label": {
                "type": "plain_text",
                "text": "Trade Action (Buy/Sell)"
            },
            "element": {
                "type": "radio_buttons",
                "action_id": "trade_side_radio",
                "options": [
                    {
                        "value": "buy",
                        "text": {
                            "type": "plain_text",
                            "text": "Buy"
                        }
                    },
                    {
                        "value": "sell",
                        "text": {
                            "type": "plain_text",
                            "text": "Sell"
                        }
                    }
                ],
                "initial_option": {
                    "value": context.trade_side,
                    "text": {
                        "type": "plain_text",
                        "text": context.trade_side.title()
                    }
                }
            }
        })
        
        # Shares input with dynamic calculation
        shares_element = {
            "type": "number_input",
            "action_id": "shares_input",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter shares, and GMV will update"
            },
            "is_decimal_allowed": False,
            "dispatch_action_config": {
                "trigger_actions_on": ["on_enter_pressed", "on_character_entered"]
            }
        }
        
        if context.shares:
            shares_element["initial_value"] = str(context.shares)
        
        blocks.append({
            "type": "input",
            "block_id": "qty_shares_block",
            "label": {
                "type": "plain_text",
                "text": "Quantity (shares)"
            },
            "element": shares_element,
            "hint": {
                "type": "plain_text",
                "text": "Changes here trigger an automatic GMV calculation."
            }
        })
        
        # GMV input with dynamic calculation
        gmv_element = {
            "type": "number_input",
            "action_id": "gmv_input",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter dollar amount, and shares will update"
            },
            "is_decimal_allowed": True,
            "dispatch_action_config": {
                "trigger_actions_on": ["on_enter_pressed", "on_character_entered"]
            }
        }
        
        if context.gmv:
            gmv_element["initial_value"] = str(float(context.gmv))
        
        blocks.append({
            "type": "input",
            "block_id": "gmv_block",
            "label": {
                "type": "plain_text",
                "text": "Gross Market Value (GMV)"
            },
            "element": gmv_element,
            "hint": {
                "type": "plain_text",
                "text": "Changes here trigger an automatic Shares calculation."
            }
        })
        
        blocks.append({"type": "divider"})
        
        # Order type selection
        blocks.append({
            "type": "input",
            "block_id": "order_type_block",
            "label": {
                "type": "plain_text",
                "text": "Order Type"
            },
            "element": {
                "type": "static_select",
                "action_id": "order_type_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an order type"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Market"
                        },
                        "value": "market"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Limit"
                        },
                        "value": "limit"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Stop"
                        },
                        "value": "stop"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Stop Limit"
                        },
                        "value": "stop_limit"
                    }
                ],
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": context.order_type.value.replace("_", " ").title()
                    },
                    "value": context.order_type.value
                }
            }
        })
        
        # Limit price input (conditional)
        limit_price_element = {
            "type": "number_input",
            "action_id": "limit_price_input",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter your maximum/minimum price"
            },
            "is_decimal_allowed": True
        }
        
        if context.limit_price:
            limit_price_element["initial_value"] = str(float(context.limit_price))
        
        blocks.append({
            "type": "input",
            "block_id": "limit_price_block",
            "optional": True,
            "label": {
                "type": "plain_text",
                "text": "Limit Price (Quantity/Price for Limit Orders)"
            },
            "element": limit_price_element,
            "hint": {
                "type": "plain_text",
                "text": "Only required for Limit or Stop Limit order types."
            }
        })
        
        # Calculation error display
        if context.calculation_error:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Calculation Error:* {context.calculation_error}"
                }
            })
        
        return blocks
    
    def calculate_gmv_from_shares(self, shares: int, price: Decimal) -> Decimal:
        """
        Calculate Gross Market Value from shares and price.
        
        Args:
            shares: Number of shares
            price: Price per share
            
        Returns:
            Calculated GMV
        """
        try:
            if shares <= 0 or price <= 0:
                raise ValueError("Shares and price must be positive")
            
            gmv = Decimal(str(shares)) * price
            return gmv.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            self.logger.error(f"GMV calculation error: {e}")
            raise ValueError(f"Invalid calculation: {e}")
    
    def calculate_shares_from_gmv(self, gmv: Decimal, price: Decimal) -> int:
        """
        Calculate shares from GMV and price.
        
        Args:
            gmv: Gross Market Value
            price: Price per share
            
        Returns:
            Calculated number of shares
        """
        try:
            if gmv <= 0 or price <= 0:
                raise ValueError("GMV and price must be positive")
            
            shares = gmv / price
            return int(shares.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            
        except Exception as e:
            self.logger.error(f"Shares calculation error: {e}")
            raise ValueError(f"Invalid calculation: {e}")
    
    def update_modal_with_calculation(
        self, 
        context: InteractiveTradeContext,
        field_updated: str,
        new_value: Union[int, Decimal]
    ) -> Dict[str, Any]:
        """
        Update modal with new calculations based on field changes.
        
        Args:
            context: Current context
            field_updated: Which field was updated ('shares' or 'gmv')
            new_value: New value for the field
            
        Returns:
            Updated modal JSON
        """
        try:
            current_price = context.current_price or self.default_price
            context.calculation_error = None
            
            if field_updated == "shares" and isinstance(new_value, int):
                # Calculate GMV from shares
                context.shares = new_value
                if new_value > 0:
                    context.gmv = self.calculate_gmv_from_shares(new_value, current_price)
                else:
                    context.gmv = None
                    
            elif field_updated == "gmv" and isinstance(new_value, Decimal):
                # Calculate shares from GMV
                context.gmv = new_value
                if new_value > 0:
                    context.shares = self.calculate_shares_from_gmv(new_value, current_price)
                else:
                    context.shares = None
            
            return self.create_interactive_modal(context)
            
        except ValueError as e:
            context.calculation_error = str(e)
            return self.create_interactive_modal(context)
        except Exception as e:
            self.logger.error(f"Modal update error: {e}")
            context.calculation_error = f"Update failed: {e}"
            return self.create_interactive_modal(context)
    
    def update_modal_with_price(
        self, 
        context: InteractiveTradeContext, 
        market_quote: MarketQuote
    ) -> Dict[str, Any]:
        """
        Update modal with new market price.
        
        Args:
            context: Current context
            market_quote: New market data
            
        Returns:
            Updated modal JSON
        """
        try:
            context.market_quote = market_quote
            context.current_price = market_quote.current_price
            context.price_loading = False
            
            # Recalculate GMV if shares are set
            if context.shares and context.shares > 0:
                context.gmv = self.calculate_gmv_from_shares(
                    context.shares, 
                    market_quote.current_price
                )
            
            return self.create_interactive_modal(context)
            
        except Exception as e:
            self.logger.error(f"Price update error: {e}")
            context.calculation_error = f"Price update failed: {e}"
            return self.create_interactive_modal(context)
    
    def validate_trade_data(self, context: InteractiveTradeContext) -> Dict[str, str]:
        """
        Validate trade data before submission.
        
        Args:
            context: Trade context to validate
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        try:
            # Validate symbol
            if not context.symbol or len(context.symbol.strip()) == 0:
                errors["symbol"] = "Stock symbol is required"
            elif len(context.symbol.strip()) > 10:
                errors["symbol"] = "Stock symbol too long"
            
            # Validate shares
            if not context.shares or context.shares <= 0:
                errors["shares"] = "Shares must be a positive number"
            elif context.shares > 1000000:
                errors["shares"] = "Shares amount too large"
            
            # Validate GMV
            if not context.gmv or context.gmv <= 0:
                errors["gmv"] = "GMV must be a positive amount"
            elif context.gmv > Decimal("10000000"):  # $10M limit
                errors["gmv"] = "GMV amount too large"
            
            # Validate order type specific fields
            if context.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                if not context.limit_price or context.limit_price <= 0:
                    errors["limit_price"] = "Limit price required for limit orders"
            
            # Validate price consistency
            if context.current_price and context.shares and context.gmv:
                expected_gmv = self.calculate_gmv_from_shares(context.shares, context.current_price)
                if abs(context.gmv - expected_gmv) > Decimal("0.01"):
                    errors["calculation"] = "Shares and GMV values are inconsistent"
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            errors["general"] = f"Validation failed: {e}"
        
        return errors
    
    def _create_error_modal(self, error_message: str) -> Dict[str, Any]:
        """Create error modal for display."""
        return {
            "type": "modal",
            "callback_id": "trade_error_modal",
            "title": {
                "type": "plain_text",
                "text": "Trade Error"
            },
            "close": {
                "type": "plain_text",
                "text": "Close"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Error:* {error_message}"
                    }
                }
            ]
        }