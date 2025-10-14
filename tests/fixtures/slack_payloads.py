"""
Slack Payload Fixtures for Integration Testing

This module provides factory functions for creating realistic Slack event payloads
used in integration testing. Includes slash commands, button actions, modal submissions,
and App Home events with proper structure and validation.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid


def create_slash_command_payload(
    command: str,
    user_id: str,
    channel_id: str,
    team_id: str = 'T1234567890',
    text: str = '',
    trigger_id: Optional[str] = None,
    response_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a realistic slash command payload.
    
    Args:
        command: The slash command (e.g., '/trade')
        user_id: Slack user ID
        channel_id: Slack channel ID
        team_id: Slack team/workspace ID
        text: Command text/parameters
        trigger_id: Trigger ID for opening modals
        response_url: Response URL for delayed responses
        
    Returns:
        Slack slash command payload dictionary
    """
    if trigger_id is None:
        trigger_id = f"trigger_{uuid.uuid4().hex[:12]}"
    
    if response_url is None:
        response_url = f"https://hooks.slack.com/commands/{team_id}/{channel_id}/{uuid.uuid4().hex}"
    
    return {
        'token': 'test_verification_token',
        'team_id': team_id,
        'team_domain': 'jain-global',
        'channel_id': channel_id,
        'channel_name': 'trading-private',
        'user_id': user_id,
        'user_name': 'test.user',
        'command': command,
        'text': text,
        'response_url': response_url,
        'trigger_id': trigger_id,
        'api_app_id': 'A1234567890',
        'is_enterprise_install': False
    }


def create_button_action_payload(
    action_id: str,
    user_id: str,
    view_id: str,
    team_id: str = 'T1234567890',
    channel_id: str = 'C1234567890',
    trigger_id: Optional[str] = None,
    block_id: Optional[str] = None,
    value: Optional[str] = None,
    state_values: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a button action payload.
    
    Args:
        action_id: ID of the action/button clicked
        user_id: Slack user ID
        view_id: ID of the view containing the button
        team_id: Slack team ID
        channel_id: Slack channel ID
        trigger_id: Trigger ID for modal operations
        block_id: Block ID containing the action
        value: Action value
        state_values: Current form state values
        
    Returns:
        Slack button action payload dictionary
    """
    if trigger_id is None:
        trigger_id = f"trigger_{uuid.uuid4().hex[:12]}"
    
    if block_id is None:
        block_id = f"block_{action_id}"
    
    if state_values is None:
        state_values = {}
    
    return {
        'type': 'block_actions',
        'user': {
            'id': user_id,
            'username': 'test.user',
            'name': 'test.user',
            'team_id': team_id
        },
        'api_app_id': 'A1234567890',
        'token': 'test_verification_token',
        'container': {
            'type': 'view',
            'view_id': view_id
        },
        'trigger_id': trigger_id,
        'team': {
            'id': team_id,
            'domain': 'jain-global'
        },
        'channel': {
            'id': channel_id,
            'name': 'trading-private'
        },
        'view': {
            'id': view_id,
            'team_id': team_id,
            'type': 'modal',
            'callback_id': 'trade_modal',
            'state': {
                'values': state_values
            },
            'hash': f"hash_{uuid.uuid4().hex[:8]}",
            'title': {
                'type': 'plain_text',
                'text': 'Execute Trade'
            },
            'close': {
                'type': 'plain_text',
                'text': 'Cancel'
            },
            'submit': {
                'type': 'plain_text',
                'text': 'Submit'
            },
            'private_metadata': '',
            'root_view_id': view_id,
            'app_id': 'A1234567890',
            'external_id': '',
            'app_installed_team_id': team_id,
            'bot_id': 'B1234567890'
        },
        'actions': [
            {
                'action_id': action_id,
                'block_id': block_id,
                'text': {
                    'type': 'plain_text',
                    'text': action_id.replace('_', ' ').title()
                },
                'value': value or action_id,
                'type': 'button',
                'action_ts': str(int(datetime.now(timezone.utc).timestamp()))
            }
        ],
        'response_url': f"https://hooks.slack.com/actions/{team_id}/{channel_id}/{uuid.uuid4().hex}",
        'is_enterprise_install': False
    }


def create_modal_submission_payload(
    callback_id: str,
    user_id: str,
    view_id: str,
    state_values: Dict[str, Any],
    team_id: str = 'T1234567890',
    private_metadata: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a modal submission payload.
    
    Args:
        callback_id: Modal callback ID
        user_id: Slack user ID
        view_id: View ID of the modal
        state_values: Form state values from the modal
        team_id: Slack team ID
        private_metadata: Private metadata JSON string
        
    Returns:
        Slack modal submission payload dictionary
    """
    if private_metadata is None:
        private_metadata = '{}'
    
    return {
        'type': 'view_submission',
        'team': {
            'id': team_id,
            'domain': 'jain-global'
        },
        'user': {
            'id': user_id,
            'username': 'test.user',
            'name': 'test.user',
            'team_id': team_id
        },
        'api_app_id': 'A1234567890',
        'token': 'test_verification_token',
        'trigger_id': f"trigger_{uuid.uuid4().hex[:12]}",
        'view': {
            'id': view_id,
            'team_id': team_id,
            'type': 'modal',
            'callback_id': callback_id,
            'state': {
                'values': state_values
            },
            'hash': f"hash_{uuid.uuid4().hex[:8]}",
            'title': {
                'type': 'plain_text',
                'text': 'Execute Trade'
            },
            'close': {
                'type': 'plain_text',
                'text': 'Cancel'
            },
            'submit': {
                'type': 'plain_text',
                'text': 'Submit'
            },
            'private_metadata': private_metadata,
            'root_view_id': view_id,
            'app_id': 'A1234567890',
            'external_id': '',
            'app_installed_team_id': team_id,
            'bot_id': 'B1234567890'
        },
        'response_urls': [],
        'is_enterprise_install': False
    }


def create_app_home_payload(
    user_id: str,
    team_id: str = 'T1234567890',
    tab: str = 'home'
) -> Dict[str, Any]:
    """
    Create an App Home opened event payload.
    
    Args:
        user_id: Slack user ID
        team_id: Slack team ID
        tab: Tab that was opened ('home', 'messages')
        
    Returns:
        Slack App Home event payload dictionary
    """
    return {
        'token': 'test_verification_token',
        'team_id': team_id,
        'api_app_id': 'A1234567890',
        'event': {
            'type': 'app_home_opened',
            'user': user_id,
            'channel': f"D{user_id[1:]}",  # DM channel ID
            'tab': tab,
            'event_ts': str(datetime.now(timezone.utc).timestamp())
        },
        'type': 'event_callback',
        'event_id': f"Ev{uuid.uuid4().hex[:8].upper()}",
        'event_time': int(datetime.now(timezone.utc).timestamp()),
        'authorizations': [
            {
                'enterprise_id': None,
                'team_id': team_id,
                'user_id': 'U1234567890',
                'is_bot': True,
                'is_enterprise_install': False
            }
        ],
        'is_ext_shared_channel': False,
        'event_context': f"1-app_home_opened-{team_id}-{user_id}"
    }


def create_message_event_payload(
    user_id: str,
    channel_id: str,
    text: str,
    team_id: str = 'T1234567890',
    message_ts: Optional[str] = None,
    thread_ts: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a message event payload.
    
    Args:
        user_id: Slack user ID who sent the message
        channel_id: Channel where message was sent
        text: Message text
        team_id: Slack team ID
        message_ts: Message timestamp
        thread_ts: Thread timestamp if reply
        
    Returns:
        Slack message event payload dictionary
    """
    if message_ts is None:
        message_ts = str(datetime.now(timezone.utc).timestamp())
    
    event_data = {
        'type': 'message',
        'user': user_id,
        'text': text,
        'ts': message_ts,
        'channel': channel_id,
        'event_ts': message_ts,
        'channel_type': 'channel'
    }
    
    if thread_ts:
        event_data['thread_ts'] = thread_ts
    
    return {
        'token': 'test_verification_token',
        'team_id': team_id,
        'api_app_id': 'A1234567890',
        'event': event_data,
        'type': 'event_callback',
        'event_id': f"Ev{uuid.uuid4().hex[:8].upper()}",
        'event_time': int(datetime.now(timezone.utc).timestamp()),
        'authorizations': [
            {
                'enterprise_id': None,
                'team_id': team_id,
                'user_id': 'U1234567890',
                'is_bot': True,
                'is_enterprise_install': False
            }
        ],
        'is_ext_shared_channel': False,
        'event_context': f"1-message-{team_id}-{channel_id}"
    }


def create_interactive_message_payload(
    user_id: str,
    channel_id: str,
    action_name: str,
    action_value: str,
    team_id: str = 'T1234567890',
    message_ts: Optional[str] = None,
    callback_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an interactive message action payload.
    
    Args:
        user_id: Slack user ID
        channel_id: Channel ID
        action_name: Name of the action
        action_value: Value of the action
        team_id: Slack team ID
        message_ts: Message timestamp
        callback_id: Callback ID for the interactive message
        
    Returns:
        Slack interactive message payload dictionary
    """
    if message_ts is None:
        message_ts = str(datetime.now(timezone.utc).timestamp())
    
    if callback_id is None:
        callback_id = 'interactive_message'
    
    return {
        'type': 'interactive_message',
        'actions': [
            {
                'name': action_name,
                'type': 'button',
                'value': action_value
            }
        ],
        'callback_id': callback_id,
        'team': {
            'id': team_id,
            'domain': 'jain-global'
        },
        'channel': {
            'id': channel_id,
            'name': 'trading-private'
        },
        'user': {
            'id': user_id,
            'name': 'test.user'
        },
        'action_ts': str(int(datetime.now(timezone.utc).timestamp())),
        'message_ts': message_ts,
        'attachment_id': '1',
        'token': 'test_verification_token',
        'is_app_unfurl': False,
        'response_url': f"https://hooks.slack.com/actions/{team_id}/{channel_id}/{uuid.uuid4().hex}",
        'trigger_id': f"trigger_{uuid.uuid4().hex[:12]}"
    }


def create_options_load_payload(
    user_id: str,
    action_id: str,
    value: str,
    team_id: str = 'T1234567890',
    view_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an options load payload for select menus.
    
    Args:
        user_id: Slack user ID
        action_id: Action ID of the select menu
        value: Current value being typed
        team_id: Slack team ID
        view_id: View ID if in a modal
        
    Returns:
        Slack options load payload dictionary
    """
    payload = {
        'type': 'block_suggestion',
        'user': {
            'id': user_id,
            'username': 'test.user',
            'team_id': team_id
        },
        'api_app_id': 'A1234567890',
        'token': 'test_verification_token',
        'action_id': action_id,
        'block_id': f"block_{action_id}",
        'value': value,
        'team': {
            'id': team_id,
            'domain': 'jain-global'
        }
    }
    
    if view_id:
        payload['container'] = {
            'type': 'view',
            'view_id': view_id
        }
    
    return payload