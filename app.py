"""
Jain Global Slack Trading Bot - Main Application Entry Point

This module serves as the main entry point for the Slack Trading Bot application.
It initializes the Slack Bolt app, configures middleware, registers event handlers,
and provides both Lambda and local development server capabilities.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any
import json
from datetime import datetime

# Slack Bolt Framework
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

# FastAPI for local development server
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Application modules
from config.settings import get_config, validate_environment
from listeners.commands import register_command_handlers
from listeners.actions import register_action_handlers
from listeners.events import register_event_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global configuration
config = get_config()

# Initialize Slack Bolt app
def create_slack_app() -> App:
    """
    Create and configure the Slack Bolt application.
    
    Returns:
        App: Configured Slack Bolt application instance
    """
    try:
        # Get Slack configuration
        slack_config = config.get_slack_config()
        
        # Create Slack app with configuration
        app = App(
            token=slack_config['token'],
            signing_secret=slack_config['signing_secret'],
            process_before_response=True  # Important for Lambda
        )
        
        # Register middleware
        register_middleware(app)
        
        # Register event handlers
        register_command_handlers(app)
        register_action_handlers(app)
        register_event_handlers(app)
        
        logger.info("Slack Bolt app initialized successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to initialize Slack app: {e}")
        raise

def register_middleware(app: App) -> None:
    """
    Register middleware for the Slack app.
    
    Args:
        app: Slack Bolt application instance
    """
    
    @app.middleware
    def log_requests(body: Dict[str, Any], next):
        """Log all incoming requests for debugging and audit purposes."""
        request_id = body.get('event_id', 'unknown')
        user_id = body.get('user_id', 'unknown')
        
        logger.info(f"Request {request_id} from user {user_id}: {body.get('type', 'unknown')}")
        
        # Call next middleware/handler
        response = next()
        
        logger.info(f"Request {request_id} completed")
        return response
    
    @app.middleware
    def validate_channel(body: Dict[str, Any], next):
        """Validate that requests come from approved channels."""
        # Skip validation for certain event types
        skip_validation = [
            'url_verification',
            'app_home_opened',
            'tokens_revoked'
        ]
        
        event_type = body.get('type')
        if event_type in skip_validation:
            return next()
        
        # Get channel ID from various possible locations
        channel_id = None
        if 'channel_id' in body:
            channel_id = body['channel_id']
        elif 'event' in body and 'channel' in body['event']:
            channel_id = body['event']['channel']
        elif 'channel' in body:
            channel_id = body['channel']
        
        # If we have a channel ID, validate it
        if channel_id and not config.is_channel_approved(channel_id):
            logger.warning(f"Request from unapproved channel: {channel_id}")
            # For now, we'll log but not block - this can be made stricter in production
        
        return next()

# Create Slack app instance
slack_app = create_slack_app()

# Lambda handler for AWS deployment
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Slack events.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Dict containing response data
    """
    try:
        # Validate environment on cold start
        if not validate_environment():
            logger.error("Environment validation failed")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Environment validation failed'})
            }
        
        # Create Slack request handler
        handler = SlackRequestHandler(app=slack_app)
        
        # Process the request
        response = handler.handle(event, context)
        
        logger.info(f"Lambda request processed successfully: {response.get('statusCode', 'unknown')}")
        return response
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# FastAPI app for local development
fastapi_app = FastAPI(
    title="Jain Global Slack Trading Bot",
    description="Slack Trading Bot for Jain Global investment management",
    version=config.app_version
)

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Validate environment
        env_valid = validate_environment()
        
        return JSONResponse(
            status_code=200 if env_valid else 503,
            content={
                'status': 'healthy' if env_valid else 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': config.app_version,
                'environment': config.environment.value,
                'config_valid': env_valid
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        )

@fastapi_app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events via HTTP."""
    try:
        # Get request body
        body = await request.body()
        headers = dict(request.headers)
        
        # Create Lambda-style event
        lambda_event = {
            'body': body.decode('utf-8'),
            'headers': headers,
            'httpMethod': 'POST',
            'path': '/slack/events',
            'queryStringParameters': dict(request.query_params) or None,
            'isBase64Encoded': False
        }
        
        # Process with Lambda handler
        response = lambda_handler(lambda_event, None)
        
        return JSONResponse(
            status_code=response.get('statusCode', 200),
            content=json.loads(response.get('body', '{}'))
        )
        
    except Exception as e:
        logger.error(f"Slack events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/slack/interactive")
async def slack_interactive(request: Request):
    """Handle Slack interactive components via HTTP."""
    try:
        # Get request body
        body = await request.body()
        headers = dict(request.headers)
        
        # Create Lambda-style event
        lambda_event = {
            'body': body.decode('utf-8'),
            'headers': headers,
            'httpMethod': 'POST',
            'path': '/slack/interactive',
            'queryStringParameters': dict(request.query_params) or None,
            'isBase64Encoded': False
        }
        
        # Process with Lambda handler
        response = lambda_handler(lambda_event, None)
        
        return JSONResponse(
            status_code=response.get('statusCode', 200),
            content=json.loads(response.get('body', '{}'))
        )
        
    except Exception as e:
        logger.error(f"Slack interactive error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/slack/commands")
async def slack_commands(request: Request):
    """Handle Slack slash commands via HTTP."""
    try:
        # Get request body
        body = await request.body()
        headers = dict(request.headers)
        
        # Create Lambda-style event
        lambda_event = {
            'body': body.decode('utf-8'),
            'headers': headers,
            'httpMethod': 'POST',
            'path': '/slack/commands',
            'queryStringParameters': dict(request.query_params) or None,
            'isBase64Encoded': False
        }
        
        # Process with Lambda handler
        response = lambda_handler(lambda_event, None)
        
        return JSONResponse(
            status_code=response.get('statusCode', 200),
            content=json.loads(response.get('body', '{}'))
        )
        
    except Exception as e:
        logger.error(f"Slack commands error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_socket_mode():
    """Run the app in Socket Mode for development."""
    try:
        if not config.slack.app_token:
            logger.error("SLACK_APP_TOKEN is required for Socket Mode")
            return
        
        logger.info("Starting Slack app in Socket Mode...")
        handler = SocketModeHandler(slack_app, config.slack.app_token)
        handler.start()
        
    except Exception as e:
        logger.error(f"Socket Mode error: {e}")
        raise

def run_http_server(host: str = "0.0.0.0", port: int = 3000):
    """Run the app as HTTP server for development."""
    try:
        logger.info(f"Starting HTTP server on {host}:{port}...")
        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            log_level="info",
            reload=config.debug_mode
        )
        
    except Exception as e:
        logger.error(f"HTTP server error: {e}")
        raise

def main():
    """Main entry point for local development."""
    try:
        # Validate environment
        if not validate_environment():
            logger.error("Environment validation failed. Please check your configuration.")
            return
        
        logger.info(f"Starting Jain Global Slack Trading Bot v{config.app_version}")
        logger.info(f"Environment: {config.environment.value}")
        logger.info(f"Debug mode: {config.debug_mode}")
        
        # Choose run mode based on configuration
        if config.slack.app_token and config.environment.value == "development":
            # Use Socket Mode for development if app token is available
            run_socket_mode()
        else:
            # Use HTTP server mode
            port = int(os.getenv('PORT', 3000))
            run_http_server(port=port)
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()

# Export for ASGI servers
app = fastapi_app