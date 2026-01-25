from aquilia import Controller, GET, POST


class SessionController(Controller):

    prefix = "/sessions"
    
    @GET("/session")
    async def get_session(self):
        return {"message": "Hello World"}

    @POST("/session")
    async def create_session(self):
        return {"message": "Hello World"}