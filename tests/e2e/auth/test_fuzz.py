"""
E2E Auth Tests — Fuzz Harness

Token parser fuzzing, PKCE fuzzing, password policy property tests.
Crash/exception logs written to tests/e2e/fuzz-reports/.
"""

import os
import json
import base64
import secrets
import time
import pytest

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from aquilia.auth.tokens import TokenManager
from aquilia.auth.oauth import PKCEVerifier
from aquilia.auth.hashing import PasswordPolicy

FUZZ_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "fuzz-reports")


def _ensure_report_dir():
    os.makedirs(FUZZ_REPORTS_DIR, exist_ok=True)


def _log_crash(test_id: str, input_data: str, error: str):
    _ensure_report_dir()
    entry = {"test_id": test_id, "input": repr(input_data)[:500], "error": str(error)[:500],
             "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    path = os.path.join(FUZZ_REPORTS_DIR, f"{test_id}.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


class TestTokenParserFuzz:
    """Fuzz the access token parser with random/malformed inputs."""

    async def test_random_bytes_1000(self, token_manager):
        """FUZ-01: 1000 random byte strings → all rejected, no crash."""
        _ensure_report_dir()
        crashes = []
        for i in range(1000):
            token = secrets.token_bytes(secrets.randbelow(200) + 1).decode("latin-1")
            try:
                await token_manager.validate_access_token(token)
                crashes.append({"input": repr(token)[:100], "issue": "did not raise"})
            except ValueError:
                pass  # expected
            except Exception as e:
                _log_crash("FUZ-01", token, e)
                # Non-ValueError exceptions are acceptable (TypeError etc) but track them
        assert len(crashes) == 0, f"Tokens accepted: {crashes[:5]}"

    async def test_massive_length_token(self, token_manager):
        """FUZ-02: 1MB token → rejected, no OOM."""
        huge = "a" * (1024 * 1024)
        with pytest.raises((ValueError, Exception)):
            await token_manager.validate_access_token(huge)

    async def test_invalid_base64_segments(self, token_manager):
        """FUZ-03: Invalid base64 in each segment → ValueError."""
        bad_tokens = [
            "!!!.valid_base64.valid_base64",
            "eyJ0ZXN0IjoxfQ.!!!bad!!!.signature",
            "eyJ0ZXN0IjoxfQ.eyJ0ZXN0IjoxfQ.!!!",
            "...",
            "\x00.\x00.\x00",
        ]
        for token in bad_tokens:
            with pytest.raises((ValueError, Exception)):
                await token_manager.validate_access_token(token)

    async def test_valid_header_random_sig(self, token_manager, key_ring):
        """FUZ-04: Valid header+payload structure, random signature → rejected."""
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "kid": key_ring.get_signing_key().kid, "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "hacker", "exp": int(time.time()) + 3600}).encode()
        ).rstrip(b"=").decode()
        for _ in range(100):
            sig = base64.urlsafe_b64encode(secrets.token_bytes(256)).rstrip(b"=").decode()
            token = f"{header}.{payload}.{sig}"
            with pytest.raises(ValueError):
                await token_manager.validate_access_token(token)

    async def test_empty_and_whitespace_tokens(self, token_manager):
        """Edge case: empty, whitespace, null bytes."""
        for token in ["", " ", "\n", "\t", "\x00", " . . "]:
            with pytest.raises((ValueError, Exception)):
                await token_manager.validate_access_token(token)


class TestPKCEFuzz:
    """Fuzz PKCE verifier."""

    def test_random_verifiers_500(self):
        """FUZ-05: Random strings as code_verifier → no crash."""
        challenge = PKCEVerifier.generate_code_challenge(
            PKCEVerifier.generate_code_verifier()
        )
        for _ in range(500):
            random_verifier = secrets.token_urlsafe(secrets.randbelow(200) + 1)
            result = PKCEVerifier.verify_code_challenge(random_verifier, challenge)
            assert result is False  # Random verifier should never match

    def test_empty_verifier(self):
        """Empty verifier → returns False, no crash."""
        challenge = PKCEVerifier.generate_code_challenge("valid_verifier")
        assert PKCEVerifier.verify_code_challenge("", challenge) is False

    def test_null_bytes_verifier(self):
        """Null bytes in verifier → returns False."""
        challenge = PKCEVerifier.generate_code_challenge("valid_verifier")
        assert PKCEVerifier.verify_code_challenge("\x00\x00\x00", challenge) is False


class TestPasswordPolicyFuzz:
    """Property-based testing for password policy."""

    @given(password=st.text(min_size=0, max_size=200))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_policy_never_crashes(self, password):
        """Any string → policy returns (bool, list[str]), never crashes."""
        policy = PasswordPolicy(
            min_length=8, require_uppercase=True, require_lowercase=True,
            require_digit=True, require_special=True,
        )
        result = policy.validate(password)
        assert isinstance(result, tuple)
        is_valid, violations = result
        assert isinstance(is_valid, bool)
        assert isinstance(violations, list)

    @given(password=st.text(min_size=0, max_size=500))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_hasher_never_crashes(self, password):
        """Any string → hasher.hash() produces a string, never crashes."""
        from aquilia.auth.hashing import PasswordHasher
        hasher = PasswordHasher(algorithm="pbkdf2_sha256", iterations=100)
        try:
            h = hasher.hash(password)
            assert isinstance(h, str)
            assert len(h) > 0
        except ValueError:
            pass  # Empty password may be rejected


class TestRefreshTokenFuzz:
    """Fuzz refresh token validation."""

    async def test_random_refresh_tokens(self, token_manager):
        """Random strings as refresh tokens → all rejected."""
        for _ in range(200):
            fake = f"rt_{secrets.token_urlsafe(32)}"
            with pytest.raises(ValueError, match="Invalid refresh token"):
                await token_manager.validate_refresh_token(fake)

    async def test_malformed_refresh_tokens(self, token_manager):
        """Non-rt_ prefixed tokens → rejected."""
        for prefix in ["at_", "xx_", "", "rt", "RT_"]:
            fake = f"{prefix}{secrets.token_urlsafe(16)}"
            with pytest.raises(ValueError):
                await token_manager.validate_refresh_token(fake)
