from botbuilder.core import Middleware, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from services.auth import AuthService

class AuthenticationMiddleware(Middleware):
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    async def on_turn(self, turn_context: TurnContext, next):
        """Authenticate the user before processing the turn."""
        if turn_context.activity.type == ActivityTypes.message:
            # Get user ID from Teams context
            user_id = turn_context.activity.from_property.aad_object_id
            
            if not user_id:
                await turn_context.send_activity(
                    "Authentication failed. Please ensure you're signed in to Teams."
                )
                return
            
            # Validate user access
            try:
                user = await self.auth_service.validate_user(user_id)
                if not user:
                    await turn_context.send_activity(
                        "You don't have access to this bot. Please contact your administrator."
                    )
                    return
                    
                # Add user to turn state
                turn_context.turn_state["user"] = user
                
            except Exception as e:
                await turn_context.send_activity(
                    f"An error occurred during authentication: {str(e)}"
                )
                return
        
        await next()
