import asyncio
import unittest
from aquilia.controller.router import ControllerRouter
from aquilia.controller.openapi import OpenAPIGenerator
from aquilia.controller.compiler import ControllerCompiler
from aquilia.controller import GET, Controller

class TestUserController(Controller):
    prefix = "/users"
    
    @GET("/«id:int»")
    async def get_user(self, ctx, id: int):
        """Get user by ID.
        
        Detailed description here.
        """
        return {"id": id}

class TestOpenAPI(unittest.TestCase):
    def test_openapi_gen(self):
        compiler = ControllerCompiler()
        compiled = compiler.compile_controller(TestUserController)
        
        router = ControllerRouter()
        router.add_controller(compiled)
        router.initialize()
        
        generator = OpenAPIGenerator()
        spec = generator.generate(router)
        
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/users/{id}", spec["paths"])
        
        op = spec["paths"]["/users/{id}"]["get"]
        self.assertEqual(op["summary"], "Get user by ID.")
        self.assertIn("Detailed description here.", op["description"])
        
        # Check params
        params = op["parameters"]
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["name"], "id")
        self.assertEqual(params[0]["in"], "path")
        self.assertEqual(params[0]["schema"]["type"], "integer")

if __name__ == "__main__":
    unittest.main()
