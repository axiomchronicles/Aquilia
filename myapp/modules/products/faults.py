"""
Products Module — Fault Definitions
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
)


PRODUCTS_DOMAIN = FaultDomain(
    name="products",
    description="Product catalog fault domain",
)


class ProductNotFoundFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.WARN
    code = "PRODUCT_NOT_FOUND"

    def __init__(self, identifier: str = ""):
        msg = f"Product '{identifier}' does not exist." if identifier else "Product not found"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class CategoryNotFoundFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.WARN
    code = "CATEGORY_NOT_FOUND"

    def __init__(self, identifier: str = ""):
        msg = f"Category '{identifier}' not found." if identifier else "Category not found"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class DuplicateSkuFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.WARN
    code = "DUPLICATE_SKU"

    def __init__(self, sku: str = ""):
        msg = f"Product SKU '{sku}' already exists." if sku else "SKU already exists"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class InsufficientStockFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.ERROR
    code = "INSUFFICIENT_STOCK"

    def __init__(self, product_name: str = "", available: int = 0, requested: int = 0):
        if product_name:
            msg = f"'{product_name}' has {available} units available, {requested} requested."
        else:
            msg = "Insufficient stock"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity,
                         metadata={"available": available, "requested": requested},
                         public=True)


class ProductValidationFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.WARN
    code = "PRODUCT_VALIDATION_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Product validation failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class InvalidPriceFault(Fault):
    domain = PRODUCTS_DOMAIN
    severity = Severity.WARN
    code = "INVALID_PRICE"

    def __init__(self):
        super().__init__(code=self.code, message="Product price must be greater than zero",
                         domain=self.domain, severity=self.severity, public=True)
