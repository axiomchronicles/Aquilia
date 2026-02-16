"""
Explainability hooks — SHAP & LIME wrappers with a unified interface.

These helpers are intentionally *thin*: they normalise inputs / outputs so
the rest of the platform never depends on a specific XAI library.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger("aquilia.mlops.explain")


# ── types ────────────────────────────────────────────────────────────────

class ExplainMethod(str, Enum):
    SHAP_KERNEL = "shap_kernel"
    SHAP_TREE = "shap_tree"
    SHAP_DEEP = "shap_deep"
    LIME_TABULAR = "lime_tabular"
    LIME_TEXT = "lime_text"
    LIME_IMAGE = "lime_image"


@dataclass(frozen=True)
class FeatureAttribution:
    """Single feature's contribution."""
    name: str
    value: float          # attribution score
    base_value: float     # model baseline (expected value)


@dataclass(frozen=True)
class Explanation:
    """Complete explanation for one prediction."""
    method: ExplainMethod
    attributions: List[FeatureAttribution]
    prediction: Any = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def top_k(self) -> List[FeatureAttribution]:
        """Top 10 features by absolute attribution."""
        return sorted(self.attributions, key=lambda a: abs(a.value), reverse=True)[:10]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "prediction": self.prediction,
            "attributions": [
                {"name": a.name, "value": a.value, "base_value": a.base_value}
                for a in self.attributions
            ],
            "top_k": [
                {"name": a.name, "value": a.value, "base_value": a.base_value}
                for a in self.top_k
            ],
            **self.extra,
        }


# ── SHAP wrapper ─────────────────────────────────────────────────────────

class SHAPExplainer:
    """
    Wraps ``shap.KernelExplainer``, ``shap.TreeExplainer`` or
    ``shap.DeepExplainer`` behind a single ``explain()`` call.
    """

    def __init__(
        self,
        predict_fn: Callable,
        background_data: Any,
        method: ExplainMethod = ExplainMethod.SHAP_KERNEL,
        feature_names: Optional[Sequence[str]] = None,
    ):
        try:
            import shap  # noqa: F811
        except ImportError:
            raise ImportError(
                "SHAP is required for SHAPExplainer.  "
                "Install it with: pip install shap"
            )

        self._feature_names = list(feature_names) if feature_names else None
        self._method = method

        if method == ExplainMethod.SHAP_KERNEL:
            self._explainer = shap.KernelExplainer(predict_fn, background_data)
        elif method == ExplainMethod.SHAP_TREE:
            self._explainer = shap.TreeExplainer(predict_fn)
        elif method == ExplainMethod.SHAP_DEEP:
            self._explainer = shap.DeepExplainer(predict_fn, background_data)
        else:
            raise ValueError(f"Unsupported SHAP method: {method}")

    def explain(self, instance: Any, **kwargs: Any) -> Explanation:
        """Compute SHAP values for *instance* (single row)."""
        arr = np.asarray(instance)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        shap_values = self._explainer.shap_values(arr, **kwargs)

        # shap_values may be list (multi-output) — take first class
        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        vals = shap_values[0]  # first (only) row
        base = float(
            self._explainer.expected_value
            if isinstance(self._explainer.expected_value, (int, float))
            else self._explainer.expected_value[0]
        )
        names = self._feature_names or [f"f{i}" for i in range(len(vals))]

        attributions = [
            FeatureAttribution(name=n, value=float(v), base_value=base)
            for n, v in zip(names, vals)
        ]
        return Explanation(
            method=self._method,
            attributions=attributions,
            prediction=None,
        )


# ── LIME wrapper ─────────────────────────────────────────────────────────

class LIMEExplainer:
    """
    Wraps ``lime.lime_tabular.LimeTabularExplainer`` (default) or
    ``lime.lime_text.LimeTextExplainer`` behind a single ``explain()`` call.
    """

    def __init__(
        self,
        training_data: Any,
        predict_fn: Callable,
        method: ExplainMethod = ExplainMethod.LIME_TABULAR,
        feature_names: Optional[Sequence[str]] = None,
        class_names: Optional[Sequence[str]] = None,
        num_features: int = 10,
    ):
        self._predict_fn = predict_fn
        self._method = method
        self._num_features = num_features

        if method == ExplainMethod.LIME_TABULAR:
            try:
                from lime.lime_tabular import LimeTabularExplainer
            except ImportError:
                raise ImportError(
                    "LIME is required for LIMEExplainer.  "
                    "Install it with: pip install lime"
                )
            self._explainer = LimeTabularExplainer(
                np.asarray(training_data),
                feature_names=list(feature_names) if feature_names else None,
                class_names=list(class_names) if class_names else None,
                mode="classification",
            )
        elif method == ExplainMethod.LIME_TEXT:
            try:
                from lime.lime_text import LimeTextExplainer
            except ImportError:
                raise ImportError(
                    "LIME is required for LIMEExplainer.  "
                    "Install it with: pip install lime"
                )
            self._explainer = LimeTextExplainer(
                class_names=list(class_names) if class_names else None,
            )
        else:
            raise ValueError(f"Unsupported LIME method: {method}")

        self._feature_names = list(feature_names) if feature_names else None

    def explain(self, instance: Any, **kwargs: Any) -> Explanation:
        """Explain a single instance."""
        if self._method == ExplainMethod.LIME_TABULAR:
            return self._explain_tabular(instance, **kwargs)
        return self._explain_text(instance, **kwargs)

    def _explain_tabular(self, instance: Any, **kwargs: Any) -> Explanation:
        arr = np.asarray(instance).ravel()
        exp = self._explainer.explain_instance(
            arr, self._predict_fn, num_features=self._num_features, **kwargs
        )
        pairs = exp.as_list()
        attributions = [
            FeatureAttribution(name=str(name), value=float(weight), base_value=0.0)
            for name, weight in pairs
        ]
        return Explanation(
            method=self._method,
            attributions=attributions,
            prediction=None,
        )

    def _explain_text(self, instance: str, **kwargs: Any) -> Explanation:
        exp = self._explainer.explain_instance(
            instance, self._predict_fn, num_features=self._num_features, **kwargs
        )
        pairs = exp.as_list()
        attributions = [
            FeatureAttribution(name=str(name), value=float(weight), base_value=0.0)
            for name, weight in pairs
        ]
        return Explanation(
            method=self._method,
            attributions=attributions,
            prediction=None,
        )


# ── Unified factory ──────────────────────────────────────────────────────

def create_explainer(
    method: ExplainMethod,
    predict_fn: Callable,
    data: Any,
    feature_names: Optional[Sequence[str]] = None,
    **kwargs: Any,
) -> SHAPExplainer | LIMEExplainer:
    """
    Factory that returns the right explainer for the requested method.

    Parameters
    ----------
    method : ExplainMethod
    predict_fn : callable accepted by the underlying library
    data : background data (SHAP) or training data (LIME)
    feature_names : optional list of feature names
    """
    if method.name.startswith("SHAP"):
        return SHAPExplainer(
            predict_fn=predict_fn,
            background_data=data,
            method=method,
            feature_names=feature_names,
            **kwargs,
        )
    return LIMEExplainer(
        training_data=data,
        predict_fn=predict_fn,
        method=method,
        feature_names=feature_names,
        **kwargs,
    )
