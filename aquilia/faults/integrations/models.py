"""
AquilaFaults - Model/Database Integration.

Integration module for connecting AquilaFaults with the AMDL model system:
- Parser error wrapping
- Database connection fault handling
- Query fault interception
- Migration fault handling
- Model discovery fault reporting

Usage:
    ```python
    from aquilia.faults.integrations.models import (
        patch_model_registry,
        create_model_fault_handler,
    )
    
    patch_model_registry()
    engine.register_global(create_model_fault_handler())
    ```
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..core import (
    Fault,
    FaultContext,
    FaultDomain,
    FaultResult,
    Resolved,
    Severity,
    Transformed,
)
from ..domains import (
    AMDLParseFault,
    DatabaseConnectionFault,
    MigrationFault,
    ModelFault,
    ModelNotFoundFault,
    ModelRegistrationFault,
    QueryFault,
    SchemaFault,
)
from ..handlers import FaultHandler

logger = logging.getLogger("aquilia.faults.integrations.models")


# ============================================================================
# Fault Handler
# ============================================================================

class ModelFaultHandler(FaultHandler):
    """
    Fault handler for MODEL domain faults.
    
    Handles:
    - AMDL parse errors → logged + abort startup
    - Database connection failures → retry with backoff
    - Query failures → logged + optional retry
    - Migration failures → abort with diagnostics
    - Schema faults → abort with table info
    """
    
    def __init__(self, max_retries: int = 3, log_queries: bool = True):
        self._max_retries = max_retries
        self._log_queries = log_queries
    
    def can_handle(self, ctx: FaultContext) -> bool:
        """Check if this handler can handle the fault."""
        return ctx.fault.domain == FaultDomain.MODEL
    
    def handle(self, ctx: FaultContext) -> FaultResult:
        """Handle a model domain fault."""
        fault = ctx.fault
        
        # Log all model faults
        logger.error(
            f"[{fault.code}] {fault.message} "
            f"(app={ctx.app}, trace={ctx.trace_id})"
        )
        
        # Database connection failures: attempt retry
        if isinstance(fault, DatabaseConnectionFault) and fault.retryable:
            retry_count = fault.metadata.get("_retry_count", 0)
            if retry_count < self._max_retries:
                fault.metadata["_retry_count"] = retry_count + 1
                logger.info(
                    f"Retrying database connection (attempt {retry_count + 1}/{self._max_retries})"
                )
                return Transformed(fault, preserve_context=True)
        
        # Query failures: log details if enabled
        if isinstance(fault, QueryFault) and self._log_queries:
            logger.debug(
                f"Failed query on model={fault.metadata.get('model')}, "
                f"op={fault.metadata.get('operation')}"
            )
        
        # Parse errors and schema faults are fatal — escalate
        if isinstance(fault, (AMDLParseFault, SchemaFault)):
            logger.critical(
                f"Fatal model fault: {fault.message}"
            )
        
        # Migration faults: log migration name
        if isinstance(fault, MigrationFault):
            logger.error(
                f"Migration '{fault.metadata.get('migration')}' failed: "
                f"{fault.metadata.get('reason')}"
            )
        
        # Default: escalate to next handler
        from ..core import Escalate
        return Escalate()


def create_model_fault_handler(
    max_retries: int = 3,
    log_queries: bool = True,
) -> ModelFaultHandler:
    """
    Create a fault handler for the MODEL domain.
    
    Args:
        max_retries: Max retry attempts for retryable faults
        log_queries: Whether to log query details on failure
    
    Returns:
        ModelFaultHandler instance
    """
    return ModelFaultHandler(
        max_retries=max_retries,
        log_queries=log_queries,
    )


# ============================================================================
# Patch Functions
# ============================================================================

def patch_model_registry() -> None:
    """
    Patch ModelRegistry to raise structured faults instead of bare exceptions.
    
    Wraps:
    - ModelRegistry.register_model() → ModelRegistrationFault
    - ModelRegistry.get_proxy() → ModelNotFoundFault
    - ModelRegistry.create_tables() → SchemaFault
    """
    try:
        from aquilia.models.runtime import ModelRegistry
    except ImportError:
        logger.debug("ModelRegistry not available — skipping patch")
        return
    
    _original_register = ModelRegistry.register_model
    _original_get_proxy = ModelRegistry.get_proxy
    _original_create_tables = ModelRegistry.create_tables
    
    def _patched_register(self, model_node, *args, **kwargs):
        try:
            return _original_register(self, model_node, *args, **kwargs)
        except Exception as e:
            raise ModelRegistrationFault(
                model_name=getattr(model_node, "name", "unknown"),
                reason=str(e),
            ) from e
    
    def _patched_get_proxy(self, name):
        try:
            return _original_get_proxy(self, name)
        except (KeyError, LookupError) as e:
            raise ModelNotFoundFault(model_name=name) from e
    
    async def _patched_create_tables(self):
        try:
            return await _original_create_tables(self)
        except Exception as e:
            raise SchemaFault(
                table="(multiple)",
                reason=str(e),
            ) from e
    
    ModelRegistry.register_model = _patched_register
    ModelRegistry.get_proxy = _patched_get_proxy
    ModelRegistry.create_tables = _patched_create_tables
    
    logger.debug("Patched ModelRegistry with fault integration")


def patch_database_engine() -> None:
    """
    Patch AquiliaDatabase to raise structured faults on connection errors.
    """
    try:
        from aquilia.db.engine import AquiliaDatabase
    except ImportError:
        logger.debug("AquiliaDatabase not available — skipping patch")
        return
    
    _original_connect = AquiliaDatabase.connect
    
    async def _patched_connect(self):
        try:
            return await _original_connect(self)
        except Exception as e:
            raise DatabaseConnectionFault(
                url=self._url,
                reason=str(e),
            ) from e
    
    AquiliaDatabase.connect = _patched_connect
    
    logger.debug("Patched AquiliaDatabase with fault integration")


def patch_all_model_subsystems() -> None:
    """Patch all model-related subsystems with fault integration."""
    patch_model_registry()
    patch_database_engine()
