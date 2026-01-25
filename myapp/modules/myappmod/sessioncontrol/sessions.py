from aquilia import Controller, GET, POST


class SessionController(Controller):

    prefix = "/sessions"
    
    @GET("/")
    async def get_session(self, ctx):
        return {"message": "Hello World"}

    @POST("/")
    async def create_session(self, ctx):
        return {"message": "Hello World"}