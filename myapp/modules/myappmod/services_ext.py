
from typing import Annotated, Protocol
from aquilia.di import service, inject

# --- 1. Request Context (Scoped Data) ---
# A simplified user identity object
class UserIdentity:
    def __init__(self, uid: int, role: str):
        self.uid = uid
        self.role = role

# --- 2. Request-Scoped Service with Deep Injection ---
@service(scope="request")
class AuditLogger:
    """
    Service that depends on the current UserIdentity.
    Since UserIdentity is request-scoped (provided by middleware),
    this service must also be request-scoped.
    """
    def __init__(self, user: UserIdentity):
        self.user = user

    def log_action(self, action: str) -> str:
        return f"[AUDIT] User {self.user.uid} ({self.user.role}) performed: {action}"

# --- 3. Interface for complex processing ---
class IProcessor(Protocol):
    async def process(self, data: str) -> str: ...

# --- 4. Lazy Injection Example ---
@service(scope="singleton")
class ExpensiveService:
    def __init__(self):
        print("ExpensiveService initialized (simulated delay)")
    
    def calculate(self) -> int:
        return 42

@service(scope="singleton")
class LazyProcessor:
    """
    Demonstrates using a Lazy Proxy.
    The expensive service is NOT instantiated until `process` is actually called.
    """
    def __init__(self, expensive: Annotated[ExpensiveService, inject(optional=False)]):
        # NOTE: In a real lazy scenario, the proxy wrapping usually happens at the container level
        # if configured. Here we simulate it or rely on the container's lazy support if enabled.
        self.expensive = expensive

    async def process(self, data: str) -> str:
        # Accessing self.expensive triggers instantiation if it was lazy
        result = self.expensive.calculate()
        return f"Processed '{data}' with Factor {result}"
