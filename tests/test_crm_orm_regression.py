"""
CRM ORM Regression Tests
=========================
Comprehensive regression tests validating that all CRM services properly
use the Aquilia ORM instead of raw SQL. Tests cover:

1. ORM Wiring — DB connectivity through ModelRegistry
2. Model CRUD — create, get, filter, update (save), delete
3. QuerySet API — filter, order, limit, offset, count, exists, first, all
4. Service Layer — every service method end-to-end through ORM
5. Signals — post_save activity logging
6. Edge Cases — not found, duplicates, stage validation, empty results

Runs against an in-memory SQLite database with full ORM wiring,
exactly as the production server does via _boot_models().
"""

import asyncio
import os
import sys
import pytest

# Ensure myapp is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "myapp"))

from aquilia.db.engine import AquiliaDatabase, configure_database
from aquilia.models.registry import ModelRegistry

# Import all models (triggers metaclass registration)
from modules.shared.models import (
    User,
    Contact,
    Company,
    Deal,
    Task,
    Activity,
    Note,
    EmailCampaign,
)


# ═════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture
async def db():
    """
    Create an in-memory SQLite database, connect it, wire it into the
    ModelRegistry (exactly as the server's _boot_models does), create
    all CRM tables, and tear down after each test.
    """
    database = AquiliaDatabase("sqlite:///:memory:")
    await database.connect()

    # Wire the DB to all models — this is the critical ORM wiring step
    ModelRegistry.set_database(database)

    # Create all tables
    models = [User, Contact, Company, Deal, Task, Activity, Note, EmailCampaign]
    for model_cls in models:
        sql = model_cls.generate_create_table_sql(dialect="sqlite")
        await database.execute(sql)
        for idx_sql in model_cls.generate_index_sql(dialect="sqlite"):
            try:
                await database.execute(idx_sql)
            except Exception:
                pass

    yield database

    await database.disconnect()
    # Clean up registry to avoid leaking state between tests
    ModelRegistry._db = None


@pytest.fixture
async def seeded_db(db):
    """
    Seed the database with representative data for integration tests.
    Returns the DB instance with data already loaded.
    """
    from aquilia.auth import PasswordHasher
    hasher = PasswordHasher()

    # Users
    await User.create(
        email="admin@crm.dev", password_hash=hasher.hash("password123"),
        first_name="Admin", last_name="User", role="admin", is_active=True,
    )
    await User.create(
        email="sarah@crm.dev", password_hash=hasher.hash("password123"),
        first_name="Sarah", last_name="Johnson", role="manager", is_active=True,
    )
    await User.create(
        email="mike@crm.dev", password_hash=hasher.hash("password123"),
        first_name="Mike", last_name="Chen", role="rep", is_active=True,
    )
    await User.create(
        email="inactive@crm.dev", password_hash=hasher.hash("password123"),
        first_name="Gone", last_name="User", role="rep", is_active=False,
    )

    # Companies
    await Company.create(
        name="Acme Corp", industry="technology", size="51-200",
        website="https://acme.com", email="info@acme.com", owner_id=2,
        annual_revenue=5000000.00,
    )
    await Company.create(
        name="GlobalHealth Inc", industry="healthcare", size="201-1000",
        email="contact@globalhealth.com", owner_id=2, annual_revenue=25000000.00,
    )

    # Contacts
    await Contact.create(
        first_name="John", last_name="Smith", email="john@acme.com",
        phone="+1-555-1001", job_title="CTO", company_id=1,
        status="customer", source="referral", score=85, owner_id=3,
    )
    await Contact.create(
        first_name="Lisa", last_name="Park", email="lisa@globalhealth.com",
        phone="+1-555-1002", job_title="VP of Operations", company_id=2,
        status="qualified", source="linkedin", score=72, owner_id=3,
    )
    await Contact.create(
        first_name="David", last_name="Brown", email="david@example.com",
        job_title="CEO", status="prospect", source="trade_show", score=60, owner_id=3,
    )

    # Deals
    await Deal.create(
        title="Acme Enterprise License", value=120000, stage="negotiation",
        probability=75, contact_id=1, company_id=1, owner_id=3, priority="high",
    )
    await Deal.create(
        title="GlobalHealth Platform", value=350000, stage="proposal",
        probability=50, contact_id=2, company_id=2, owner_id=3, priority="critical",
    )
    await Deal.create(
        title="Small Starter Deal", value=15000, stage="discovery",
        probability=20, contact_id=3, owner_id=3, priority="medium",
    )
    await Deal.create(
        title="Won Deal", value=80000, stage="closed_won",
        probability=100, owner_id=3, priority="high",
    )
    await Deal.create(
        title="Lost Deal", value=30000, stage="closed_lost",
        probability=0, owner_id=3, priority="low",
    )

    # Tasks
    await Task.create(
        title="Follow up with John Smith", status="pending", priority="high",
        task_type="call", assigned_to_id=3, created_by_id=2, contact_id=1, deal_id=1,
    )
    await Task.create(
        title="Send proposal to GlobalHealth", status="in_progress", priority="urgent",
        task_type="email", assigned_to_id=3, created_by_id=2, contact_id=2, deal_id=2,
    )
    await Task.create(
        title="Completed task", status="completed", priority="low",
        task_type="other", assigned_to_id=3, created_by_id=2,
    )
    await Task.create(
        title="Cancelled task", status="cancelled", priority="medium",
        task_type="meeting", assigned_to_id=2, created_by_id=1,
    )

    # Notes
    await Note.create(
        content="John expressed strong interest.",
        entity_type="contact", entity_id=1, author_id=3, is_pinned=True,
    )
    await Note.create(
        content="GlobalHealth compliance requirements.",
        entity_type="deal", entity_id=2, author_id=3, is_pinned=True,
    )

    # Email Campaigns
    await EmailCampaign.create(
        name="Q1 Newsletter", subject="Q1 Update", body_html="<h1>Hello</h1>",
        status="draft", sender_id=1,
    )

    return db


# ═════════════════════════════════════════════════════════════════════════════
#  1. ORM WIRING TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestORMWiring:
    """Verify the fundamental ORM database wiring works correctly."""

    async def test_model_registry_has_database(self, db):
        """ModelRegistry.get_database() returns the wired DB after set_database."""
        result = ModelRegistry.get_database()
        assert result is db

    async def test_model_get_db_returns_connected_database(self, db):
        """Model._get_db() returns a connected database instance."""
        result = User._get_db()
        assert result is db
        assert result._connected is True

    async def test_all_models_share_same_db(self, db):
        """All CRM models access the exact same DB instance."""
        models = [User, Contact, Company, Deal, Task, Activity, Note, EmailCampaign]
        dbs = [m._get_db() for m in models]
        for model_db in dbs:
            assert model_db is db

    async def test_model_registry_set_database_propagates(self, db):
        """set_database propagates to every registered model's _db."""
        assert User._db is db
        assert Contact._db is db
        assert Deal._db is db

    async def test_tables_created_via_orm(self, db):
        """Tables are created using Model.generate_create_table_sql."""
        # Verify tables exist by doing a simple query
        row = await db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='crm_users'"
        )
        assert row is not None
        assert row["name"] == "crm_users"

    async def test_all_crm_tables_exist(self, db):
        """All 8 CRM tables are created."""
        expected_tables = [
            "crm_users", "crm_contacts", "crm_companies", "crm_deals",
            "crm_tasks", "crm_activities", "crm_notes", "crm_email_campaigns",
        ]
        rows = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [r["name"] for r in rows]
        for table in expected_tables:
            assert table in table_names, f"Missing table: {table}"


# ═════════════════════════════════════════════════════════════════════════════
#  2. MODEL CRUD TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestModelCreate:
    """Test ORM create() for all models."""

    async def test_create_user(self, db):
        user = await User.create(
            email="test@example.com", password_hash="hash123",
            first_name="Test", last_name="User", role="rep", is_active=True,
        )
        assert user.pk is not None
        assert user.pk > 0
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.role == "rep"
        assert user.is_active is True

    async def test_create_user_auto_timestamps(self, db):
        """auto_now_add fields get timestamps on create."""
        user = await User.create(
            email="ts@test.com", password_hash="h", first_name="A", last_name="B",
        )
        assert user.created_at is not None

    async def test_create_contact(self, db):
        contact = await Contact.create(
            first_name="Jane", last_name="Doe", email="jane@test.com",
            status="lead", source="website",
        )
        assert contact.pk is not None
        assert contact.first_name == "Jane"
        assert contact.email == "jane@test.com"
        assert contact.status == "lead"

    async def test_create_company(self, db):
        company = await Company.create(
            name="TestCorp", industry="technology", size="1-10",
        )
        assert company.pk is not None
        assert company.name == "TestCorp"

    async def test_create_deal(self, db):
        deal = await Deal.create(
            title="Big Deal", value=100000, stage="discovery",
            probability=10, priority="high",
        )
        assert deal.pk is not None
        assert deal.title == "Big Deal"
        assert deal.value == 100000
        assert deal.stage == "discovery"

    async def test_create_task(self, db):
        task = await Task.create(
            title="Call client", status="pending", priority="high",
            task_type="call",
        )
        assert task.pk is not None
        assert task.title == "Call client"
        assert task.status == "pending"

    async def test_create_activity(self, db):
        activity = await Activity.create(
            action="test_action", entity_type="contact",
            entity_id=1, description="Test activity",
        )
        assert activity.pk is not None
        assert activity.action == "test_action"

    async def test_create_note(self, db):
        note = await Note.create(
            content="Important note", entity_type="deal",
            entity_id=1, author_id=1,
        )
        assert note.pk is not None
        assert note.content == "Important note"

    async def test_create_email_campaign(self, db):
        campaign = await EmailCampaign.create(
            name="Newsletter", subject="Hello!", body_html="<p>Hi</p>",
            status="draft",
        )
        assert campaign.pk is not None
        assert campaign.name == "Newsletter"
        assert campaign.status == "draft"

    async def test_create_returns_model_instance(self, db):
        """create() returns a Model instance, not a dict or row."""
        user = await User.create(
            email="inst@test.com", password_hash="h",
            first_name="A", last_name="B",
        )
        assert isinstance(user, User)


class TestModelGet:
    """Test ORM get() by PK and filters."""

    async def test_get_by_pk(self, seeded_db):
        user = await User.get(pk=1)
        assert user is not None
        assert user.pk == 1
        assert user.email == "admin@crm.dev"

    async def test_get_by_pk_returns_none_for_missing(self, seeded_db):
        user = await User.get(pk=99999)
        assert user is None

    async def test_get_by_filter(self, seeded_db):
        user = await User.get(email="sarah@crm.dev")
        assert user is not None
        assert user.first_name == "Sarah"

    async def test_get_returns_model_instance(self, seeded_db):
        user = await User.get(pk=1)
        assert isinstance(user, User)

    async def test_get_contact_by_pk(self, seeded_db):
        contact = await Contact.get(pk=1)
        assert contact is not None
        assert contact.first_name == "John"
        assert contact.last_name == "Smith"

    async def test_get_company_by_pk(self, seeded_db):
        company = await Company.get(pk=1)
        assert company is not None
        assert company.name == "Acme Corp"

    async def test_get_deal_by_pk(self, seeded_db):
        deal = await Deal.get(pk=1)
        assert deal is not None
        assert deal.title == "Acme Enterprise License"
        assert deal.value == 120000


class TestModelSave:
    """Test ORM save() with update_fields."""

    async def test_save_updates_field(self, seeded_db):
        user = await User.get(pk=1)
        user.first_name = "Updated"
        await user.save(update_fields=["first_name"])

        # Re-read to verify persistence
        user2 = await User.get(pk=1)
        assert user2.first_name == "Updated"

    async def test_save_multiple_fields(self, seeded_db):
        contact = await Contact.get(pk=1)
        contact.first_name = "Johnny"
        contact.job_title = "CEO"
        await contact.save(update_fields=["first_name", "job_title"])

        contact2 = await Contact.get(pk=1)
        assert contact2.first_name == "Johnny"
        assert contact2.job_title == "CEO"

    async def test_save_preserves_unchanged_fields(self, seeded_db):
        user = await User.get(pk=1)
        original_email = user.email
        user.first_name = "Changed"
        await user.save(update_fields=["first_name"])

        user2 = await User.get(pk=1)
        assert user2.email == original_email
        assert user2.first_name == "Changed"

    async def test_save_returns_model_instance(self, seeded_db):
        user = await User.get(pk=1)
        user.first_name = "Test"
        result = await user.save(update_fields=["first_name"])
        assert isinstance(result, User)


class TestModelDelete:
    """Test ORM delete_instance()."""

    async def test_delete_instance(self, seeded_db):
        note = await Note.create(
            content="Will be deleted", entity_type="test",
            entity_id=1,
        )
        pk = note.pk
        assert pk is not None

        await note.delete_instance()

        # Verify it's gone
        deleted = await Note.get(pk=pk)
        assert deleted is None

    async def test_delete_contact(self, seeded_db):
        contact = await Contact.create(
            first_name="Delete", last_name="Me", email="delete@test.com",
        )
        pk = contact.pk
        await contact.delete_instance()
        assert await Contact.get(pk=pk) is None

    async def test_delete_returns_row_count(self, seeded_db):
        note = await Note.create(
            content="Count test", entity_type="test", entity_id=1,
        )
        count = await note.delete_instance()
        assert count == 1


# ═════════════════════════════════════════════════════════════════════════════
#  3. QUERYSET API TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestQuerySetFilter:
    """Test ORM filter(), exclude(), where() chains."""

    async def test_filter_single_field(self, seeded_db):
        users = await User.objects.filter(role="admin").all()
        assert len(users) == 1
        assert users[0].email == "admin@crm.dev"

    async def test_filter_multiple_fields(self, seeded_db):
        users = await User.objects.filter(role="rep", is_active=True).all()
        assert len(users) == 1
        assert users[0].email == "mike@crm.dev"

    async def test_filter_returns_empty_for_no_match(self, seeded_db):
        users = await User.objects.filter(email="nonexistent@test.com").all()
        assert len(users) == 0

    async def test_filter_boolean_field(self, seeded_db):
        active_users = await User.objects.filter(is_active=True).all()
        inactive_users = await User.objects.filter(is_active=False).all()
        # 3 active + 1 inactive
        assert len(active_users) == 3
        assert len(inactive_users) == 1

    async def test_where_raw_clause(self, seeded_db):
        """Test raw WHERE with LIKE for multi-field search."""
        s = "%John%"
        contacts = await Contact.query().where(
            "(first_name LIKE ? OR last_name LIKE ?)", s, s
        ).all()
        assert len(contacts) == 1
        assert contacts[0].first_name == "John"

    async def test_where_with_filter_combined(self, seeded_db):
        """Test combining raw WHERE and ORM filter."""
        s = "%John%"
        contacts = await Contact.query().where(
            "(first_name LIKE ? OR last_name LIKE ?)", s, s
        ).filter(status="customer").all()
        assert len(contacts) == 1


class TestQuerySetOrder:
    """Test ORM ordering."""

    async def test_order_ascending(self, seeded_db):
        companies = await Company.objects.order("name").all()
        assert len(companies) == 2
        assert companies[0].name == "Acme Corp"
        assert companies[1].name == "GlobalHealth Inc"

    async def test_order_descending(self, seeded_db):
        companies = await Company.objects.order("-name").all()
        assert companies[0].name == "GlobalHealth Inc"
        assert companies[1].name == "Acme Corp"


class TestQuerySetPagination:
    """Test limit, offset for pagination."""

    async def test_limit(self, seeded_db):
        contacts = await Contact.objects.limit(2).all()
        assert len(contacts) == 2

    async def test_offset(self, seeded_db):
        all_contacts = await Contact.objects.all()
        offset_contacts = await Contact.objects.limit(10).offset(1).all()
        assert len(offset_contacts) == len(all_contacts) - 1

    async def test_limit_offset_combined(self, seeded_db):
        # Page 1: first 2
        page1 = await Contact.objects.limit(2).offset(0).all()
        # Page 2: next 2
        page2 = await Contact.objects.limit(2).offset(2).all()
        assert len(page1) == 2
        assert len(page2) <= 2
        # No overlap
        page1_pks = {c.pk for c in page1}
        page2_pks = {c.pk for c in page2}
        assert page1_pks.isdisjoint(page2_pks)


class TestQuerySetAggregates:
    """Test count(), exists(), first()."""

    async def test_count(self, seeded_db):
        count = await User.objects.count()
        assert count == 4  # 4 users seeded

    async def test_count_with_filter(self, seeded_db):
        count = await User.objects.filter(is_active=True).count()
        assert count == 3

    async def test_exists_true(self, seeded_db):
        exists = await User.objects.filter(email="admin@crm.dev").exists()
        assert exists is True

    async def test_exists_false(self, seeded_db):
        exists = await User.objects.filter(email="nope@nope.com").exists()
        assert exists is False

    async def test_first(self, seeded_db):
        user = await User.objects.filter(role="admin").first()
        assert user is not None
        assert user.email == "admin@crm.dev"

    async def test_first_returns_none_on_empty(self, seeded_db):
        user = await User.objects.filter(email="nope@nope.com").first()
        assert user is None

    async def test_all_returns_list(self, seeded_db):
        users = await User.objects.all()
        assert isinstance(users, list)
        assert all(isinstance(u, User) for u in users)


class TestModelToDict:
    """Test Model.to_dict() and User.to_safe_dict()."""

    async def test_to_dict_returns_dict(self, seeded_db):
        user = await User.get(pk=1)
        d = user.to_dict()
        assert isinstance(d, dict)
        assert "email" in d
        assert d["email"] == "admin@crm.dev"

    async def test_to_safe_dict_excludes_password(self, seeded_db):
        user = await User.get(pk=1)
        d = user.to_safe_dict()
        assert "password_hash" not in d
        assert "full_name" in d
        assert d["full_name"] == "Admin User"


class TestModelProperties:
    """Test model properties (full_name, pk)."""

    async def test_user_full_name(self, seeded_db):
        user = await User.get(pk=1)
        assert user.full_name == "Admin User"

    async def test_contact_full_name(self, seeded_db):
        contact = await Contact.get(pk=1)
        assert contact.full_name == "John Smith"

    async def test_pk_property(self, seeded_db):
        user = await User.get(pk=1)
        assert user.pk == 1
        assert user.pk == user.id


# ═════════════════════════════════════════════════════════════════════════════
#  4. SERVICE LAYER TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCRMAuthService:
    """Regression tests for CRMAuthService using ORM."""

    async def test_register_creates_user(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.register({
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        })

        assert result["email"] == "newuser@test.com"
        assert "password_hash" not in result
        assert result["full_name"] == "New User"

        # Verify persisted via ORM
        user = await User.get(email="newuser@test.com")
        assert user is not None

    async def test_register_duplicate_raises(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        from modules.shared.faults import UserAlreadyExistsFault
        svc = CRMAuthService(auth_manager=None, cache=None)

        with pytest.raises(UserAlreadyExistsFault):
            await svc.register({
                "email": "admin@crm.dev",  # already exists
                "password": "Pass123!",
                "first_name": "Dup",
                "last_name": "User",
            })

    async def test_login_success(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.login("admin@crm.dev", "password123")
        assert "user" in result
        assert result["user"]["email"] == "admin@crm.dev"

    async def test_login_wrong_password_raises(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        from modules.shared.faults import InvalidCredentialsFault
        svc = CRMAuthService(auth_manager=None, cache=None)

        with pytest.raises(InvalidCredentialsFault):
            await svc.login("admin@crm.dev", "wrongpass")

    async def test_login_nonexistent_user_raises(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        from modules.shared.faults import InvalidCredentialsFault
        svc = CRMAuthService(auth_manager=None, cache=None)

        with pytest.raises(InvalidCredentialsFault):
            await svc.login("nobody@crm.dev", "password")

    async def test_login_inactive_user_raises(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        from modules.shared.faults import InvalidCredentialsFault
        svc = CRMAuthService(auth_manager=None, cache=None)

        with pytest.raises(InvalidCredentialsFault):
            await svc.login("inactive@crm.dev", "password123")

    async def test_login_updates_last_login(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        user_before = await User.get(pk=1)
        assert user_before.last_login is None

        await svc.login("admin@crm.dev", "password123")

        user_after = await User.get(pk=1)
        assert user_after.last_login is not None

    async def test_get_user_by_id(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.get_user_by_id(1)
        assert result is not None
        assert result["email"] == "admin@crm.dev"

    async def test_get_user_by_id_not_found(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.get_user_by_id(99999)
        assert result is None

    async def test_get_all_users_excludes_inactive(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.get_all_users()
        assert isinstance(result, list)
        assert len(result) == 3  # excludes inactive user

    async def test_update_profile(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.update_profile(1, {"first_name": "AdminUpdated"})
        assert result["first_name"] == "AdminUpdated"

        # Verify persisted
        user = await User.get(pk=1)
        assert user.first_name == "AdminUpdated"

    async def test_update_profile_not_found(self, seeded_db):
        from modules.crm_auth.services import CRMAuthService
        svc = CRMAuthService(auth_manager=None, cache=None)

        result = await svc.update_profile(99999, {"first_name": "Ghost"})
        assert result is None


class TestContactService:
    """Regression tests for ContactService using ORM."""

    async def test_list_contacts(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.list_contacts()
        assert "items" in result
        assert "total" in result
        assert result["total"] == 3

    async def test_list_contacts_with_status_filter(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.list_contacts(status="customer")
        assert result["total"] == 1
        assert result["items"][0]["first_name"] == "John"

    async def test_list_contacts_with_search(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.list_contacts(search="John")
        assert result["total"] >= 1
        assert any(c["first_name"] == "John" for c in result["items"])

    async def test_list_contacts_pagination(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.list_contacts(per_page=2, page=1)
        assert len(result["items"]) == 2
        assert result["total"] == 3
        assert result["total_pages"] == 2

    async def test_get_contact(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.get_contact(1)
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"
        assert "company_name" in result  # enriched via ORM
        assert result["company_name"] == "Acme Corp"

    async def test_get_contact_not_found(self, seeded_db):
        from modules.contacts.services import ContactService
        from modules.shared.faults import ContactNotFoundFault
        svc = ContactService(cache=None)

        with pytest.raises(ContactNotFoundFault):
            await svc.get_contact(99999)

    async def test_create_contact(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.create_contact({
            "first_name": "New",
            "last_name": "Contact",
            "email": "new@test.com",
        })
        assert result["first_name"] == "New"
        assert result["email"] == "new@test.com"
        assert result["id"] is not None

    async def test_create_contact_duplicate_raises(self, seeded_db):
        from modules.contacts.services import ContactService
        from modules.shared.faults import DuplicateContactFault
        svc = ContactService(cache=None)

        with pytest.raises(DuplicateContactFault):
            await svc.create_contact({
                "first_name": "Dup",
                "last_name": "Contact",
                "email": "john@acme.com",  # already exists
            })

    async def test_update_contact(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.update_contact(1, {"job_title": "CFO"})
        assert result["job_title"] == "CFO"

        # Verify persisted
        contact = await Contact.get(pk=1)
        assert contact.job_title == "CFO"

    async def test_delete_contact(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        result = await svc.delete_contact(1)
        assert result is True

        # Verify gone
        assert await Contact.get(pk=1) is None

    async def test_delete_contact_not_found(self, seeded_db):
        from modules.contacts.services import ContactService
        from modules.shared.faults import ContactNotFoundFault
        svc = ContactService(cache=None)

        with pytest.raises(ContactNotFoundFault):
            await svc.delete_contact(99999)

    async def test_contact_stats(self, seeded_db):
        from modules.contacts.services import ContactService
        svc = ContactService(cache=None)

        stats = await svc.get_contact_stats()
        assert stats["total"] == 3
        assert "by_status" in stats
        assert "by_source" in stats
        assert "recent" in stats
        assert isinstance(stats["recent"], list)


class TestCompanyService:
    """Regression tests for CompanyService using ORM."""

    async def test_list_companies(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        result = await svc.list_companies()
        assert "items" in result
        assert result["total"] == 2

    async def test_get_company(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        result = await svc.get_company(1)
        assert result["name"] == "Acme Corp"

    async def test_get_company_not_found(self, seeded_db):
        from modules.companies.services import CompanyService
        from modules.shared.faults import CompanyNotFoundFault
        svc = CompanyService(cache=None)

        with pytest.raises(CompanyNotFoundFault):
            await svc.get_company(99999)

    async def test_create_company(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        result = await svc.create_company({
            "name": "NewCorp", "industry": "finance", "size": "11-50",
        })
        assert result["name"] == "NewCorp"
        assert result["id"] is not None

    async def test_update_company(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        result = await svc.update_company(1, {"industry": "finance"})
        assert result["industry"] == "finance"

    async def test_delete_company(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        result = await svc.delete_company(1)
        assert result is True
        assert await Company.get(pk=1) is None

    async def test_company_stats(self, seeded_db):
        from modules.companies.services import CompanyService
        svc = CompanyService(cache=None)

        stats = await svc.get_company_stats()
        assert stats["total"] == 2
        assert "by_industry" in stats


class TestDealService:
    """Regression tests for DealService using ORM."""

    async def test_list_deals(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.list_deals()
        assert "items" in result
        assert result["total"] == 5

    async def test_list_deals_filter_by_stage(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.list_deals(stage="negotiation")
        assert result["total"] == 1
        assert result["items"][0]["title"] == "Acme Enterprise License"

    async def test_list_deals_with_search(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.list_deals(search="Acme")
        assert result["total"] >= 1

    async def test_get_deal(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.get_deal(1)
        assert result["title"] == "Acme Enterprise License"
        assert float(result["value"]) == 120000
        # Enriched fields via ORM
        assert "contact" in result
        assert "company" in result
        assert "tasks" in result
        assert "notes" in result

    async def test_get_deal_not_found(self, seeded_db):
        from modules.deals.services import DealService
        from modules.shared.faults import DealNotFoundFault
        svc = DealService(cache=None)

        with pytest.raises(DealNotFoundFault):
            await svc.get_deal(99999)

    async def test_create_deal(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.create_deal({
            "title": "New Deal", "value": 50000, "stage": "discovery",
        })
        assert result["title"] == "New Deal"
        assert result["value"] == 50000
        assert result["probability"] == 10  # auto-set from stage

    async def test_update_deal_stage_transition(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        # discovery → qualification is valid
        deal = await Deal.create(
            title="Stage Test", value=10000, stage="discovery", probability=10,
        )
        result = await svc.update_deal(deal.pk, {"stage": "qualification"})
        assert result["stage"] == "qualification"
        assert result["probability"] == 25  # auto-updated

    async def test_update_deal_invalid_stage_transition(self, seeded_db):
        from modules.deals.services import DealService
        from modules.shared.faults import InvalidStageTransitionFault
        svc = DealService(cache=None)

        # discovery → closed_won is invalid
        deal = await Deal.create(
            title="Invalid Stage", value=10000, stage="discovery", probability=10,
        )
        with pytest.raises(InvalidStageTransitionFault):
            await svc.update_deal(deal.pk, {"stage": "closed_won"})

    async def test_update_deal_close_sets_date(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        # negotiation → closed_won is valid
        deal = await Deal.create(
            title="Close Test", value=50000, stage="negotiation", probability=75,
        )
        result = await svc.update_deal(deal.pk, {"stage": "closed_won"})
        assert result["stage"] == "closed_won"
        assert result["actual_close_date"] is not None

    async def test_delete_deal(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        result = await svc.delete_deal(1)
        assert result is True
        assert await Deal.get(pk=1) is None

    async def test_pipeline_stats(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        stats = await svc.get_pipeline_stats()
        assert "total" in stats
        assert stats["total"] == 5
        assert "total_pipeline_value" in stats
        assert "won_value" in stats
        assert "by_stage" in stats
        assert isinstance(stats["by_stage"], dict)

    async def test_pipeline_board(self, seeded_db):
        from modules.deals.services import DealService
        svc = DealService(cache=None)

        board = await svc.get_pipeline_board()
        assert isinstance(board, dict)
        assert "discovery" in board
        assert "negotiation" in board
        assert "closed_won" in board
        # Check deals in correct stages
        assert len(board["negotiation"]) == 1
        assert board["negotiation"][0]["title"] == "Acme Enterprise License"


class TestTaskService:
    """Regression tests for TaskService using ORM."""

    async def test_list_tasks(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.list_tasks()
        assert "items" in result
        assert result["total"] == 4

    async def test_list_tasks_filter_status(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.list_tasks(status="pending")
        assert result["total"] == 1

    async def test_get_task(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.get_task(1)
        assert result["title"] == "Follow up with John Smith"
        assert "assigned_to" in result  # enriched via ORM

    async def test_get_task_not_found(self, seeded_db):
        from modules.tasks.services import TaskService
        from modules.shared.faults import TaskNotFoundFault
        svc = TaskService(cache=None)

        with pytest.raises(TaskNotFoundFault):
            await svc.get_task(99999)

    async def test_create_task(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.create_task({
            "title": "New Task", "status": "pending", "priority": "high",
            "task_type": "call",
        })
        assert result["title"] == "New Task"

    async def test_update_task_mark_completed(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.update_task(1, {"status": "completed"})
        assert result["status"] == "completed"
        assert result.get("completed_at") is not None

    async def test_delete_task(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        result = await svc.delete_task(1)
        assert result is True
        assert await Task.get(pk=1) is None

    async def test_task_stats(self, seeded_db):
        from modules.tasks.services import TaskService
        svc = TaskService(cache=None)

        stats = await svc.get_task_stats()
        assert stats["total"] == 4
        assert "by_status" in stats
        assert "by_priority" in stats
        assert "by_type" in stats


class TestCRMMailService:
    """Regression tests for CRMMailService using ORM."""

    async def test_list_campaigns(self, seeded_db):
        from modules.crm_mail.services import CRMMailService
        svc = CRMMailService(cache=None)

        result = await svc.list_campaigns()
        assert "items" in result
        assert result["total"] == 1

    async def test_get_campaign(self, seeded_db):
        from modules.crm_mail.services import CRMMailService
        svc = CRMMailService(cache=None)

        result = await svc.get_campaign(1)
        assert result["name"] == "Q1 Newsletter"

    async def test_get_campaign_not_found(self, seeded_db):
        from modules.crm_mail.services import CRMMailService
        from modules.shared.faults import CampaignNotFoundFault
        svc = CRMMailService(cache=None)

        with pytest.raises(CampaignNotFoundFault):
            await svc.get_campaign(99999)

    async def test_create_campaign(self, seeded_db):
        from modules.crm_mail.services import CRMMailService
        svc = CRMMailService(cache=None)

        result = await svc.create_campaign({
            "name": "Q2 Campaign",
            "subject": "Q2 Update",
            "body_html": "<h1>Q2</h1>",
        }, sender_id=1)
        assert result["name"] == "Q2 Campaign"
        assert result["status"] == "draft"
        assert result["sender_id"] == 1


class TestAnalyticsService:
    """Regression tests for AnalyticsService using ORM."""

    async def test_get_dashboard_data(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        assert "kpis" in data
        assert "pipeline" in data
        assert "recent_activities" in data
        assert "tasks_overview" in data
        assert "revenue_by_stage" in data
        assert "contacts_by_status" in data
        assert "top_deals" in data
        assert "team_performance" in data

    async def test_kpis_counts(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        kpis = data["kpis"]
        assert kpis["total_contacts"] == 3
        assert kpis["total_companies"] == 2
        assert kpis["total_deals"] == 5
        assert kpis["active_deals"] == 3  # 3 not closed
        assert kpis["pipeline_value"] > 0
        assert kpis["won_revenue"] == 80000.0  # Won Deal = 80k
        assert "win_rate" in kpis
        assert kpis["win_rate"] > 0  # 1 won / 2 closed total = 50%

    async def test_pipeline_summary(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        pipeline = data["pipeline"]
        assert isinstance(pipeline, list)
        assert len(pipeline) > 0
        # Each entry has stage, count, value
        for entry in pipeline:
            assert "stage" in entry
            assert "count" in entry
            assert "value" in entry

    async def test_tasks_overview(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        tasks = data["tasks_overview"]
        assert "by_status" in tasks
        assert "overdue" in tasks

    async def test_top_deals(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        top_deals = data["top_deals"]
        assert isinstance(top_deals, list)
        # Should have open deals sorted by value desc
        if len(top_deals) > 1:
            assert top_deals[0]["value"] >= top_deals[1]["value"]

    async def test_team_performance(self, seeded_db):
        from modules.analytics.services import AnalyticsService
        svc = AnalyticsService(cache=None)

        data = await svc.get_dashboard_data()
        team = data["team_performance"]
        assert isinstance(team, list)
        for member in team:
            assert "name" in member
            assert "deals" in member
            assert "won_revenue" in member


# ═════════════════════════════════════════════════════════════════════════════
#  5. SIGNAL TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSignals:
    """Test that ORM signals fire correctly."""

    async def test_post_save_contact_creates_activity(self, seeded_db):
        """Creating a contact should auto-log an activity via post_save signal."""
        # Count activities before
        before_count = await Activity.objects.count()

        await Contact.create(
            first_name="Signal", last_name="Test", email="signal@test.com",
        )

        # Activity count should increase
        after_count = await Activity.objects.count()
        assert after_count > before_count

    async def test_post_save_deal_creates_activity(self, seeded_db):
        before_count = await Activity.objects.count()

        await Deal.create(
            title="Signal Deal", value=10000, stage="discovery", probability=10,
        )

        after_count = await Activity.objects.count()
        assert after_count > before_count

    async def test_post_save_task_creates_activity(self, seeded_db):
        before_count = await Activity.objects.count()

        await Task.create(
            title="Signal Task", status="pending", priority="medium", task_type="other",
        )

        after_count = await Activity.objects.count()
        assert after_count > before_count


# ═════════════════════════════════════════════════════════════════════════════
#  6. EDGE CASES & DATA INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and data integrity checks."""

    async def test_empty_table_count(self, db):
        """count() returns 0 on empty table."""
        count = await User.objects.count()
        assert count == 0

    async def test_empty_table_all(self, db):
        """all() returns empty list on empty table."""
        users = await User.objects.all()
        assert users == []

    async def test_empty_table_exists(self, db):
        """exists() returns False on empty table."""
        exists = await User.objects.filter(email="any@test.com").exists()
        assert exists is False

    async def test_empty_table_first(self, db):
        """first() returns None on empty table."""
        user = await User.objects.first()
        assert user is None

    async def test_create_with_nullable_fields(self, db):
        """Nullable fields can be omitted from create."""
        contact = await Contact.create(
            first_name="Min", last_name="Contact", email="min@test.com",
        )
        assert contact.pk is not None
        assert contact.phone is None
        assert contact.company_id is None

    async def test_filter_chaining(self, seeded_db):
        """Multiple filter calls are AND-combined."""
        contacts = await Contact.objects.filter(
            status="customer"
        ).filter(
            source="referral"
        ).all()
        assert len(contacts) == 1
        assert contacts[0].first_name == "John"

    async def test_order_with_limit(self, seeded_db):
        """order + limit produces correctly sorted subset."""
        deals = await Deal.objects.order("-value").limit(2).all()
        assert len(deals) == 2
        assert deals[0].value >= deals[1].value

    async def test_raw_db_access_via_model(self, seeded_db):
        """Model._get_db() provides raw DB for complex aggregates."""
        db = Deal._get_db()
        row = await db.fetch_one(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(value), 0) as total FROM crm_deals"
        )
        assert row["cnt"] == 5
        assert row["total"] > 0

    async def test_hybrid_orm_and_raw(self, seeded_db):
        """
        Services use ORM for CRUD and raw SQL for aggregates,
        both through the same DB instance.
        """
        # ORM path
        deal = await Deal.get(pk=1)
        assert deal is not None

        # Raw path through same DB
        db = Deal._get_db()
        row = await db.fetch_one(
            "SELECT SUM(value) as total FROM crm_deals WHERE stage = ?",
            ["closed_won"]
        )
        assert row["total"] == 80000

    async def test_concurrent_creates(self, db):
        """Multiple concurrent ORM creates don't conflict."""
        tasks = []
        for i in range(10):
            tasks.append(User.create(
                email=f"concurrent{i}@test.com", password_hash="h",
                first_name=f"User{i}", last_name="Test",
            ))
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        pks = [u.pk for u in results]
        assert len(set(pks)) == 10  # All unique PKs

    async def test_update_after_create(self, db):
        """Save immediately after create updates the same record."""
        user = await User.create(
            email="updateafter@test.com", password_hash="h",
            first_name="Before", last_name="Test",
        )
        pk = user.pk

        user.first_name = "After"
        await user.save(update_fields=["first_name"])

        user2 = await User.get(pk=pk)
        assert user2.first_name == "After"
        assert user2.email == "updateafter@test.com"

    async def test_filter_with_order_limit_offset(self, seeded_db):
        """Full query chain: filter → order → limit → offset → all."""
        result = await Deal.objects.filter(
            priority="high"
        ).order("-value").limit(10).offset(0).all()
        assert isinstance(result, list)
        for deal in result:
            assert deal.priority == "high"


# ═════════════════════════════════════════════════════════════════════════════
#  7. DB SETUP / SEEDING TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDBSetup:
    """Test the db_setup module uses ORM for seeding."""

    async def test_seed_data_creates_users(self, db):
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        count = await User.objects.count()
        assert count == 5  # 5 seeded users

    async def test_seed_data_creates_contacts(self, db):
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        count = await Contact.objects.count()
        assert count == 10  # 10 seeded contacts

    async def test_seed_data_creates_companies(self, db):
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        count = await Company.objects.count()
        assert count == 6

    async def test_seed_data_creates_deals(self, db):
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        count = await Deal.objects.count()
        assert count == 8

    async def test_seed_data_creates_tasks(self, db):
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        count = await Task.objects.count()
        assert count == 8

    async def test_seed_data_idempotent(self, db):
        """Running seed_data twice doesn't duplicate data."""
        from modules.shared.db_setup import seed_data
        await seed_data(db)
        await seed_data(db)  # second call should skip

        count = await User.objects.count()
        assert count == 5  # still 5, not 10

    async def test_seed_data_user_passwords_hashed(self, db):
        """Seeded users have hashed passwords, not plaintext."""
        from modules.shared.db_setup import seed_data
        await seed_data(db)

        user = await User.get(email="admin@crm.dev")
        assert user.password_hash != "password123"
        assert len(user.password_hash) > 20  # It's a hash


# ═════════════════════════════════════════════════════════════════════════════
#  8. NO RAW SQL IN SERVICES (META-TESTS)
# ═════════════════════════════════════════════════════════════════════════════

class TestNoRawSQLLeaks:
    """
    Meta-tests: verify services don't use self.db
    (all DB access goes through ORM or Model._get_db()).
    """

    def test_auth_service_no_db_param(self):
        """CRMAuthService.__init__ does NOT accept a db parameter."""
        from modules.crm_auth.services import CRMAuthService
        import inspect
        sig = inspect.signature(CRMAuthService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_contact_service_no_db_param(self):
        from modules.contacts.services import ContactService
        import inspect
        sig = inspect.signature(ContactService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_company_service_no_db_param(self):
        from modules.companies.services import CompanyService
        import inspect
        sig = inspect.signature(CompanyService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_deal_service_no_db_param(self):
        from modules.deals.services import DealService
        import inspect
        sig = inspect.signature(DealService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_task_service_no_db_param(self):
        from modules.tasks.services import TaskService
        import inspect
        sig = inspect.signature(TaskService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_mail_service_no_db_param(self):
        from modules.crm_mail.services import CRMMailService
        import inspect
        sig = inspect.signature(CRMMailService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_analytics_service_no_db_param(self):
        from modules.analytics.services import AnalyticsService
        import inspect
        sig = inspect.signature(AnalyticsService.__init__)
        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_services_have_no_self_db_attribute(self):
        """No service stores self.db — all DB access is through ORM."""
        from modules.crm_auth.services import CRMAuthService
        from modules.contacts.services import ContactService
        from modules.companies.services import CompanyService
        from modules.deals.services import DealService
        from modules.tasks.services import TaskService
        from modules.crm_mail.services import CRMMailService
        from modules.analytics.services import AnalyticsService

        services = [
            CRMAuthService(auth_manager=None, cache=None),
            ContactService(cache=None),
            CompanyService(cache=None),
            DealService(cache=None),
            TaskService(cache=None),
            CRMMailService(cache=None),
            AnalyticsService(cache=None),
        ]
        for svc in services:
            assert not hasattr(svc, "db"), f"{svc.__class__.__name__} still has self.db"

    def test_no_raw_sql_in_service_source_code(self):
        """Verify NO raw SQL patterns exist in any CRM service source code."""
        import pathlib

        service_files = [
            "myapp/modules/crm_auth/services.py",
            "myapp/modules/contacts/services.py",
            "myapp/modules/companies/services.py",
            "myapp/modules/deals/services.py",
            "myapp/modules/tasks/services.py",
            "myapp/modules/crm_mail/services.py",
            "myapp/modules/analytics/services.py",
        ]

        forbidden_patterns = [
            "_get_db()",
            "fetch_all",
            "fetch_one",
            "db.execute",
            "AquiliaDatabase",
        ]

        for fpath in service_files:
            p = pathlib.Path(fpath)
            if not p.exists():
                continue
            source = p.read_text()
            for pattern in forbidden_patterns:
                assert pattern not in source, (
                    f"{fpath} still contains raw SQL pattern '{pattern}'"
                )
