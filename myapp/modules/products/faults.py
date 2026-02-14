"""
Products Module - Faults

Showcases domain-specific faults for product operations.
"""

from aquilia.faults import Fault, FaultDomain, Severity


class ProductNotFoundFault(Fault):
    def __init__(self, product_id: str):
        super().__init__(
            code="PRODUCT_NOT_FOUND",
            message=f"Product '{product_id}' not found",
            domain=FaultDomain.IO,
            severity=Severity.ERROR,
            retryable=False,
            public=True,
            status_code=404,
            metadata={"product_id": product_id},
        )


class InvalidProductDataFault(Fault):
    def __init__(self, reason: str):
        super().__init__(
            code="INVALID_PRODUCT_DATA",
            message=f"Invalid product data: {reason}",
            domain=FaultDomain.IO,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=400,
            metadata={"reason": reason},
        )


class InsufficientStockFault(Fault):
    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(
            code="INSUFFICIENT_STOCK",
            message=f"Insufficient stock for product '{product_id}'",
            domain=FaultDomain.IO,
            severity=Severity.WARN,
            retryable=False,
            public=True,
            status_code=409,
            metadata={
                "product_id": product_id,
                "requested": requested,
                "available": available,
            },
        )
