
"""
Advanced Dependency Injection usage in Aquilia.

This module demonstrates production-grade patterns:
1. Interface Binding (Dependency Inversion)
2. Tagged Dependencies (Multiple implementations)
3. Async Lifecycle Hooks
4. Factory Providers
5. Explicit Scope Management
"""

from typing import Protocol, Annotated, List, Dict
import asyncio
from aquilia.di import inject, service, factory
from aquilia.controller import Controller, GET, POST, RequestCtx

# --- 1. Interface Definition (Domain Layer) ---
class IUserRepository(Protocol):
    async def get_user(self, user_id: int) -> Dict: ...
    async def save_user(self, user: Dict) -> None: ...

# --- 2. Concrete Implementations (Infrastructure Layer) ---

@service(scope="singleton", tag="memory")
class MemoryUserRepository:
    """In-memory implementation for testing/dev."""
    def __init__(self):
        self._store = {1: {"id": 1, "name": "Test User"}}
        
    async def get_user(self, user_id: int) -> Dict:
        return self._store.get(user_id)
        
    async def save_user(self, user: Dict) -> None:
        self._store[user["id"]] = user

@service(scope="singleton", tag="sql")
class SqlUserRepository:
    """Production SQL implementation."""
    
    # Lifecycle: Async initialization
    async def async_init(self) -> None:
        print("🔌 Connecting to SQL Database...")
        await asyncio.sleep(0.1) # Simulate connection
        self.connected = True
        
    # Lifecycle: Cleanup
    async def shutdown(self) -> None:
        print("🔌 Closing SQL Connection...")
        self.connected = False

    async def get_user(self, user_id: int) -> Dict:
        if not getattr(self, "connected", False):
            raise RuntimeError("DB not connected")
        return {"id": user_id, "name": "SQL User"}
        
    async def save_user(self, user: Dict) -> None:
        print(f"SQL INSERT: {user}")

# --- 3. Factory Provider ---

@factory(scope="singleton", name="db_config")
def create_db_config() -> Dict[str, str]:
    return {"host": "localhost", "port": "5432"}

# --- 4. Advanced Controller Usage ---

class AdvancedUserController(Controller):
    prefix = "/advanced/users"
    
    def __init__(
        self, 
        # Interface Injection: The specific impl is bound in startup
        repo: IUserRepository, 
        
        # Tagged Injection: Explicitly requesting the 'memory' version
        cache: Annotated[IUserRepository, inject(tag="memory")],
        
        # Injected Configuration from Factory
        config: Annotated[Dict, inject(token="db_config")]
    ):
        self.repo = repo
        self.cache = cache
        self.config = config
    
    @GET("/{id}")
    async def get_user(self, ctx, id: int) -> dict:
        # Try cache first
        cached = await self.cache.get_user(id)
        if cached:
            return {"source": "memory_cache", "data": cached}
            
        # Fallback to main repo
        user = await self.repo.get_user(id)
        if user:
            # Write-through cache
            await self.cache.save_user(user)
            return {"source": "primary_db", "data": user}
            
        return {"error": "User not found"}

    @GET("/config")
    async def debug_config(self, ctx) -> dict:
        return self.config

# --- 5. Setup / Wiring (Usually in app startup) ---
# This function shows how you would wire this up in your main server startup
async def setup_advanced_di(container):
    from aquilia.di import ClassProvider, FactoryProvider
    
    # Bind Interface -> Concrete Implementation
    # This allows swapping SqlUserRepository with MemoryUserRepository locally
    # without changing the controller code.
    container.bind(IUserRepository, SqlUserRepository)
    
    # Register the Memory version explicitly with a tag
    # (The @service decorator handles this usually, but explicit registration is also possible)
    # container.register(ClassProvider(MemoryUserRepository, tags=("memory",)))
    
    # Factories are registered automatically if imported by the Registry,
    # or manually:
    # container.register(FactoryProvider(create_db_config))
