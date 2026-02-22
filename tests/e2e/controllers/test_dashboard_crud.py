"""
DASH-001 to DASH-006: Dashboard CRUD controller tests.

Exercises: DashboardController (list, create, get, update, delete), DashboardService, faults.
"""

import pytest


pytestmark = pytest.mark.asyncio


# ── DASH-001: Create ─────────────────────────────────────────────────────

class TestDashboardCreate:
    """Creating dashboard items."""

    async def test_create_item(self, client):
        """DASH-001: POST /dashboard/ creates an item with ID."""
        resp = await client.post("/dashboard/", json={"name": "My Widget"})
        assert resp.status_code == 201, f"Create failed: {resp.status_code} {resp.text}"
        body = resp.json()
        assert "id" in body
        assert body["name"] == "My Widget"

    async def test_create_returns_incremented_id(self, client):
        """DASH-001b: Sequential creates have incrementing IDs."""
        r1 = await client.post("/dashboard/", json={"name": "First"})
        r2 = await client.post("/dashboard/", json={"name": "Second"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r2.json()["id"] > r1.json()["id"]


# ── DASH-002: List ────────────────────────────────────────────────────────

class TestDashboardList:
    """Listing dashboard items."""

    async def test_list_empty(self, client):
        """DASH-002: Fresh list returns empty items array."""
        resp = await client.get("/dashboard/")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    async def test_list_after_create(self, client):
        """DASH-002b: List includes created items."""
        await client.post("/dashboard/", json={"name": "Listed Item"})
        resp = await client.get("/dashboard/")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ── DASH-003: Get by ID ──────────────────────────────────────────────────

class TestDashboardGet:
    """Getting a specific dashboard item."""

    async def test_get_by_id(self, client):
        """DASH-003: GET /dashboard/{id} returns the correct item."""
        create_resp = await client.post("/dashboard/", json={"name": "Get Me"})
        item_id = create_resp.json()["id"]

        resp = await client.get(f"/dashboard/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == item_id
        assert resp.json()["name"] == "Get Me"


# ── DASH-004: Update ─────────────────────────────────────────────────────

class TestDashboardUpdate:
    """Updating dashboard items."""

    async def test_update_item(self, client):
        """DASH-004: PUT /dashboard/{id} updates the item."""
        create_resp = await client.post("/dashboard/", json={"name": "Old Name"})
        item_id = create_resp.json()["id"]

        update_resp = await client.put(f"/dashboard/{item_id}", json={"name": "New Name"})
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "New Name"

        # Verify persistence
        get_resp = await client.get(f"/dashboard/{item_id}")
        assert get_resp.json()["name"] == "New Name"


# ── DASH-005: Delete ─────────────────────────────────────────────────────

class TestDashboardDelete:
    """Deleting dashboard items."""

    async def test_delete_item(self, client):
        """DASH-005: DELETE /dashboard/{id} returns 204."""
        create_resp = await client.post("/dashboard/", json={"name": "Delete Me"})
        item_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/dashboard/{item_id}")
        assert del_resp.status_code == 204

    async def test_get_after_delete_fails(self, client):
        """DASH-005b: GET after DELETE returns fault."""
        create_resp = await client.post("/dashboard/", json={"name": "Gone"})
        item_id = create_resp.json()["id"]
        await client.delete(f"/dashboard/{item_id}")

        get_resp = await client.get(f"/dashboard/{item_id}")
        assert 400 <= get_resp.status_code < 500


# ── DASH-006: Not found ──────────────────────────────────────────────────

class TestDashboardNotFound:
    """Accessing non-existent items raises DashboardNotFoundFault."""

    async def test_get_nonexistent(self, client):
        """DASH-006: GET /dashboard/9999 returns not found."""
        resp = await client.get("/dashboard/9999")
        assert 400 <= resp.status_code < 500

    async def test_update_nonexistent(self, client):
        """DASH-006b: PUT /dashboard/9999 returns not found."""
        resp = await client.put("/dashboard/9999", json={"name": "Nope"})
        assert 400 <= resp.status_code < 500

    async def test_delete_nonexistent(self, client):
        """DASH-006c: DELETE /dashboard/9999 returns not found."""
        resp = await client.delete("/dashboard/9999")
        assert 400 <= resp.status_code < 500
