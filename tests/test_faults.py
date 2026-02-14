"""
Test 6: Faults System (faults/)

Tests Fault, FaultDomain, Severity, FaultContext, RecoveryStrategy, FaultEngine.
"""

import pytest

from aquilia.faults.core import (
    Fault, FaultDomain, Severity, RecoveryStrategy, DOMAIN_DEFAULTS,
)
from aquilia.faults import FaultEngine, FaultContext, FaultHandler


# ============================================================================
# Severity
# ============================================================================

class TestSeverity:

    def test_values(self):
        assert Severity.INFO == "info"
        assert Severity.WARN == "warn"
        assert Severity.ERROR == "error"
        assert Severity.FATAL == "fatal"

    def test_aliases(self):
        assert Severity.LOW == Severity.INFO
        assert Severity.MEDIUM == Severity.WARN
        assert Severity.HIGH == Severity.ERROR
        assert Severity.CRITICAL == Severity.FATAL


# ============================================================================
# FaultDomain
# ============================================================================

class TestFaultDomain:

    def test_standard_domains(self):
        assert FaultDomain.CONFIG.name == "config"
        assert FaultDomain.REGISTRY.name == "registry"
        assert FaultDomain.DI.name == "di"
        assert FaultDomain.ROUTING.name == "routing"
        assert FaultDomain.FLOW.name == "flow"
        assert FaultDomain.EFFECT.name == "effect"
        assert FaultDomain.IO.name == "io"
        assert FaultDomain.SECURITY.name == "security"
        assert FaultDomain.SYSTEM.name == "system"

    def test_custom_domain(self):
        custom = FaultDomain("payments", "Payment errors")
        assert custom.name == "payments"
        assert custom.description == "Payment errors"

    def test_domain_equality(self):
        d1 = FaultDomain("test", "")
        d2 = FaultDomain("test", "")
        d3 = FaultDomain("other", "")
        assert d1 == d2
        assert d1 != d3

    def test_domain_hashable(self):
        d = FaultDomain("test", "")
        s = {d}
        assert d in s


# ============================================================================
# Fault
# ============================================================================

class TestFault:

    def test_basic_fault(self):
        f = Fault(
            code="USER_NOT_FOUND",
            message="User not found",
            domain=FaultDomain.FLOW,
        )
        assert f.code == "USER_NOT_FOUND"
        assert f.message == "User not found"
        assert f.domain == FaultDomain.FLOW
        assert f.severity == Severity.ERROR  # Default for FLOW
        assert f.retryable is False
        assert f.public is False

    def test_fault_str(self):
        f = Fault(code="ERR", message="Something wrong", domain=FaultDomain.SYSTEM)
        assert "[ERR]" in str(f)
        assert "Something wrong" in str(f)

    def test_fault_is_exception(self):
        f = Fault(code="ERR", message="msg", domain=FaultDomain.IO)
        assert isinstance(f, Exception)

    def test_fault_raise(self):
        with pytest.raises(Fault) as exc_info:
            raise Fault(code="BANG", message="kaboom", domain=FaultDomain.SYSTEM)
        assert exc_info.value.code == "BANG"

    def test_fault_with_metadata(self):
        f = Fault(
            code="ERR",
            message="msg",
            domain=FaultDomain.IO,
            metadata={"key": "value"},
        )
        assert f.metadata["key"] == "value"

    def test_fault_kwargs_merged_to_metadata(self):
        f = Fault(
            code="ERR",
            message="msg",
            domain=FaultDomain.IO,
            user_id="42",
        )
        assert f.metadata["user_id"] == "42"

    def test_fault_custom_severity(self):
        f = Fault(
            code="WARN",
            message="not critical",
            domain=FaultDomain.IO,
            severity=Severity.WARN,
        )
        assert f.severity == Severity.WARN

    def test_fault_retryable(self):
        f = Fault(
            code="TIMEOUT",
            message="timed out",
            domain=FaultDomain.EFFECT,
            retryable=True,
        )
        assert f.retryable is True

    def test_fault_public(self):
        f = Fault(
            code="BAD_INPUT",
            message="invalid input",
            domain=FaultDomain.ROUTING,
            public=True,
        )
        assert f.public is True

    def test_fault_subclass(self):
        class NotFoundFault(Fault):
            code = "NOT_FOUND"
            message = "Resource not found"
            domain = FaultDomain.ROUTING

        f = NotFoundFault()
        assert f.code == "NOT_FOUND"
        assert f.domain == FaultDomain.ROUTING

    def test_fault_missing_required_raises(self):
        with pytest.raises(TypeError):
            Fault(code="X")  # Missing message and domain


# ============================================================================
# RecoveryStrategy
# ============================================================================

class TestRecoveryStrategy:

    def test_values(self):
        assert RecoveryStrategy.PROPAGATE == "propagate"
        assert RecoveryStrategy.RETRY == "retry"
        assert RecoveryStrategy.FALLBACK == "fallback"
        assert RecoveryStrategy.MASK == "mask"
        assert RecoveryStrategy.CIRCUIT_BREAK == "break"


# ============================================================================
# Domain Defaults
# ============================================================================

class TestDomainDefaults:

    def test_config_fatal(self):
        defaults = DOMAIN_DEFAULTS[FaultDomain.CONFIG]
        assert defaults["severity"] == Severity.FATAL
        assert defaults["retryable"] is False

    def test_io_retryable(self):
        defaults = DOMAIN_DEFAULTS[FaultDomain.IO]
        assert defaults["retryable"] is True

    def test_effect_retryable(self):
        defaults = DOMAIN_DEFAULTS[FaultDomain.EFFECT]
        assert defaults["retryable"] is True

    def test_security_not_retryable(self):
        defaults = DOMAIN_DEFAULTS[FaultDomain.SECURITY]
        assert defaults["retryable"] is False
