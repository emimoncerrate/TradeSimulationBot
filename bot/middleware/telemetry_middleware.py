from botbuilder.core import Middleware, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging
import json
from datetime import datetime

class TelemetryMiddleware(Middleware):
    def __init__(self, instrumentation_key: str):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(
            AzureLogHandler(
                connection_string=f"InstrumentationKey={instrumentation_key}"
            )
        )
        self.logger.setLevel(logging.INFO)

    async def on_turn(self, turn_context: TurnContext, next):
        """Log telemetry data for the turn."""
        start_time = datetime.utcnow()
        
        # Create the event data
        event_data = {
            "activity_id": turn_context.activity.id,
            "activity_type": turn_context.activity.type,
            "channel_id": turn_context.activity.channel_id,
            "user_id": turn_context.activity.from_property.id,
            "tenant_id": turn_context.activity.conversation.tenant_id,
            "timestamp": start_time.isoformat(),
        }
        
        if turn_context.activity.type == ActivityTypes.message:
            event_data["text"] = turn_context.activity.text
            
        try:
            # Process the turn
            await next()
            
            # Add completion time and success status
            event_data["duration_ms"] = (datetime.utcnow() - start_time).total_seconds() * 1000
            event_data["success"] = True
            
        except Exception as e:
            # Log any errors
            event_data["duration_ms"] = (datetime.utcnow() - start_time).total_seconds() * 1000
            event_data["success"] = False
            event_data["error"] = str(e)
            raise
        
        finally:
            # Log the event
            self.logger.info("Bot Turn", extra={"custom_dimensions": event_data})
