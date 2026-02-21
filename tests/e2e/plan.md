# Brutal Auth E2E Test Plan

## Regression Sequences

| ID | Title | Prerequisites | Request(s) | Expected Side-Effects | Cleanup | Risk |
|----|-------|--------------|------------|----------------------|---------|------|
| REG-01 | Token revocation → reuse | Seed user, login | 1) `authenticate_password` 2) `revoke_token(refresh)` 3) `refresh_access_token(revoked)` | Step 3 raises `ValueError("Refresh token revoked")`, token in `_revoked_tokens` set | Fixtures auto-cleanup | high |
| REG-02 | Concurrent password resets | Seed user | 10× concurrent `authenticate_password` with wrong pw then 1× correct | Rate limiter tracks all 10 attempts, possible lockout race | Reset rate limiter | high |
| REG-03 | Session fixation | Seed user | 1) Forge `sess_EVIL` 2) Login gets `sess_NEW` 3) Validate `sess_EVIL` fails | Login always generates new session_id, forged ID never enters store | None | high |
| REG-04 | Concurrent writes to same user | Seed user | 10× concurrent credential updates | Last write wins, no crashes, store consistent | Re-seed | high |
| REG-05 | Login→Refresh→Logout full cycle | Seed user | Login → validate → refresh (old revoked) → logout (session revoked) | Audit trail: login+refresh+revoke events | Fixtures | high |
| REG-06 | Duplicate registration | Seed user | Create same identity ID twice | Second create raises or overwrites deterministically | Delete | medium |

## Chaos Tests

| ID | Title | Prerequisites | Steps | Expected | Cleanup | Risk |
|----|-------|--------------|-------|----------|---------|------|
| CHS-01 | Store corruption mid-operation | Auth manager | Monkey-patch store to raise mid-`save_password` | AuthManager returns structured fault, no partial state | Restore patches | high |
| CHS-02 | Cache corruption: invalid JSON | Token store | Write garbage bytes to `_refresh_tokens[id]` | `validate_refresh_token` raises `ValueError`, no crash | Clear store | medium |
| CHS-03 | Token store unavailable | Auth manager | Monkey-patch token_store to raise `ConnectionError` | Login fails with structured fault, no token leak | Restore | high |
| CHS-04 | Chained failure: corrupt+concurrent | Auth manager, stores | Corrupt cache → concurrent refresh → restore → consistency check | No duplicate tokens, no orphaned sessions, store consistent | Full teardown | high |

## Fuzzing

| ID | Title | Input | Expected | Risk |
|----|-------|-------|----------|------|
| FUZ-01 | Token parser: random bytes | 1000 random byte strings as access tokens | All raise `ValueError`, no crash/hang | high |
| FUZ-02 | Token parser: massive length | Tokens with 1MB+ payload | Raises `ValueError`, no OOM | high |
| FUZ-03 | Token parser: invalid base64 | Malformed base64 in header/payload/sig | Raises `ValueError` | high |
| FUZ-04 | Token parser: bad signatures | Valid header+payload, random signature | Raises `ValueError("Invalid signature")` | high |
| FUZ-05 | PKCE verifier fuzz | 500 random strings as code_verifier | `verify_code_challenge` returns False, no crash | medium |
| FUZ-06 | Password policy fuzz (Hypothesis) | Property test: any string → policy returns well-formed result | No exceptions, returns `(bool, list[str])` | medium |

## Fault Injection

| ID | Title | Injection | Expected | Risk |
|----|-------|-----------|----------|------|
| FLT-01 | External email provider down | Monkey-patch mail send to raise | Password reset returns structured error, no sensitive data leaked | medium |
| FLT-02 | Rate limiter misconfiguration | Set max_attempts=0 | Immediate lockout on any attempt | medium |
| FLT-03 | Memory pressure on token store | Fill store with 10000 tokens then operate | Operations succeed within timeout, cleanup works | medium |

## Performance / Stress

| ID | Title | Setup | Steps | Threshold | Risk |
|----|-------|-------|-------|-----------|------|
| PRF-01 | 200 concurrent login+refresh | Seed user | 200× asyncio.gather(login→refresh) for 10s | No deadlocks, all complete, no resource exhaustion | high |
| PRF-02 | Token validation throughput | Issue 1000 tokens | Validate all 1000 sequentially | < 10s total, no memory leak | medium |
| PRF-03 | Concurrent token revocation | Issue 100 tokens | 100× concurrent revoke_token | All revoked, no races, store consistent | high |
