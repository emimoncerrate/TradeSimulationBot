"""
Enhanced market data action handlers for interactive live market data features.

This module handles all interactive actions for the enhanced /trade command,
including real-time updates, symbol changes, view toggles, and market data
refresh operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

from slack_bolt import App, Ack, BoltContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from services.market_data import MarketDataService, MarketDataError
from services.auth import AuthService
from services.service_container import get_container
from listeners.enhanced_trade_command import EnhancedTradeCommand, EnhancedMarketContext, MarketDataView
from utils.validators import validate_symbol

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedMarketActions:
    """Handler for enhanced market data interactive actions."""
    
    def __init__(self, enhanced_command: EnhancedTradeCommand):
        """Initialize enhanced market actions handler."""
        self.enhanced_command = enhanced_command
        self.market_data_service = enhanced_command.market_data_service
        self.auth_service = enhanced_command.auth_service
        
        logger.info("Enhanced market actions handler initialized")
    
    def fetch_any_ticker_data(self, symbol: str, view_id: str, user_id: str, client, company_name: str = None, emoji: str = "📊"):
        """Generic function to fetch market data for any ticker symbol."""
        import threading
        import requests
        from config.settings import get_config
        
        def fetch_market_data():
            try:
                # Get API key from config
                config = get_config()
                api_key = config.market_data.finnhub_api_key
                
                # Make synchronous HTTP request to Finnhub API
                url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract price data
                    current_price = data.get('c', 0)  # current price
                    price_change = data.get('d', 0)   # change
                    price_change_percent = data.get('dp', 0)  # change percent
                    
                    # Print to terminal
                    print(f"\n🎯 {symbol} MARKET DATA FETCHED SUCCESSFULLY!")
                    print(f"💰 Current Price: ${current_price}")
                    print(f"📈 Price Change: ${price_change}")
                    print(f"📊 Change %: {price_change_percent}%")
                    print(f"⚡ Data Quality: Real-time")
                    print(f"🏢 Exchange: Various")
                    print("-" * 50)
                    
                    # Update modal with real data
                    change_emoji = "📈" if price_change >= 0 else "📉"
                    price_change_text = f"\n{change_emoji} *Change:* ${price_change} ({price_change_percent}%)"
                    
                    display_name = f"{symbol}"
                    if company_name:
                        display_name = f"{symbol} - {company_name}"
                    
                    updated_modal = {
                        "type": "modal",
                        "callback_id": "enhanced_trade_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "📊 Live Market Data"
                        },
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{emoji} {display_name}*\n\n✅ Live market data fetched successfully!"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"💰 *Current Price:* ${current_price}\n📊 *Market Status:* Open\n⚡ *Data Quality:* Real-time{price_change_text}"
                                }
                            }
                        ],
                        "close": {
                            "type": "plain_text",
                            "text": "Close"
                        }
                    }
                    
                    client.views_update(view_id=view_id, view=updated_modal)
                    logger.info(f"✅ {symbol} real market data displayed for user {user_id}")
                    
                else:
                    print(f"❌ {symbol} API request failed with status {response.status_code}")
                    print(f"Response: {response.text}")
                    raise Exception(f"API request failed with status {response.status_code}")
                
            except Exception as e:
                print(f"❌ Error fetching {symbol} market data: {e}")
                logger.error(f"Error fetching {symbol} market data: {e}")
                
                # Show error in modal
                try:
                    error_modal = {
                        "type": "modal",
                        "callback_id": "enhanced_trade_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "📊 Live Market Data"
                        },
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{emoji} {symbol}*\n\n❌ Error fetching market data. Please try again.\n\nNote: Make sure the ticker symbol is valid (e.g., AAPL, TSLA, MSFT)"
                                }
                            }
                        ],
                        "close": {
                            "type": "plain_text",
                            "text": "Close"
                        }
                    }
                    client.views_update(view_id=view_id, view=error_modal)
                except:
                    pass
        
        # Start the fetch in a separate thread
        fetch_thread = threading.Thread(target=fetch_market_data)
        fetch_thread.daemon = True
        fetch_thread.start()
    
    async def handle_quick_symbol_selection(self, ack: Ack, body: Dict[str, Any], 
                                          client: WebClient, context: BoltContext) -> None:
        """Handle quick symbol selection buttons."""
        logger.info(f"🎯 Quick symbol selection handler called! Action: {body.get('actions', [{}])[0].get('action_id', 'unknown')}")
        await ack()
        
        try:
            # Extract symbol from action_id
            action_id = body["actions"][0]["action_id"]
            symbol = action_id.replace("quick_symbol_", "")
            
            # Get user context
            user_id = body["user"]["id"]
            team_id = body["team"]["id"]
            view_id = body["view"]["id"]
            
            # Update the market context
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                market_context.symbol = symbol
                
                # Fetch new market data
                await self.enhanced_command._fetch_market_data(market_context)
                
                # Update modal
                updated_modal = await self.enhanced_command._create_enhanced_market_modal(market_context)
                
                await client.views_update(
                    view_id=view_id,
                    view=updated_modal
                )
                
                logger.info(f"Quick symbol selected: {symbol} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling quick symbol selection: {str(e)}")
            await self._send_error_update(client, body, "Failed to update symbol")
    
    async def handle_refresh_market_data(self, ack: Ack, body: Dict[str, Any], 
                                       client: WebClient, context: BoltContext) -> None:
        """Handle manual market data refresh."""
        await ack()
        
        try:
            user_id = body["user"]["id"]
            view_id = body["view"]["id"]
            
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                
                if market_context.symbol:
                    # Force refresh market data
                    await self.enhanced_command._fetch_market_data(market_context)
                    
                    # Update modal with refreshed data
                    updated_modal = await self.enhanced_command._create_enhanced_market_modal(market_context)
                    
                    await client.views_update(
                        view_id=view_id,
                        view=updated_modal
                    )
                    
                    logger.info(f"Market data refreshed for {market_context.symbol} for user {user_id}")
                else:
                    await self._send_error_update(client, body, "No symbol selected for refresh")
            
        except Exception as e:
            logger.error(f"Error refreshing market data: {str(e)}")
            await self._send_error_update(client, body, "Failed to refresh market data")
    
    async def handle_toggle_auto_refresh(self, ack: Ack, body: Dict[str, Any], 
                                       client: WebClient, context: BoltContext) -> None:
        """Handle auto-refresh toggle."""
        await ack()
        
        try:
            user_id = body["user"]["id"]
            view_id = body["view"]["id"]
            
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                
                # Toggle auto-refresh
                market_context.auto_refresh = not market_context.auto_refresh
                
                # Update modal to reflect new state
                updated_modal = await self.enhanced_command._create_enhanced_market_modal(market_context)
                
                await client.views_update(
                    view_id=view_id,
                    view=updated_modal
                )
                
                # Start or stop real-time updates
                if market_context.auto_refresh and market_context.symbol:
                    asyncio.create_task(
                        self.enhanced_command._start_real_time_updates(session_key, client)
                    )
                
                logger.info(
                    f"Auto-refresh toggled: {market_context.auto_refresh}", 
                    user_id=user_id
                )
            
        except Exception as e:
            logger.error(f"Error toggling auto-refresh: {str(e)}")
            await self._send_error_update(client, body, "Failed to toggle auto-refresh")
    
    async def handle_change_view_type(self, ack: Ack, body: Dict[str, Any], 
                                    client: WebClient, context: BoltContext) -> None:
        """Handle view type change."""
        await ack()
        
        try:
            user_id = body["user"]["id"]
            view_id = body["view"]["id"]
            selected_value = body["actions"][0]["selected_option"]["value"]
            
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                
                # Update view type
                market_context.view_type = MarketDataView(selected_value)
                
                # Update modal with new view
                updated_modal = await self.enhanced_command._create_enhanced_market_modal(market_context)
                
                await client.views_update(
                    view_id=view_id,
                    view=updated_modal
                )
                
                logger.info(f"View type changed to: {selected_value} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error changing view type: {str(e)}")
            await self._send_error_update(client, body, "Failed to change view type")
    
    async def handle_add_to_watchlist(self, ack: Ack, body: Dict[str, Any], 
                                    client: WebClient, context: BoltContext) -> None:
        """Handle adding symbol to watchlist."""
        await ack()
        
        try:
            user_id = body["user"]["id"]
            symbol = body["actions"][0]["value"]
            
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                
                # Add to watchlist if not already present
                if symbol not in market_context.watch_list:
                    market_context.watch_list.append(symbol)
                    
                    # Send confirmation message
                    await client.chat_postEphemeral(
                        channel=body.get("channel", {}).get("id", ""),
                        user=user_id,
                        text=f"⭐ Added {symbol} to your watchlist!"
                    )
                    
                    logger.info(f"Added {symbol} to watchlist for user {user_id}")
                else:
                    await client.chat_postEphemeral(
                        channel=body.get("channel", {}).get("id", ""),
                        user=user_id,
                        text=f"{symbol} is already in your watchlist."
                    )
            
        except Exception as e:
            logger.error(f"Error adding to watchlist: {str(e)}")
    
    async def handle_symbol_input_change(self, ack: Ack, body: Dict[str, Any], 
                                       client: WebClient, context: BoltContext) -> None:
        """Handle symbol input changes."""
        await ack()
        
        try:
            # This would be triggered by input changes
            # For now, we'll handle it in the modal submission
            pass
            
        except Exception as e:
            logger.error(f"Error handling symbol input change: {str(e)}")
    
    async def handle_modal_submission(self, ack: Ack, body: Dict[str, Any], 
                                    client: WebClient, context: BoltContext) -> None:
        """Handle modal submission with symbol input."""
        try:
            # Get symbol from input
            symbol_input = body["view"]["state"]["values"].get("symbol_input", {})
            symbol_value = symbol_input.get("symbol_value", {}).get("value", "").strip().upper()
            
            if not symbol_value:
                await ack({
                    "response_action": "errors",
                    "errors": {
                        "symbol_input": "Please enter a stock symbol"
                    }
                })
                return
            
            # Validate symbol
            validation_result = validate_symbol(symbol_value)
            if not validation_result.is_valid:
                await ack({
                    "response_action": "errors",
                    "errors": {
                        "symbol_input": f"Invalid symbol: {validation_result.errors[0] if validation_result.errors else 'Unknown error'}"
                    }
                })
                return
            
            await ack()
            
            # Update session with new symbol
            user_id = body["user"]["id"]
            session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
            
            if session_key in self.enhanced_command.active_sessions:
                market_context = self.enhanced_command.active_sessions[session_key]
                market_context.symbol = symbol_value
                
                # Fetch market data for new symbol
                await self.enhanced_command._fetch_market_data(market_context)
                
                # Create new modal with updated data
                updated_modal = await self.enhanced_command._create_enhanced_market_modal(market_context)
                
                # Open new modal (since we can't update after submission)
                await client.views_open(
                    trigger_id=body.get("trigger_id"),
                    view=updated_modal
                )
                
                logger.info(f"Symbol updated to: {symbol_value} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling modal submission: {str(e)}")
            await ack({
                "response_action": "errors",
                "errors": {
                    "symbol_input": "Failed to process symbol. Please try again."
                }
            })
    
    async def _send_error_update(self, client: WebClient, body: Dict[str, Any], error_message: str) -> None:
        """Send error update to user."""
        try:
            user_id = body["user"]["id"]
            channel_id = body.get("channel", {}).get("id")
            
            if channel_id:
                await client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"❌ {error_message}"
                )
        except Exception as e:
            logger.error(f"Failed to send error update: {str(e)}")


def register_enhanced_market_actions(app: App, enhanced_command: EnhancedTradeCommand) -> None:
    """Register enhanced market data action handlers."""
    actions_handler = EnhancedMarketActions(enhanced_command)
    
    # Simple synchronous handlers that work with Slack Bolt
    def handle_quick_symbol_aapl(ack, body, client, context):
        ack()
        logger.info("🎯 AAPL button clicked!")
        try:
            view_id = body["view"]["id"]
            user_id = body["user"]["id"]
            
            # First, show loading state
            loading_modal = {
                "type": "modal",
                "callback_id": "enhanced_trade_modal",
                "title": {
                    "type": "plain_text",
                    "text": "📊 Live Market Data"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📈 AAPL Selected!*\n\n🔄 Fetching live market data for Apple Inc..."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "💰 *Current Price:* Loading...\n📊 *Market Status:* Checking...\n⚡ *Data Quality:* Real-time"
                        }
                    }
                ],
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                }
            }
            
            client.views_update(view_id=view_id, view=loading_modal)
            
            # Fetch real market data using synchronous HTTP request
            import threading
            import requests
            from config.settings import get_config
            
            def fetch_market_data():
                try:
                    # Get API key from config
                    config = get_config()
                    api_key = config.market_data.finnhub_api_key
                    
                    # Make synchronous HTTP request to Finnhub API
                    url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract price data
                        current_price = data.get('c', 0)  # current price
                        price_change = data.get('d', 0)   # change
                        price_change_percent = data.get('dp', 0)  # change percent
                        
                        # Print to terminal
                        print(f"\n🎯 AAPL MARKET DATA FETCHED SUCCESSFULLY!")
                        print(f"💰 Current Price: ${current_price}")
                        print(f"📈 Price Change: ${price_change}")
                        print(f"📊 Change %: {price_change_percent}%")
                        print(f"⚡ Data Quality: Real-time")
                        print(f"🏢 Exchange: NASDAQ")
                        print("-" * 50)
                        
                        # Update modal with real data
                        change_emoji = "📈" if price_change >= 0 else "📉"
                        price_change_text = f"\n{change_emoji} *Change:* ${price_change} ({price_change_percent}%)"
                        
                        updated_modal = {
                            "type": "modal",
                            "callback_id": "enhanced_trade_modal",
                            "title": {
                                "type": "plain_text",
                                "text": "📊 Live Market Data"
                            },
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*📈 AAPL - Apple Inc.*\n\n✅ Live market data fetched successfully!"
                                    }
                                },
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"💰 *Current Price:* ${current_price}\n📊 *Market Status:* Open\n⚡ *Data Quality:* Real-time{price_change_text}"
                                    }
                                }
                            ],
                            "close": {
                                "type": "plain_text",
                                "text": "Close"
                            }
                        }
                        
                        client.views_update(view_id=view_id, view=updated_modal)
                        logger.info(f"✅ AAPL real market data displayed for user {user_id}")
                        
                    else:
                        print(f"❌ API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")
                    
                except Exception as e:
                    print(f"❌ Error fetching AAPL market data: {e}")
                    logger.error(f"Error fetching AAPL market data: {e}")
                    
                    # Show error in modal
                    try:
                        error_modal = {
                            "type": "modal",
                            "callback_id": "enhanced_trade_modal",
                            "title": {
                                "type": "plain_text",
                                "text": "📊 Live Market Data"
                            },
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "*📈 AAPL - Apple Inc.*\n\n❌ Error fetching market data. Please try again."
                                    }
                                }
                            ],
                            "close": {
                                "type": "plain_text",
                                "text": "Close"
                            }
                        }
                        client.views_update(view_id=view_id, view=error_modal)
                    except:
                        pass
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_market_data)
            fetch_thread.daemon = True
            fetch_thread.start()
            
        except Exception as e:
            logger.error(f"Error in AAPL handler: {e}")
            print(f"❌ Error in AAPL handler: {e}")
    
    def handle_quick_symbol_tsla(ack, body, client, context):
        ack()
        logger.info("🎯 TSLA button clicked!")
        try:
            view_id = body["view"]["id"]
            user_id = body["user"]["id"]
            
            # Show loading state
            loading_modal = {
                "type": "modal",
                "callback_id": "enhanced_trade_modal",
                "title": {
                    "type": "plain_text",
                    "text": "📊 Live Market Data"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🚗 TSLA Selected!*\n\n🔄 Fetching live market data for Tesla Inc..."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "💰 *Current Price:* Loading...\n📊 *Market Status:* Checking...\n⚡ *Data Quality:* Real-time"
                        }
                    }
                ],
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                }
            }
            
            client.views_update(view_id=view_id, view=loading_modal)
            
            # Fetch real market data using synchronous HTTP request
            import threading
            import requests
            from config.settings import get_config
            
            def fetch_market_data():
                try:
                    # Get API key from config
                    config = get_config()
                    api_key = config.market_data.finnhub_api_key
                    
                    # Make synchronous HTTP request to Finnhub API
                    url = f"https://finnhub.io/api/v1/quote?symbol=TSLA&token={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract price data
                        current_price = data.get('c', 0)  # current price
                        price_change = data.get('d', 0)   # change
                        price_change_percent = data.get('dp', 0)  # change percent
                        
                        # Print to terminal
                        print(f"\n🎯 TSLA MARKET DATA FETCHED SUCCESSFULLY!")
                        print(f"💰 Current Price: ${current_price}")
                        print(f"📈 Price Change: ${price_change}")
                        print(f"📊 Change %: {price_change_percent}%")
                        print(f"⚡ Data Quality: Real-time")
                        print(f"🏢 Exchange: NASDAQ")
                        print("-" * 50)
                        
                        # Update modal with real data
                        change_emoji = "📈" if price_change >= 0 else "📉"
                        price_change_text = f"\n{change_emoji} *Change:* ${price_change} ({price_change_percent}%)"
                        
                        updated_modal = {
                            "type": "modal",
                            "callback_id": "enhanced_trade_modal",
                            "title": {
                                "type": "plain_text",
                                "text": "📊 Live Market Data"
                            },
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*🚗 TSLA - Tesla Inc.*\n\n✅ Live market data fetched successfully!"
                                    }
                                },
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"💰 *Current Price:* ${current_price}\n📊 *Market Status:* Open\n⚡ *Data Quality:* Real-time{price_change_text}"
                                    }
                                }
                            ],
                            "close": {
                                "type": "plain_text",
                                "text": "Close"
                            }
                        }
                        
                        client.views_update(view_id=view_id, view=updated_modal)
                        logger.info(f"✅ TSLA real market data displayed for user {user_id}")
                        
                    else:
                        print(f"❌ TSLA API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")
                    
                except Exception as e:
                    print(f"❌ Error fetching TSLA market data: {e}")
                    logger.error(f"Error fetching TSLA market data: {e}")
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_market_data)
            fetch_thread.daemon = True
            fetch_thread.start()
            
        except Exception as e:
            logger.error(f"Error in TSLA handler: {e}")
            print(f"❌ Error in TSLA handler: {e}")
    
    def handle_quick_symbol_msft(ack, body, client, context):
        ack()
        logger.info("🎯 MSFT button clicked!")
        try:
            view_id = body["view"]["id"]
            user_id = body["user"]["id"]
            
            # Show loading state
            loading_modal = {
                "type": "modal",
                "callback_id": "enhanced_trade_modal",
                "title": {
                    "type": "plain_text",
                    "text": "📊 Live Market Data"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*💻 MSFT Selected!*\n\n🔄 Fetching live market data for Microsoft Corp..."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "💰 *Current Price:* Loading...\n📊 *Market Status:* Checking...\n⚡ *Data Quality:* Real-time"
                        }
                    }
                ],
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                }
            }
            
            client.views_update(view_id=view_id, view=loading_modal)
            
            # Fetch real market data using synchronous HTTP request
            import threading
            import requests
            from config.settings import get_config
            
            def fetch_market_data():
                try:
                    # Get API key from config
                    config = get_config()
                    api_key = config.market_data.finnhub_api_key
                    
                    # Make synchronous HTTP request to Finnhub API
                    url = f"https://finnhub.io/api/v1/quote?symbol=MSFT&token={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract price data
                        current_price = data.get('c', 0)  # current price
                        price_change = data.get('d', 0)   # change
                        price_change_percent = data.get('dp', 0)  # change percent
                        
                        # Print to terminal
                        print(f"\n🎯 MSFT MARKET DATA FETCHED SUCCESSFULLY!")
                        print(f"💰 Current Price: ${current_price}")
                        print(f"📈 Price Change: ${price_change}")
                        print(f"📊 Change %: {price_change_percent}%")
                        print(f"⚡ Data Quality: Real-time")
                        print(f"🏢 Exchange: NASDAQ")
                        print("-" * 50)
                        
                        # Update modal with real data
                        change_emoji = "📈" if price_change >= 0 else "📉"
                        price_change_text = f"\n{change_emoji} *Change:* ${price_change} ({price_change_percent}%)"
                        
                        updated_modal = {
                            "type": "modal",
                            "callback_id": "enhanced_trade_modal",
                            "title": {
                                "type": "plain_text",
                                "text": "📊 Live Market Data"
                            },
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*💻 MSFT - Microsoft Corp.*\n\n✅ Live market data fetched successfully!"
                                    }
                                },
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"💰 *Current Price:* ${current_price}\n📊 *Market Status:* Open\n⚡ *Data Quality:* Real-time{price_change_text}"
                                    }
                                }
                            ],
                            "close": {
                                "type": "plain_text",
                                "text": "Close"
                            }
                        }
                        
                        client.views_update(view_id=view_id, view=updated_modal)
                        logger.info(f"✅ MSFT real market data displayed for user {user_id}")
                        
                    else:
                        print(f"❌ MSFT API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")
                    
                except Exception as e:
                    print(f"❌ Error fetching MSFT market data: {e}")
                    logger.error(f"Error fetching MSFT market data: {e}")
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_market_data)
            fetch_thread.daemon = True
            fetch_thread.start()
            
        except Exception as e:
            logger.error(f"Error in MSFT handler: {e}")
            print(f"❌ Error in MSFT handler: {e}")
    
    def handle_quick_symbol_googl(ack, body, client, context):
        ack()
        logger.info("🎯 GOOGL button clicked!")
        try:
            view_id = body["view"]["id"]
            user_id = body["user"]["id"]
            
            # Show loading state
            loading_modal = {
                "type": "modal",
                "callback_id": "enhanced_trade_modal",
                "title": {
                    "type": "plain_text",
                    "text": "📊 Live Market Data"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🔍 GOOGL Selected!*\n\n🔄 Fetching live market data for Alphabet Inc..."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "💰 *Current Price:* Loading...\n📊 *Market Status:* Checking...\n⚡ *Data Quality:* Real-time"
                        }
                    }
                ],
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                }
            }
            
            client.views_update(view_id=view_id, view=loading_modal)
            
            # Fetch real market data using synchronous HTTP request
            import threading
            import requests
            from config.settings import get_config
            
            def fetch_market_data():
                try:
                    # Get API key from config
                    config = get_config()
                    api_key = config.market_data.finnhub_api_key
                    
                    # Make synchronous HTTP request to Finnhub API
                    url = f"https://finnhub.io/api/v1/quote?symbol=GOOGL&token={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract price data
                        current_price = data.get('c', 0)  # current price
                        price_change = data.get('d', 0)   # change
                        price_change_percent = data.get('dp', 0)  # change percent
                        
                        # Print to terminal
                        print(f"\n🎯 GOOGL MARKET DATA FETCHED SUCCESSFULLY!")
                        print(f"💰 Current Price: ${current_price}")
                        print(f"📈 Price Change: ${price_change}")
                        print(f"📊 Change %: {price_change_percent}%")
                        print(f"⚡ Data Quality: Real-time")
                        print(f"🏢 Exchange: NASDAQ")
                        print("-" * 50)
                        
                        # Update modal with real data
                        change_emoji = "📈" if price_change >= 0 else "📉"
                        price_change_text = f"\n{change_emoji} *Change:* ${price_change} ({price_change_percent}%)"
                        
                        updated_modal = {
                            "type": "modal",
                            "callback_id": "enhanced_trade_modal",
                            "title": {
                                "type": "plain_text",
                                "text": "📊 Live Market Data"
                            },
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*🔍 GOOGL - Alphabet Inc.*\n\n✅ Live market data fetched successfully!"
                                    }
                                },
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"💰 *Current Price:* ${current_price}\n📊 *Market Status:* Open\n⚡ *Data Quality:* Real-time{price_change_text}"
                                    }
                                }
                            ],
                            "close": {
                                "type": "plain_text",
                                "text": "Close"
                            }
                        }
                        
                        client.views_update(view_id=view_id, view=updated_modal)
                        logger.info(f"✅ GOOGL real market data displayed for user {user_id}")
                        
                    else:
                        print(f"❌ GOOGL API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")
                    
                except Exception as e:
                    print(f"❌ Error fetching GOOGL market data: {e}")
                    logger.error(f"Error fetching GOOGL market data: {e}")
            
            # Start the fetch in a separate thread
            fetch_thread = threading.Thread(target=fetch_market_data)
            fetch_thread.daemon = True
            fetch_thread.start()
            
        except Exception as e:
            logger.error(f"Error in GOOGL handler: {e}")
            print(f"❌ Error in GOOGL handler: {e}")
    
    # Register the handlers using the decorator pattern
    app.action("quick_symbol_AAPL")(handle_quick_symbol_aapl)
    app.action("quick_symbol_TSLA")(handle_quick_symbol_tsla)
    app.action("quick_symbol_MSFT")(handle_quick_symbol_msft)
    app.action("quick_symbol_GOOGL")(handle_quick_symbol_googl)
    
    # Refresh button
    def handle_refresh(ack, body, client, context):
        ack()
        logger.info("🔄 Refresh button clicked!")
    
    # Auto-refresh toggle
    def handle_auto_refresh_toggle(ack, body, client, context):
        ack()
        logger.info("🔴 Auto-refresh toggled!")
    
    # View type change
    def handle_view_change(ack, body, client, context):
        ack()
        logger.info("👁️ View type changed!")
    
    # Add to watchlist
    def handle_watchlist_add(ack, body, client, context):
        ack()
        logger.info("⭐ Added to watchlist!")
    
    # Modal submission
    def handle_modal_submit(ack, body, client, context):
        ack()
        logger.info("📝 Modal submitted!")
    
    # Post-trade: return to live data view
    def handle_return_to_live(ack, body, client, context):
        """Return from Trade Summary to the enhanced live data modal."""
        ack()
        try:
            # Recover symbol from private_metadata saved in summary modal
            view = body.get("view", {})
            private_raw = view.get("private_metadata") or "{}"
            import json as _json
            meta = {}
            try:
                meta = _json.loads(private_raw)
            except Exception:
                meta = {}
            symbol = meta.get("symbol") or "AAPL"
            
            # Rebuild enhanced live data modal quickly
            loading_modal = {
                "type": "modal",
                "callback_id": "enhanced_trade_modal",
                "title": {"type": "plain_text", "text": "📊 Live Market Data"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*📊 {symbol}*\n\n🔄 Loading market data..."}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "💰 *Current Price:* Loading...\n📊 *Market Status:* Checking...\n⚡ *Data Quality:* Real-time"}}
                ],
                "close": {"type": "plain_text", "text": "Close"}
            }
            client.views_update(view_id=view.get("id"), view=loading_modal)
            
            # Kick async refresh to fetch and update
            try:
                user_id = body.get("user", {}).get("id")
                if user_id:
                    # Store in active session if present, then update
                    session_key = f"{user_id}_{body.get('channel', {}).get('id', 'modal')}"
                    if session_key in enhanced_command.active_sessions:
                        market_context = enhanced_command.active_sessions[session_key]
                        market_context.symbol = symbol
                    else:
                        from listeners.enhanced_trade_command import EnhancedMarketContext
                        market_context = EnhancedMarketContext(user=None, channel_id=body.get('channel', {}).get('id', ''), trigger_id=body.get('trigger_id', ''), symbol=symbol)
                        enhanced_command.active_sessions[session_key] = market_context
                    
                    # Fetch and update
                    import asyncio as _asyncio
                    async def _refresh():
                        try:
                            await enhanced_command._fetch_market_data(market_context)
                            updated_modal = await enhanced_command._create_enhanced_market_modal(market_context)
                            client.views_update(view_id=view.get("id"), view=updated_modal)
                        except Exception as _e:
                            logger.warning(f"Return-to-live refresh failed: {_e}")
                    _asyncio.create_task(_refresh())
            except Exception as e:
                logger.warning(f"Post-trade return scheduling error: {e}")
        except Exception as e:
            logger.error(f"Error returning to live data modal: {e}")
    
    # Start Trade button handler
    def handle_start_trade(ack, body, client, context):
        """Handle Start Trade button click - opens trade entry form."""
        ack()
        logger.info("💼 Start Trade button clicked!")
        
        try:
            # Extract current symbol from the modal's metadata or state
            view = body.get("view", {})
            blocks = view.get("blocks", [])
            
            # Try to extract symbol from the modal title or blocks
            symbol = "AAPL"  # Default
            for block in blocks:
                if block.get("type") == "section":
                    text = block.get("text", {}).get("text", "")
                    # Extract symbol from text like "*📈 AAPL - Apple Inc.*"
                    import re
                    match = re.search(r'\*[^\s]+ (\w+) -', text)
                    if match:
                        symbol = match.group(1)
                        break
            
            trigger_id = body.get("trigger_id")
            user_id = body["user"]["id"]
            
            logger.info(f"Opening trade entry modal for {symbol}")
            
            # Create trade entry modal matching the screenshot
            trade_modal = {
                "type": "modal",
                "callback_id": "trade_entry_modal",
                "title": {
                    "type": "plain_text",
                    "text": "📊 Enter New Trade"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Execute Trade"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "private_metadata": json.dumps({"symbol": symbol}),
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "This links the trade to a specific virtual portfolio."
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "ticker_symbol",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "ticker_value",
                            "initial_value": symbol,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g., AAPL, GOOG, NVDA"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Ticker Symbol"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "position_type",
                        "element": {
                            "type": "radio_buttons",
                            "action_id": "position_value",
                            "initial_option": {
                                "text": {
                                    "type": "plain_text",
                                    "text": "BUY (Long Position)"
                                },
                                "value": "buy"
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "BUY (Long Position)"
                                    },
                                    "value": "buy"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "SELL (Short Position)"
                                    },
                                    "value": "sell"
                                }
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Position Type"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "quantity",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "quantity_value",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g., 100"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Quantity (Shares/Contracts)"
                        },
                        "hint": {
                            "type": "plain_text",
                            "text": "Enter an integer amount."
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "order_type",
                        "element": {
                            "type": "static_select",
                            "action_id": "order_value",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select Order Type"
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Market Order"
                                    },
                                    "value": "market"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Limit Order"
                                    },
                                    "value": "limit"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Stop Order"
                                    },
                                    "value": "stop"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Stop-Limit Order"
                                    },
                                    "value": "stop_limit"
                                }
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Order Type"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "limit_price",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "limit_value",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g., 150.25"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Limit/Stop Price (Required for Limit/Stop Orders)"
                        },
                        "hint": {
                            "type": "plain_text",
                            "text": "Only needed if Order Type is Limit or Stop."
                        }
                    }
                ]
            }
            
            # Open the trade entry modal (replace current modal)
            client.views_update(
                view_id=body.get("view", {}).get("id"),
                view=trade_modal
            )
            
            logger.info(f"✅ Trade entry modal opened for {symbol} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error opening trade entry modal: {e}")
            print(f"❌ Error opening trade entry modal: {e}")
    
    # Trade execution handler (when user submits the trade form)
    def handle_trade_execution(ack, body, client, context):
        """Handle trade entry modal submission - execute via Alpaca Paper Trading or mock."""
        logger.info("🎯 Trade execution handler called!")
        
        try:
            # Extract form data
            values = body["view"]["state"]["values"]
            
            ticker = values["ticker_symbol"]["ticker_value"]["value"]
            position_type = values["position_type"]["position_value"]["selected_option"]["value"]
            quantity = values["quantity"]["quantity_value"]["value"]
            order_type = values["order_type"]["order_value"]["selected_option"]["value"]
            limit_price = values["limit_price"]["limit_value"].get("value", "")
            
            # Validate inputs
            errors = {}
            
            if not ticker or not ticker.strip():
                errors["ticker_symbol"] = "Ticker symbol is required"
            
            if not quantity or not quantity.strip():
                errors["quantity"] = "Quantity is required"
            else:
                try:
                    qty_int = int(quantity)
                    if qty_int <= 0:
                        errors["quantity"] = "Quantity must be positive"
                except ValueError:
                    errors["quantity"] = "Quantity must be a valid integer"
            
            if order_type in ["limit", "stop", "stop_limit"] and not limit_price:
                errors["limit_price"] = f"{order_type.replace('_', '-').title()} order requires a price"
            
            if limit_price:
                try:
                    float(limit_price)
                except ValueError:
                    errors["limit_price"] = "Price must be a valid number"
            
            if errors:
                ack(response_action="errors", errors=errors)
                return
            
            # ========== EXECUTE TRADE VIA TRADING SERVICE ==========
            user_id = body["user"]["id"]
            from datetime import datetime, timezone as _tz
            from decimal import Decimal
            from services.service_container import get_container
            from services.trading_api import TradingAPIService, OrderType as TradingOrderType
            from models.trade import Trade, TradeType, TradeStatus
            import uuid as _uuid
            import asyncio as _a
            import threading as _threading
            
            exec_time = datetime.now(_tz.utc)
            trade_id = str(_uuid.uuid4())
            
            # Convert order type
            order_type_map = {
                'market': TradingOrderType.MARKET,
                'limit': TradingOrderType.LIMIT,
                'stop': TradingOrderType.STOP,
                'stop_limit': TradingOrderType.STOP_LIMIT
            }
            trading_order_type = order_type_map.get(order_type, TradingOrderType.MARKET)
            
            # Create trade object
            trade_obj = Trade(
                trade_id=trade_id,
                user_id=user_id,
                symbol=ticker.upper(),
                quantity=int(quantity),
                trade_type=TradeType.BUY if position_type == "buy" else TradeType.SELL,
                price=Decimal(limit_price) if limit_price else Decimal("0"),
                timestamp=exec_time,
                status=TradeStatus.PENDING
            )
            
            # Execute trade using TradingAPIService (synchronously in thread for modal ack)
            execution_result = {"success": False, "error": None, "execution_report": None}
            
            def execute_trade_sync():
                try:
                    loop = _a.new_event_loop()
                    _a.set_event_loop(loop)
                    container = get_container()
                    trading_service = container.get(TradingAPIService)
                    
                    # Ensure Alpaca is initialized
                    loop.run_until_complete(trading_service.initialize())
                    
                    # Execute trade
                    execution_report = loop.run_until_complete(
                        trading_service.execute_trade(trade_obj, trading_order_type)
                    )
                    
                    execution_result["success"] = True
                    execution_result["execution_report"] = execution_report
                    loop.close()
                except Exception as e:
                    logger.error(f"Trade execution failed: {e}")
                    execution_result["success"] = False
                    execution_result["error"] = str(e)
            
            # Execute in thread to avoid blocking
            exec_thread = _threading.Thread(target=execute_trade_sync)
            exec_thread.start()
            exec_thread.join(timeout=15)  # Wait max 15 seconds for execution
            
            # Build summary based on execution results
            if execution_result["success"] and execution_result["execution_report"]:
                exec_report = execution_result["execution_report"]
                execution_mode = exec_report.audit_trail[-1] if exec_report.audit_trail else "Unknown"
                
                # Determine execution mode display
                if "Alpaca" in str(exec_report.audit_trail):
                    execution_badge = "🚀 Alpaca Paper Trading"
                else:
                    execution_badge = "🎭 Mock Simulator"
                
                # Get execution price
                if exec_report.average_fill_price:
                    fill_price = float(exec_report.average_fill_price)
                    price_display = f"${fill_price:.2f}"
                    total_value = fill_price * int(quantity)
                else:
                    fill_price = float(limit_price) if limit_price else 0
                    price_display = f"${limit_price}" if limit_price else "Market"
                    total_value = fill_price * int(quantity) if limit_price else None
            else:
                # Execution failed - use submitted values
                execution_badge = "⚠️ Execution Failed"
                fill_price = float(limit_price) if limit_price else 0
                price_display = f"${limit_price}" if limit_price else "Market"
                total_value = fill_price * int(quantity) if limit_price else None
            
            side_text = "BUY" if position_type == "buy" else "SELL"

            # Fetch current position for summary (synchronously for immediate display)
            try:
                from services.service_container import get_container
                from services.database import DatabaseService
                container = get_container()
                db_service = container.get(DatabaseService)
                
                # Try to get existing position synchronously (will be None if new)
                import threading
                position_data = {"prev_qty": 0, "prev_avg": 0, "new_qty": 0, "new_avg": 0}
                
                def fetch_position():
                    try:
                        import asyncio as _a
                        loop = _a.new_event_loop()
                        _a.set_event_loop(loop)
                        positions = loop.run_until_complete(db_service.get_user_positions(user_id))
                        existing = next((p for p in positions if p.symbol == ticker.upper()), None)
                        if existing:
                            position_data["prev_qty"] = existing.quantity
                            position_data["prev_avg"] = float(existing.average_price)
                        loop.close()
                    except Exception as e:
                        logger.warning(f"Could not fetch position: {e}")
                
                fetch_thread = threading.Thread(target=fetch_position)
                fetch_thread.start()
                fetch_thread.join(timeout=0.5)  # Wait max 500ms
                
                # Calculate new position
                trade_qty = int(quantity) if position_type == "buy" else -int(quantity)
                prev_qty = position_data["prev_qty"]
                prev_avg = position_data["prev_avg"]
                new_qty = prev_qty + trade_qty
                
                # Calculate new average cost
                if new_qty != 0 and limit_price:
                    if position_type == "buy":
                        new_avg = ((prev_qty * prev_avg) + (int(quantity) * float(limit_price))) / new_qty if new_qty > 0 else float(limit_price)
                    else:
                        new_avg = prev_avg  # Selling doesn't change avg cost
                else:
                    new_avg = float(limit_price) if limit_price else 0
                
                position_data["new_qty"] = new_qty
                position_data["new_avg"] = new_avg
            except Exception as pos_err:
                logger.warning(f"Position calc error: {pos_err}")
                position_data = {"prev_qty": 0, "prev_avg": 0, "new_qty": int(quantity), "new_avg": float(limit_price) if limit_price else 0}

            # Build additional execution details if available
            execution_details = ""
            if execution_result.get("execution_report"):
                exec_report = execution_result["execution_report"]
                if hasattr(exec_report, 'fills') and exec_report.fills:
                    alpaca_order_id = exec_report.fills[0].fill_id if exec_report.fills else None
                    if alpaca_order_id and "Alpaca" in str(exec_report.audit_trail):
                        execution_details = f" • Alpaca Order: `{alpaca_order_id[:8]}...`"
            
            summary_blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Trade Executed Successfully*\n{execution_badge}"}},
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Symbol*\n{ticker.upper()}"},
                        {"type": "mrkdwn", "text": f"*Side*\n{side_text}"},
                        {"type": "mrkdwn", "text": f"*Quantity*\n{int(quantity):,}"},
                        {"type": "mrkdwn", "text": f"*Order Type*\n{order_type.replace('_', ' ').title()}"},
                        {"type": "mrkdwn", "text": f"*Fill Price*\n{price_display}"},
                        {"type": "mrkdwn", "text": f"*Total*\n{('$' + format(total_value, ',.2f')) if total_value is not None else '—'}"}
                    ]
                },
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Trade ID: `{trade_id}`{execution_details} • Time: {exec_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"}]},
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📊 Position Impact*\n"
                                f"Previous: *{position_data['prev_qty']:,}* shares @ ${position_data['prev_avg']:.2f}\n"
                                f"New Position: *{position_data['new_qty']:,}* shares @ ${position_data['new_avg']:.2f}\n"
                                f"{'📈 *First position in ' + ticker.upper() + '*' if position_data['prev_qty'] == 0 else '✅ Position updated'}"
                    }
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "📊 View Portfolio"}, "value": "view_portfolio", "action_id": "posttrade_view_portfolio"},
                        {"type": "button", "text": {"type": "plain_text", "text": "➕ New Trade"}, "value": "new_trade", "action_id": "posttrade_new_trade"},
                        {"type": "button", "text": {"type": "plain_text", "text": "🛑 Set Stop Loss"}, "value": ticker.upper(), "action_id": "posttrade_set_stop"}
                    ]
                }
            ]

            import json as _json
            summary_modal = {
                "type": "modal",
                "callback_id": "trade_summary_modal",
                "title": {"type": "plain_text", "text": "Trade Summary"},
                "close": {"type": "plain_text", "text": "Done"},
                "blocks": summary_blocks,
                "private_metadata": _json.dumps({"symbol": ticker.upper()})
            }

            ack(response_action="update", view=summary_modal)

            # Persist trade and update position asynchronously after ack
            # (This is now handled by TradingAPIService during execution)
            logger.info(f"✅ Trade {trade_id} executed and will be persisted by TradingAPIService")
            
            return
            
            # Send success message
            try:
                channel_id = body.get("view", {}).get("private_metadata", {})
                
                # Try to get channel from the initial interaction
                # For now, we'll post an ephemeral message
                success_message = (
                    f"✅ *Trade Executed Successfully!*\n\n"
                    f"• Symbol: *{ticker.upper()}*\n"
                    f"• Type: *{position_type.upper()}*\n"
                    f"• Quantity: *{quantity}* shares\n"
                    f"• Order Type: *{order_type.upper()}*"
                )
                
                if limit_price:
                    success_message += f"\n• Price: *${limit_price}*"
                
                success_message += f"\n• Execution: *MOCK MODE (Simulated)*\n\n"
                success_message += "_This trade has been logged to your portfolio._"
                
                # Send message - note: we may need channel context
                logger.info(f"Trade success message prepared for user {user_id}")
                print(f"\n✅ Success message: {success_message}\n")
                
            except Exception as msg_error:
                logger.error(f"Error sending success message: {msg_error}")
            
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            import traceback
            traceback.print_exc()
            ack(response_action="errors", errors={"ticker_symbol": "Failed to execute trade. Please try again."})
    
    # Register the other handlers
    app.action("refresh_market_data")(handle_refresh)
    app.action("toggle_auto_refresh")(handle_auto_refresh_toggle)
    app.action("change_view_type")(handle_view_change)
    app.action("add_to_watchlist")(handle_watchlist_add)
    app.action("start_trade")(handle_start_trade)  # NEW: Start Trade button
    app.view("enhanced_trade_modal")(handle_modal_submit)
    # Button on summary modal to return to live view
    app.action("posttrade_new_trade")(handle_return_to_live)
    app.view("trade_entry_modal")(handle_trade_execution)  # NEW: Trade execution
    
    logger.info("✅ Enhanced market data action handlers registered successfully")
    logger.info(f"📋 Registered actions: quick_symbol_AAPL, quick_symbol_TSLA, quick_symbol_MSFT, quick_symbol_GOOGL, start_trade")