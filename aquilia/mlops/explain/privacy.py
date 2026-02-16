"""
Privacy helpers — PII redaction, differential privacy noise, and
input sanitisation transforms for inference payloads.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

logger = logging.getLogger("aquilia.mlops.explain.privacy")


# ── PII entity types ────────────────────────────────────────────────────

class PIIKind(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    CUSTOM = "custom"


@dataclass(frozen=True)
class PIIMatch:
    kind: PIIKind
    start: int
    end: int
    text: str


# ── Built-in regex patterns ─────────────────────────────────────────────

_BUILTIN_PATTERNS: Dict[PIIKind, re.Pattern] = {
    PIIKind.EMAIL: re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
    ),
    PIIKind.PHONE: re.compile(
        r"(?:\+?1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}"
    ),
    PIIKind.SSN: re.compile(r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b"),
    PIIKind.CREDIT_CARD: re.compile(
        r"\b(?:\d[ \-]*?){13,19}\b"
    ),
    PIIKind.IP_ADDRESS: re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
}


# ── PII redactor ─────────────────────────────────────────────────────────

class PIIRedactor:
    """
    Scans text for PII and replaces matches with a configurable placeholder.

    Usage
    -----
    >>> redactor = PIIRedactor()
    >>> redactor.redact("Email me at alice@example.com")
    'Email me at [EMAIL_REDACTED]'
    """

    def __init__(
        self,
        *,
        kinds: Optional[Set[PIIKind]] = None,
        placeholder_template: str = "[{kind}_REDACTED]",
        custom_patterns: Optional[Dict[str, re.Pattern]] = None,
        hash_replacement: bool = False,
    ):
        self._kinds = kinds or set(PIIKind) - {PIIKind.CUSTOM}
        self._placeholder_template = placeholder_template
        self._hash_replacement = hash_replacement
        self._patterns: Dict[PIIKind, re.Pattern] = {}

        for kind in self._kinds:
            if kind in _BUILTIN_PATTERNS:
                self._patterns[kind] = _BUILTIN_PATTERNS[kind]

        if custom_patterns:
            for name, pat in custom_patterns.items():
                self._patterns[PIIKind.CUSTOM] = pat  # last one wins (for now)
                self._kinds.add(PIIKind.CUSTOM)

    # ── public API ───────────────────────────────────────────────────────

    def scan(self, text: str) -> List[PIIMatch]:
        """Return all PII matches found in *text*."""
        matches: List[PIIMatch] = []
        for kind, pattern in self._patterns.items():
            for m in pattern.finditer(text):
                matches.append(
                    PIIMatch(kind=kind, start=m.start(), end=m.end(), text=m.group())
                )
        matches.sort(key=lambda m: m.start)
        return matches

    def redact(self, text: str) -> str:
        """Return *text* with all PII replaced."""
        result = text
        # process in reverse order so indices stay valid
        for match in reversed(self.scan(text)):
            replacement = self._replacement(match)
            result = result[: match.start] + replacement + result[match.end :]
        return result

    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact string values in a dict."""
        out: Dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(v, str):
                out[k] = self.redact(v)
            elif isinstance(v, dict):
                out[k] = self.redact_dict(v)
            elif isinstance(v, list):
                out[k] = [
                    self.redact(i) if isinstance(i, str) else i for i in v
                ]
            else:
                out[k] = v
        return out

    # ── internals ────────────────────────────────────────────────────────

    def _replacement(self, match: PIIMatch) -> str:
        if self._hash_replacement:
            h = hashlib.sha256(match.text.encode()).hexdigest()[:8]
            return f"[{match.kind.value.upper()}_HASH_{h}]"
        return self._placeholder_template.format(kind=match.kind.value.upper())


# ── Differential-privacy noise ───────────────────────────────────────────

class LaplaceNoise:
    """
    Adds calibrated Laplace noise to numeric values.

    This provides ε-differential privacy for simple numeric queries.
    """

    def __init__(self, epsilon: float = 1.0, sensitivity: float = 1.0):
        if epsilon <= 0:
            raise ValueError("epsilon must be > 0")
        self._epsilon = epsilon
        self._sensitivity = sensitivity
        self._scale = sensitivity / epsilon

    def add_noise(self, value: float) -> float:
        """Return *value* + Laplace(0, scale)."""
        u = random.random() - 0.5
        noise = -self._scale * _sign(u) * math.log(1 - 2 * abs(u))
        return value + noise

    def add_noise_array(self, values: Sequence[float]) -> List[float]:
        return [self.add_noise(v) for v in values]


def _sign(x: float) -> int:
    return 1 if x >= 0 else -1


# ── Input sanitiser ─────────────────────────────────────────────────────

class InputSanitiser:
    """
    Pipeline of transforms applied to inference payloads before they
    reach the model.

    Register transforms with :meth:`add_transform`.
    """

    def __init__(self) -> None:
        self._transforms: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def add_transform(
        self, fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> "InputSanitiser":
        self._transforms.append(fn)
        return self

    def sanitise(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = payload
        for fn in self._transforms:
            result = fn(result)
        return result

    @classmethod
    def default(cls) -> "InputSanitiser":
        """Pre-configured sanitiser with PII redaction."""
        redactor = PIIRedactor()
        s = cls()
        s.add_transform(redactor.redact_dict)
        return s
