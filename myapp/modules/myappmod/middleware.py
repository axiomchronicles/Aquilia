
from aquilia.middleware import Middleware
from aquilia.di import Container
from .services_ext import UserIdentity

class AuthSimulationMiddleware(Middleware):
    """
    Simulates authentication by binding a UserIdentity to the request container.
    """
    async def __call__(self, request, ctx, next_handler):
        # 1. Simulate extracting user from header
        # In real world: jwt.decode(request.headers.get("Authorization"))
        user_id = 123
        role = "admin"
        
        # 2. Create the identity object
        identity = UserIdentity(uid=user_id, role=role)
        
        # 3. Bind it to the DI container for this request
        if ctx.container:
            print(f"DEBUG: AuthSimulationMiddleware registering UserIdentity in container {id(ctx.container)}")
            try:
                await ctx.container.register_instance(
                    UserIdentity, 
                    identity, 
                    scope="request"
                )
                print("DEBUG: Registration successful")
            except Exception as e:
                print(f"DEBUG: Registration failed: {e}")
        else:
            print("DEBUG: AuthSimulationMiddleware - No container found!")
            
        return await next_handler(request, ctx)
