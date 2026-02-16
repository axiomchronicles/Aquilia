"""
Tests for aquilia.mlops.explain — SHAP/LIME hooks, privacy & PII redaction.
"""

import pytest

from aquilia.mlops.explain.hooks import (
    ExplainMethod,
    FeatureAttribution,
    Explanation,
    create_explainer,
)
from aquilia.mlops.explain.privacy import (
    PIIKind,
    PIIRedactor,
    LaplaceNoise,
    InputSanitiser,
)


# ── Explanation data classes ─────────────────────────────────────────────

class TestExplanation:
    def test_top_k(self):
        attrs = [
            FeatureAttribution(name=f"f{i}", value=float(i), base_value=0.0)
            for i in range(20)
        ]
        exp = Explanation(method=ExplainMethod.SHAP_KERNEL, attributions=attrs)
        top = exp.top_k
        assert len(top) == 10
        assert top[0].value == 19.0  # largest absolute value

    def test_to_dict(self):
        attrs = [FeatureAttribution(name="age", value=0.5, base_value=0.1)]
        exp = Explanation(
            method=ExplainMethod.LIME_TABULAR,
            attributions=attrs,
            prediction=1,
        )
        d = exp.to_dict()
        assert d["method"] == "lime_tabular"
        assert d["prediction"] == 1
        assert len(d["attributions"]) == 1


# ── PIIRedactor ──────────────────────────────────────────────────────────

class TestPIIRedactor:
    def test_redact_email(self):
        r = PIIRedactor()
        text = "Contact alice@example.com for details."
        result = r.redact(text)
        assert "alice@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_redact_phone(self):
        r = PIIRedactor()
        text = "Call me at 555-123-4567 ok?"
        result = r.redact(text)
        assert "555-123-4567" not in result

    def test_redact_ssn(self):
        r = PIIRedactor()
        text = "SSN: 123-45-6789"
        result = r.redact(text)
        assert "123-45-6789" not in result

    def test_redact_ip(self):
        r = PIIRedactor()
        text = "Server at 192.168.1.100"
        result = r.redact(text)
        assert "192.168.1.100" not in result

    def test_no_pii(self):
        r = PIIRedactor()
        text = "Just a normal sentence."
        assert r.redact(text) == text

    def test_scan_returns_matches(self):
        r = PIIRedactor()
        matches = r.scan("Email: user@test.com, phone: 555-000-1234")
        kinds = {m.kind for m in matches}
        assert PIIKind.EMAIL in kinds
        assert PIIKind.PHONE in kinds

    def test_redact_dict(self):
        r = PIIRedactor()
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "nested": {"ip": "10.0.0.1"},
        }
        result = r.redact_dict(data)
        assert "alice@example.com" not in result["email"]
        assert "10.0.0.1" not in result["nested"]["ip"]

    def test_hash_replacement(self):
        r = PIIRedactor(hash_replacement=True)
        result = r.redact("Contact bob@test.com")
        assert "_HASH_" in result

    def test_selective_kinds(self):
        r = PIIRedactor(kinds={PIIKind.EMAIL})
        text = "Email: a@b.com, Phone: 555-111-2222"
        result = r.redact(text)
        assert "a@b.com" not in result
        assert "555-111-2222" in result  # phone not redacted


# ── LaplaceNoise ─────────────────────────────────────────────────────────

class TestLaplaceNoise:
    def test_adds_noise(self):
        noise = LaplaceNoise(epsilon=1.0, sensitivity=1.0)
        values = [noise.add_noise(100.0) for _ in range(100)]
        # All values should differ from 100 (with overwhelming probability)
        exact = [v for v in values if v == 100.0]
        assert len(exact) < 5  # extremely unlikely to be exactly 100

    def test_noise_centered(self):
        noise = LaplaceNoise(epsilon=10.0, sensitivity=1.0)
        vals = [noise.add_noise(0.0) for _ in range(10000)]
        mean = sum(vals) / len(vals)
        assert abs(mean) < 0.5  # should be roughly centered at 0

    def test_invalid_epsilon(self):
        with pytest.raises(ValueError):
            LaplaceNoise(epsilon=0)

    def test_array_noise(self):
        noise = LaplaceNoise(epsilon=1.0)
        result = noise.add_noise_array([1.0, 2.0, 3.0])
        assert len(result) == 3


# ── InputSanitiser ───────────────────────────────────────────────────────

class TestInputSanitiser:
    def test_default_sanitiser(self):
        s = InputSanitiser.default()
        result = s.sanitise({"text": "Email me at foo@bar.com"})
        assert "foo@bar.com" not in result["text"]

    def test_custom_transform(self):
        s = InputSanitiser()
        s.add_transform(lambda d: {k: v.upper() if isinstance(v, str) else v for k, v in d.items()})
        result = s.sanitise({"name": "alice"})
        assert result["name"] == "ALICE"

    def test_chained_transforms(self):
        s = InputSanitiser()
        s.add_transform(lambda d: {**d, "step1": True})
        s.add_transform(lambda d: {**d, "step2": True})
        result = s.sanitise({"original": True})
        assert result["step1"] is True
        assert result["step2"] is True
