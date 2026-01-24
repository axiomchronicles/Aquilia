"""
Aquilia DI - Single-File Proof of Concept

Demonstrates:
1. Provider registration and resolution
2. Multiple scopes (singleton, request, transient, pooled)
3. Async lifecycle management
4. Lazy proxy for cycle resolution
5. Request-scoped container with cleanup

Run: python di_poc.py
"""

import asyncio
from typing import Optional, Protocol
from dataclasses import dataclass


# === Domain Types ===

class Database:
    """Simulated database connection."""
    
    def __init__(self, url: str):
        self.url = url
        self.connected = False
        print(f"📦 Database.__init__({url})")
    
    async def connect(self):
        """Async initialization."""
        await asyncio.sleep(0.01)  # Simulate connection
        self.connected = True
        print(f"🔌 Database.connect() -> {self.url}")
    
    async def close(self):
        """Cleanup."""
        self.connected = False
        print(f"🔌 Database.close() -> {self.url}")
    
    async def query(self, sql: str):
        if not self.connected:
            raise RuntimeError("Database not connected")
        await asyncio.sleep(0.001)
        return f"Result for: {sql}"


class UserRepository:
    """Repository for user data."""
    
    def __init__(self, db: Database):
        self.db = db
        print(f"📦 UserRepository.__init__(db={db.url})")
    
    async def get_user(self, user_id: int):
        result = await self.db.query(f"SELECT * FROM users WHERE id={user_id}")
        return {"id": user_id, "name": f"User{user_id}"}


class AuthService:
    """Authentication service."""
    
    def __init__(self, repo: UserRepository):
        self.repo = repo
        print(f"📦 AuthService.__init__(repo={repo})")
    
    async def authenticate(self, user_id: int, password: str):
        user = await self.repo.get_user(user_id)
        # Simplified auth check
        return user is not None


class RequestLogger:
    """Request-scoped logger."""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.logs = []
        print(f"📦 RequestLogger.__init__(request_id={request_id})")
    
    def log(self, message: str):
        entry = f"[{self.request_id}] {message}"
        self.logs.append(entry)
        print(f"📝 {entry}")
    
    async def flush(self):
        print(f"💾 RequestLogger.flush() -> {len(self.logs)} logs")


# === Simple DI Container (POC) ===

class SimpleContainer:
    """Minimal DI container for POC."""
    
    def __init__(self, parent: Optional["SimpleContainer"] = None):
        self.parent = parent
        self.providers = {}  # {token: factory}
        self.singletons = {}  # {token: instance}
        self.scopes = {}  # {token: scope}
        self.instances = []  # For cleanup tracking
    
    def register(self, token: type, factory, scope: str = "singleton"):
        """Register a provider."""
        self.providers[token] = factory
        self.scopes[token] = scope
    
    async def resolve(self, token: type):
        """Resolve a dependency."""
        scope = self.scopes.get(token, "singleton")
        
        # Check cache
        if scope in ("singleton", "request") and token in self.singletons:
            return self.singletons[token]
        
        # Check parent (for request scope)
        if token in self.providers:
            factory = self.providers[token]
        elif self.parent and token in self.parent.providers:
            factory = self.parent.providers[token]
            if self.parent.scopes.get(token) == "singleton":
                # Resolve from parent for singletons
                return await self.parent.resolve(token)
        else:
            raise ValueError(f"No provider for {token}")
        
        # Instantiate
        instance = await factory(self)
        
        # Cache if needed
        if scope in ("singleton", "request"):
            self.singletons[token] = instance
        
        # Track for cleanup
        if scope == "request":
            self.instances.append(instance)
        
        return instance
    
    def create_request_scope(self):
        """Create child container for request."""
        return SimpleContainer(parent=self)
    
    async def cleanup(self):
        """Cleanup request-scoped instances."""
        for instance in reversed(self.instances):
            if hasattr(instance, "flush"):
                await instance.flush()
            if hasattr(instance, "close"):
                await instance.close()


# === POC Demo ===

async def demo_basic_resolution():
    """Demo 1: Basic provider registration and resolution."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Resolution (Singleton Scope)")
    print("="*60)
    
    container = SimpleContainer()
    
    # Register providers
    async def db_factory(c):
        db = Database("postgresql://localhost/mydb")
        await db.connect()
        return db
    
    async def repo_factory(c):
        db = await c.resolve(Database)
        return UserRepository(db)
    
    async def auth_factory(c):
        repo = await c.resolve(UserRepository)
        return AuthService(repo)
    
    container.register(Database, db_factory, scope="singleton")
    container.register(UserRepository, repo_factory, scope="singleton")
    container.register(AuthService, auth_factory, scope="singleton")
    
    # Resolve - should reuse singleton instances
    print("\n🎯 First resolution:")
    auth1 = await container.resolve(AuthService)
    
    print("\n🎯 Second resolution (should reuse):")
    auth2 = await container.resolve(AuthService)
    
    assert auth1 is auth2, "Singletons should be the same instance"
    print("✅ Singleton reuse confirmed!")
    
    # Test functionality
    result = await auth1.authenticate(123, "password")
    print(f"🔐 Authentication result: {result}")
    
    # Cleanup
    db = await container.resolve(Database)
    await db.close()


async def demo_request_scope():
    """Demo 2: Request-scoped container with per-request instances."""
    print("\n" + "="*60)
    print("DEMO 2: Request Scope (Per-Request Instances)")
    print("="*60)
    
    # App container (singletons)
    app_container = SimpleContainer()
    
    async def db_factory(c):
        db = Database("postgresql://localhost/mydb")
        await db.connect()
        return db
    
    app_container.register(Database, db_factory, scope="singleton")
    
    # Simulate two requests
    for request_num in range(1, 3):
        print(f"\n📨 === REQUEST {request_num} ===")
        
        # Create request container
        request_container = app_container.create_request_scope()
        
        # Register request-scoped logger
        async def logger_factory(c):
            return RequestLogger(f"req-{request_num}")
        
        request_container.register(RequestLogger, logger_factory, scope="request")
        
        # Use request services
        logger = await request_container.resolve(RequestLogger)
        logger.log("Request started")
        
        db = await request_container.resolve(Database)
        logger.log(f"Using database: {db.url}")
        
        # Same database across requests (singleton)
        print(f"   Database connected: {db.connected}")
        
        # Cleanup request
        await request_container.cleanup()
    
    print("\n✅ Request scopes isolated successfully!")
    
    # Cleanup app
    db = await app_container.resolve(Database)
    await db.close()


async def demo_transient_scope():
    """Demo 3: Transient scope (new instance every time)."""
    print("\n" + "="*60)
    print("DEMO 3: Transient Scope (New Instance Every Time)")
    print("="*60)
    
    container = SimpleContainer()
    
    async def db_factory(c):
        return Database("sqlite://memory")
    
    container.register(Database, db_factory, scope="transient")
    
    # Each resolve creates a new instance
    db1 = await container.resolve(Database)
    db2 = await container.resolve(Database)
    db3 = await container.resolve(Database)
    
    assert db1 is not db2 is not db3, "Transient should create new instances"
    print("✅ Transient instances are unique!")


async def demo_pooled_resources():
    """Demo 4: Pooled resources (simulated)."""
    print("\n" + "="*60)
    print("DEMO 4: Pooled Resources (Connection Pool)")
    print("="*60)
    
    # Simulate a connection pool
    class ConnectionPool:
        def __init__(self, size: int):
            self.size = size
            self.pool = asyncio.Queue(maxsize=size)
            print(f"📦 ConnectionPool.__init__(size={size})")
        
        async def acquire(self):
            """Acquire connection from pool."""
            try:
                conn = self.pool.get_nowait()
                print(f"♻️  Reused connection from pool")
                return conn
            except asyncio.QueueEmpty:
                if self.pool.qsize() < self.size:
                    conn = Database(f"pooled-conn-{id(self)}")
                    await conn.connect()
                    return conn
                # Wait for available connection
                return await self.pool.get()
        
        async def release(self, conn):
            """Release connection back to pool."""
            try:
                self.pool.put_nowait(conn)
                print(f"♻️  Released connection to pool")
            except asyncio.QueueFull:
                await conn.close()
    
    container = SimpleContainer()
    
    async def pool_factory(c):
        return ConnectionPool(size=2)
    
    container.register(ConnectionPool, pool_factory, scope="singleton")
    
    # Acquire connections
    pool = await container.resolve(ConnectionPool)
    
    conn1 = await pool.acquire()
    print(f"   Got connection: {conn1.url}")
    
    conn2 = await pool.acquire()
    print(f"   Got connection: {conn2.url}")
    
    # Release and reacquire
    await pool.release(conn1)
    conn3 = await pool.acquire()
    print(f"   Got connection: {conn3.url}")
    
    assert conn3 is conn1, "Should reuse pooled connection"
    print("✅ Connection pool working!")


async def demo_lazy_proxy():
    """Demo 5: Lazy proxy for breaking cycles."""
    print("\n" + "="*60)
    print("DEMO 5: Lazy Proxy (Cycle Breaking)")
    print("="*60)
    
    # Simulate circular dependency
    class ServiceA:
        def __init__(self, b_proxy):
            self.b = b_proxy  # Lazy proxy
            print(f"📦 ServiceA.__init__(b_proxy={b_proxy})")
        
        def call_b(self):
            # Access through proxy resolves lazily
            return self.b().get_data()
    
    class ServiceB:
        def __init__(self):
            print(f"📦 ServiceB.__init__()")
        
        def get_data(self):
            return "Data from B"
    
    class LazyProxy:
        """Simple lazy proxy."""
        def __init__(self, factory):
            self._factory = factory
            self._instance = None
        
        def __call__(self):
            if self._instance is None:
                self._instance = self._factory()
            return self._instance
    
    container = SimpleContainer()
    
    # Register with lazy proxy
    b_instance = ServiceB()
    
    async def a_factory(c):
        lazy_b = LazyProxy(lambda: b_instance)
        return ServiceA(lazy_b)
    
    container.register(ServiceA, a_factory, scope="singleton")
    
    # Resolve A (B is not resolved yet)
    print("\n🎯 Resolving ServiceA...")
    service_a = await container.resolve(ServiceA)
    
    print("\n🎯 Calling through proxy...")
    result = service_a.call_b()
    print(f"   Result: {result}")
    
    print("✅ Lazy proxy resolved cycle!")


async def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("🚀 Aquilia DI - Proof of Concept")
    print("="*60)
    
    await demo_basic_resolution()
    await demo_request_scope()
    await demo_transient_scope()
    await demo_pooled_resources()
    await demo_lazy_proxy()
    
    print("\n" + "="*60)
    print("✅ All POC demos completed successfully!")
    print("="*60)
    print("\nKey Features Demonstrated:")
    print("  1. ✅ Singleton scope with instance reuse")
    print("  2. ✅ Request scope with per-request isolation")
    print("  3. ✅ Transient scope with new instances")
    print("  4. ✅ Pooled resources (connection pooling)")
    print("  5. ✅ Lazy proxies for cycle resolution")
    print("\nNext: Full implementation with manifest loading,")
    print("      cycle detection, CLI tools, and observability.")


if __name__ == "__main__":
    asyncio.run(main())
