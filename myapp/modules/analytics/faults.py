"""
Analytics Module — Fault Definitions
"""

from aquilia.faults import (
    Fault,
    FaultDomain,
    Severity,
)


ANALYTICS_DOMAIN = FaultDomain(
    name="analytics",
    description="Analytics and ML/recommendation fault domain",
)


class AnalyticsQueryFault(Fault):
    domain = ANALYTICS_DOMAIN
    severity = Severity.ERROR
    code = "ANALYTICS_QUERY_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Analytics query failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class InvalidDateRangeFault(Fault):
    domain = ANALYTICS_DOMAIN
    severity = Severity.WARN
    code = "INVALID_DATE_RANGE"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Invalid date range for analytics query"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class ModelInferenceFault(Fault):
    domain = ANALYTICS_DOMAIN
    severity = Severity.ERROR
    code = "MODEL_INFERENCE_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "ML model inference failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class RecommendationFault(Fault):
    domain = ANALYTICS_DOMAIN
    severity = Severity.WARN
    code = "RECOMMENDATION_UNAVAILABLE"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Recommendation engine unavailable"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)


class DataExportFault(Fault):
    domain = ANALYTICS_DOMAIN
    severity = Severity.ERROR
    code = "DATA_EXPORT_FAILED"

    def __init__(self, detail: str = ""):
        msg = detail if detail else "Data export failed"
        super().__init__(code=self.code, message=msg, domain=self.domain,
                         severity=self.severity, public=True)
