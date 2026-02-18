"""
Analytics Module — Business intelligence and ML recommendations.

Components:
- Services: AnalyticsService, RecommendationService
- Controllers: AnalyticsController (with SSE), RecommendationController
- Faults: Analytics-specific error handling
"""

from .services import AnalyticsService, RecommendationService
from .controllers import AnalyticsController, RecommendationController
from .faults import (
    AnalyticsQueryFault,
    ModelInferenceFault,
    RecommendationFault,
)

__all__ = [
    "AnalyticsService", "RecommendationService",
    "AnalyticsController", "RecommendationController",
    "AnalyticsQueryFault", "ModelInferenceFault", "RecommendationFault",
]
