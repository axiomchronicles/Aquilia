"""
Orders Module — Fault Definitions
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
)


ORDERS_DOMAIN = FaultDomain(
    name="orders",
    description="Order processing fault domain",
)


class OrderNotFoundFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.WARN
    code = "ORDER_NOT_FOUND"

    def __init__(self, order_number: str = ""):
        msg = f"Order '{order_number}' does not exist." if order_number else "Order not found"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class EmptyCartFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.WARN
    code = "EMPTY_CART"

    def __init__(self):
        super().__init__(code=self.code, message="Cannot place order with an empty cart",
                         domain=self.domain, severity=self.severity, public=True)


class InvalidOrderTransitionFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.ERROR
    code = "INVALID_ORDER_TRANSITION"

    def __init__(self, from_status: str = "", to_status: str = ""):
        if from_status and to_status:
            msg = f"Cannot transition order from '{from_status}' to '{to_status}'."
        else:
            msg = "Invalid order status transition"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class PaymentFailedFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.ERROR
    code = "PAYMENT_FAILED"

    def __init__(self, reason: str = ""):
        msg = f"Payment failed: {reason}" if reason else "Payment processing failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class OrderCancellationFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.WARN
    code = "ORDER_CANCELLATION_FAILED"

    def __init__(self):
        super().__init__(code=self.code, message="Order cannot be cancelled in its current state",
                         domain=self.domain, severity=self.severity, public=True)


class RefundFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.ERROR
    code = "REFUND_FAILED"

    def __init__(self, reason: str = ""):
        msg = f"Refund failed: {reason}" if reason else "Refund processing failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class OrderLimitExceededFault(Fault):
    domain = ORDERS_DOMAIN
    severity = Severity.WARN
    code = "ORDER_LIMIT_EXCEEDED"

    def __init__(self):
        super().__init__(code=self.code, message="Order rate limit exceeded",
                         domain=self.domain, severity=self.severity, public=True)
