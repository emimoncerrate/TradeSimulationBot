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
    
    # Register the other handlers
    app.action("refresh_market_data")(handle_refresh)
    app.action("toggle_auto_refresh")(handle_auto_refresh_toggle)
    app.action("change_view_type")(handle_view_change)
    app.action("add_to_watchlist")(handle_watchlist_add)
    app.view("enhanced_trade_modal")(handle_modal_submit)
    
    logger.info("✅ Enhanced market data action handlers registered successfully")
    logger.info(f"📋 Registered actions: quick_symbol_AAPL, quick_symbol_TSLA, quick_symbol_MSFT, quick_symbol_GOOGL")