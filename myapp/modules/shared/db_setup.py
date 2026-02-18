"""
CRM Database Setup & Seeding
=============================
Creates all tables and seeds initial data.
Fully wired through the Aquilia ORM — uses Model.create() for seeding.
"""

from aquilia.db import AquiliaDatabase
from aquilia.auth import PasswordHasher

from modules.shared.models import (
    User, Contact, Company, Deal, Task, Activity, Note, EmailCampaign,
)


async def create_tables(db: AquiliaDatabase) -> None:
    """Create all CRM tables using model SQL generation."""
    models = [User, Contact, Company, Deal, Task, Activity, Note, EmailCampaign]

    for model_cls in models:
        sql = model_cls.generate_create_table_sql(dialect="sqlite")
        await db.execute(sql)

        # Create indexes
        for idx_sql in model_cls.generate_index_sql(dialect="sqlite"):
            try:
                await db.execute(idx_sql)
            except Exception:
                pass  # Index may already exist

        # Create M2M tables
        for m2m_sql in model_cls.generate_m2m_sql(dialect="sqlite"):
            try:
                await db.execute(m2m_sql)
            except Exception:
                pass


async def seed_data(db) -> None:
    """Seed initial CRM data for development using the ORM."""
    hasher = PasswordHasher()

    # Check if already seeded via ORM
    user_count = await User.objects.count()
    if user_count > 0:
        print("[CRM] Database already seeded — skipping.")
        return

    # --- Users (via ORM) ---
    users_data = [
        ("admin@crm.dev", "Admin", "User", "admin"),
        ("sarah@crm.dev", "Sarah", "Johnson", "manager"),
        ("mike@crm.dev", "Mike", "Chen", "rep"),
        ("emma@crm.dev", "Emma", "Wilson", "rep"),
        ("viewer@crm.dev", "View", "Only", "viewer"),
    ]
    created_users = []
    for email, first, last, role in users_data:
        pw = hasher.hash("password123")
        user = await User.create(
            email=email,
            password_hash=pw,
            first_name=first,
            last_name=last,
            role=role,
            is_active=True,
        )
        created_users.append(user)

    # --- Companies (via ORM) ---
    companies_data = [
        dict(name="Acme Corp", industry="technology", size="51-200", website="https://acme.com",
             email="info@acme.com", phone="+1-555-0100", city="San Francisco", state="CA",
             country="USA", annual_revenue=5000000.00, description="Leading tech solutions provider", owner_id=2),
        dict(name="GlobalHealth Inc", industry="healthcare", size="201-1000", website="https://globalhealth.com",
             email="contact@globalhealth.com", phone="+1-555-0200", city="Boston", state="MA",
             country="USA", annual_revenue=25000000.00, description="Healthcare innovation company", owner_id=2),
        dict(name="EduForward", industry="education", size="11-50", website="https://eduforward.io",
             email="hello@eduforward.io", city="Austin", state="TX",
             country="USA", annual_revenue=1200000.00, description="EdTech startup", owner_id=3),
        dict(name="FinanceFirst", industry="finance", size="1000+", website="https://financefirst.com",
             email="biz@financefirst.com", city="New York", state="NY",
             country="USA", annual_revenue=100000000.00, description="Global financial services", owner_id=2),
        dict(name="RetailNova", industry="retail", size="51-200",
             city="Chicago", state="IL", country="USA", annual_revenue=8000000.00,
             description="E-commerce platform", owner_id=4),
        dict(name="BuildRight Ltd", industry="manufacturing", size="201-1000",
             city="Detroit", state="MI", country="USA", annual_revenue=45000000.00,
             description="Industrial manufacturing", owner_id=3),
    ]
    for cdata in companies_data:
        await Company.create(**cdata)

    # --- Contacts (via ORM) ---
    contacts_data = [
        dict(first_name="John", last_name="Smith", email="john@acme.com", phone="+1-555-1001",
             job_title="CTO", company_id=1, status="customer", source="referral",
             city="San Francisco", country="USA", score=85, owner_id=3),
        dict(first_name="Lisa", last_name="Park", email="lisa@globalhealth.com", phone="+1-555-1002",
             job_title="VP of Operations", company_id=2, status="qualified", source="linkedin",
             city="Boston", country="USA", score=72, owner_id=3),
        dict(first_name="David", last_name="Brown", email="david@eduforward.io", phone="+1-555-1003",
             job_title="CEO", company_id=3, status="prospect", source="trade_show",
             city="Austin", country="USA", score=60, owner_id=4),
        dict(first_name="Maria", last_name="Garcia", email="maria@financefirst.com", phone="+1-555-1004",
             job_title="Procurement Director", company_id=4, status="qualified", source="cold_call",
             city="New York", country="USA", score=90, owner_id=3),
        dict(first_name="James", last_name="Wilson", email="james@retailnova.com", phone="+1-555-1005",
             job_title="Head of Tech", company_id=5, status="lead", source="website",
             city="Chicago", country="USA", score=45, owner_id=4),
        dict(first_name="Anna", last_name="Taylor", email="anna@buildright.com", phone="+1-555-1006",
             job_title="Operations Manager", company_id=6, status="lead", source="email_campaign",
             city="Detroit", country="USA", score=30, owner_id=3),
        dict(first_name="Robert", last_name="Lee", email="robert@techstartup.io",
             job_title="Founder", status="prospect", source="linkedin",
             city="Seattle", country="USA", score=55, owner_id=4),
        dict(first_name="Sophie", last_name="Martin", email="sophie@designco.fr",
             job_title="Creative Director", status="lead", source="website",
             city="Paris", country="France", score=40, owner_id=4),
        dict(first_name="Chen", last_name="Wei", email="chen@dragontrade.cn",
             job_title="Import Manager", status="qualified", source="trade_show",
             city="Shanghai", country="China", score=78, owner_id=3),
        dict(first_name="Priya", last_name="Patel", email="priya@innovateind.in",
             job_title="VP Engineering", status="customer", source="referral",
             city="Mumbai", country="India", score=92, owner_id=3),
    ]
    for cdata in contacts_data:
        await Contact.create(**cdata)

    # --- Deals (via ORM) ---
    deals_data = [
        dict(title="Acme Enterprise License", value=120000, stage="negotiation", probability=75,
             contact_id=1, company_id=1, owner_id=3, priority="high",
             description="Annual enterprise software license", source="Existing Customer"),
        dict(title="GlobalHealth Platform Integration", value=350000, stage="proposal", probability=50,
             contact_id=2, company_id=2, owner_id=3, priority="critical",
             description="Full platform integration project", source="LinkedIn"),
        dict(title="EduForward Starter Pack", value=15000, stage="discovery", probability=20,
             contact_id=3, company_id=3, owner_id=4, priority="medium",
             description="Initial trial package for EdTech", source="Trade Show"),
        dict(title="FinanceFirst Security Suite", value=500000, stage="qualification", probability=35,
             contact_id=4, company_id=4, owner_id=3, priority="critical",
             description="Enterprise security compliance suite", source="Cold Outreach"),
        dict(title="RetailNova E-commerce Addon", value=45000, stage="proposal", probability=60,
             contact_id=5, company_id=5, owner_id=4, priority="medium",
             description="E-commerce enhancement package"),
        dict(title="BuildRight IoT Monitoring", value=200000, stage="discovery", probability=15,
             contact_id=6, company_id=6, owner_id=3, priority="low",
             description="IoT monitoring for manufacturing floor"),
        dict(title="Innovate India SaaS Deal", value=80000, stage="closed_won", probability=100,
             contact_id=10, owner_id=3, priority="high",
             description="SaaS subscription — closed!"),
        dict(title="DragonTrade Export Tools", value=65000, stage="negotiation", probability=70,
             contact_id=9, owner_id=3, priority="high",
             description="Export management tooling"),
    ]
    for ddata in deals_data:
        await Deal.create(**ddata)

    # --- Tasks (via ORM) ---
    tasks_data = [
        dict(title="Follow up with John Smith", status="pending", priority="high", task_type="call",
             assigned_to_id=3, created_by_id=2, contact_id=1, deal_id=1,
             description="Call to discuss contract renewal terms"),
        dict(title="Send proposal to GlobalHealth", status="in_progress", priority="urgent", task_type="email",
             assigned_to_id=3, created_by_id=2, contact_id=2, deal_id=2,
             description="Prepare and send formal proposal document"),
        dict(title="Demo for EduForward", status="pending", priority="medium", task_type="demo",
             assigned_to_id=4, created_by_id=2, contact_id=3, deal_id=3,
             description="Product demo for CEO David Brown"),
        dict(title="Negotiate FinanceFirst terms", status="pending", priority="high", task_type="meeting",
             assigned_to_id=3, created_by_id=1, contact_id=4, deal_id=4,
             description="Meeting with procurement team"),
        dict(title="Update CRM data for Q1", status="completed", priority="low", task_type="other",
             assigned_to_id=4, created_by_id=2,
             description="Clean up and update Q1 contact data"),
        dict(title="Prepare monthly report", status="pending", priority="medium", task_type="other",
             assigned_to_id=2, created_by_id=1,
             description="Generate monthly sales pipeline report"),
        dict(title="Onboard Priya Patel", status="completed", priority="high", task_type="meeting",
             assigned_to_id=3, created_by_id=2, contact_id=10,
             description="Customer onboarding for Innovate India"),
        dict(title="Cold email campaign review", status="in_progress", priority="medium", task_type="email",
             assigned_to_id=4, created_by_id=2,
             description="Review and approve Q2 cold email campaign copy"),
    ]
    for tdata in tasks_data:
        await Task.create(**tdata)

    # --- Notes (via ORM) ---
    notes_data = [
        dict(content="John expressed strong interest in upgrading to enterprise tier. Needs board approval by EOQ.",
             entity_type="contact", entity_id=1, author_id=3, is_pinned=True),
        dict(content="GlobalHealth has strict compliance requirements. Need to involve legal team.",
             entity_type="deal", entity_id=2, author_id=3, is_pinned=True),
        dict(content="EduForward is bootstrapped — price sensitivity is high. Offer extended trial.",
             entity_type="company", entity_id=3, author_id=4, is_pinned=False),
        dict(content="FinanceFirst wants SOC2 certification proof before proceeding.",
             entity_type="deal", entity_id=4, author_id=3, is_pinned=True),
        dict(content="Good initial call with Anna. She wants to see ROI calculations.",
             entity_type="contact", entity_id=6, author_id=3, is_pinned=False),
    ]
    for ndata in notes_data:
        await Note.create(**ndata)

    print("[CRM] ✓ Database seeded with sample data.")


async def setup_database(db: AquiliaDatabase) -> None:
    """Full database setup: create tables + seed."""
    await create_tables(db)
    await seed_data(db)
