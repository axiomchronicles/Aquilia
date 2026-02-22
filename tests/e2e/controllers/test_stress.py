"""
STRESS-001: Concurrency stress test.

Fires 200 parallel requests (mix of login, refresh, /me, dashboard CRUD)
for ~60 seconds to surface deadlocks and resource exhaustion.
"""

import pytest
import asyncio
import uuid
import time


pytestmark = pytest.mark.asyncio


def _unique_email(tag: str = "") -> str:
    return f"stress-{tag}-{uuid.uuid4().hex[:8]}@test.com"


class TestConcurrencyStress:
    """High-concurrency mixed workload stress test."""

    @pytest.mark.timeout(120)  # Hard timeout
    async def test_200_parallel_mixed_requests(self, client):
        """STRESS-001: 200 parallel requests should not deadlock or exhaust resources."""
        # Phase 1: Seed users
        users = []
        for i in range(5):
            email = _unique_email(f"s{i}")
            user = {"email": email, "password": "Str0ngP@ss!", "full_name": f"Stress {i}"}
            reg = await client.post("/auth/register", json=user)
            if reg.status_code == 201:
                login = await client.post("/auth/login", json={
                    "email": email, "password": user["password"],
                })
                if login.status_code == 200:
                    tokens = login.json()
                    users.append({"user": user, "tokens": tokens})

        assert len(users) >= 1, "Need at least 1 registered user for stress test"

        # Phase 2: Define workload mix
        request_counter = {"total": 0, "success": 0, "error": 0}

        async def random_login():
            u = users[request_counter["total"] % len(users)]
            resp = await client.post("/auth/login", json={
                "email": u["user"]["email"],
                "password": u["user"]["password"],
            })
            return resp

        async def random_me():
            u = users[request_counter["total"] % len(users)]
            resp = await client.get("/auth/me", headers={
                "Authorization": f"Bearer {u['tokens']['access_token']}",
            })
            return resp

        async def random_dashboard_crud():
            # Create
            r = await client.post("/dashboard/", json={"name": f"stress-{uuid.uuid4().hex[:6]}"})
            if r.status_code == 201:
                item_id = r.json().get("id", 1)
                await client.get(f"/dashboard/{item_id}")
                await client.put(f"/dashboard/{item_id}", json={"name": "updated"})
                await client.delete(f"/dashboard/{item_id}")
            return r

        async def random_refresh():
            u = users[request_counter["total"] % len(users)]
            # Re-login to get fresh refresh token
            login = await client.post("/auth/login", json={
                "email": u["user"]["email"],
                "password": u["user"]["password"],
            })
            if login.status_code == 200:
                return await client.post("/auth/refresh", json={
                    "refresh_token": login.json()["refresh_token"],
                })
            return login

        workloads = [random_login, random_me, random_dashboard_crud, random_refresh]

        # Phase 3: Fire requests
        async def run_workload(idx):
            request_counter["total"] += 1
            fn = workloads[idx % len(workloads)]
            try:
                resp = await fn()
                if hasattr(resp, 'status_code') and resp.status_code < 500:
                    request_counter["success"] += 1
                else:
                    request_counter["error"] += 1
                return resp
            except Exception:
                request_counter["error"] += 1
                return None

        start = time.monotonic()
        batch_size = 50
        total_requests = 200

        for batch_start in range(0, total_requests, batch_size):
            batch_end = min(batch_start + batch_size, total_requests)
            tasks = [run_workload(i) for i in range(batch_start, batch_end)]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Check if we've been running too long
            if time.monotonic() - start > 60:
                break

        elapsed = time.monotonic() - start

        # Assertions
        total = request_counter["total"]
        success = request_counter["success"]
        error = request_counter["error"]

        assert total >= 100, f"Expected at least 100 requests, ran {total}"
        # At least 50% success rate for stress test
        success_rate = success / max(total, 1)
        assert success_rate >= 0.5, (
            f"Success rate too low: {success_rate:.1%} ({success}/{total}). "
            f"Errors: {error}. Elapsed: {elapsed:.1f}s"
        )

    async def test_rapid_register_login_cycle(self, client):
        """STRESS-001b: Rapid register-login cycles should not leak resources."""
        for i in range(20):
            email = _unique_email(f"rapid{i}")
            reg = await client.post("/auth/register", json={
                "email": email, "password": "Str0ngP@ss!", "full_name": f"Rapid {i}",
            })
            if reg.status_code == 201:
                await client.post("/auth/login", json={
                    "email": email, "password": "Str0ngP@ss!",
                })
        # If we get here without hanging/crashing, the test passes
