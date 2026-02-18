"""
Migration: 20260218_112313_activity_company_contact_and_5_more
Generated: 2026-02-18T11:23:13.146177+00:00
Models: Activity, Company, Contact, Deal, EmailCampaign, Note, Task, User
"""

from aquilia.models.migration_dsl import (
    CreateIndex, CreateModel,
    columns as C,
)


class Meta:
    revision = "20260218_112313"
    slug = "activity_company_contact_and_5_more"
    models = ['Activity', 'Company', 'Contact', 'Deal', 'EmailCampaign', 'Note', 'Task', 'User']


operations = [
    CreateModel(
        name='Activity',
        table='crm_activities',
        fields=[
            C.varchar("action", 50),
            C.varchar("entity_type", 50),
            C.integer("entity_id"),
            C.integer("user_id", null=True),
            C.text("description", null=True),
            C.text("metadata_json", null=True),
            C.timestamp("created_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_activities_entity_id', table='crm_activities',
        columns=['entity_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_activities_user_id', table='crm_activities',
        columns=['user_id'], unique=False,
    ),
    CreateModel(
        name='Company',
        table='crm_companies',
        fields=[
            C.varchar("name", 255, unique=True),
            C.varchar("industry", 30, default='technology'),
            C.varchar("size", 20, default='1-10'),
            C.varchar("website", 200, null=True),
            C.varchar("email", 254, null=True),
            C.varchar("phone", 30, null=True),
            C.text("address", null=True),
            C.varchar("city", 100, null=True),
            C.varchar("state", 100, null=True),
            C.varchar("country", 100, null=True),
            C.varchar("zip_code", 20, null=True),
            C.decimal("annual_revenue", 15, 2, null=True),
            C.text("description", null=True),
            C.integer("owner_id", null=True),
            C.varchar("logo_url", 200, null=True),
            C.varchar("tags", 500, null=True),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_companies_name', table='crm_companies',
        columns=['name'], unique=True,
    ),
    CreateIndex(
        name='idx_crm_companies_owner_id', table='crm_companies',
        columns=['owner_id'], unique=False,
    ),
    CreateModel(
        name='Contact',
        table='crm_contacts',
        fields=[
            C.varchar("first_name", 100),
            C.varchar("last_name", 100),
            C.varchar("email", 254, unique=True),
            C.varchar("phone", 30, null=True),
            C.varchar("mobile", 30, null=True),
            C.varchar("job_title", 150, null=True),
            C.varchar("department", 100, null=True),
            C.varchar("source", 30, default='website'),
            C.varchar("status", 20, default='lead'),
            C.integer("company_id", null=True),
            C.integer("owner_id", null=True),
            C.text("address", null=True),
            C.varchar("city", 100, null=True),
            C.varchar("state", 100, null=True),
            C.varchar("country", 100, null=True),
            C.varchar("zip_code", 20, null=True),
            C.text("notes", null=True),
            C.varchar("tags", 500, null=True),
            C.integer("score", default=0),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_contacts_email', table='crm_contacts',
        columns=['email'], unique=True,
    ),
    CreateIndex(
        name='idx_crm_contacts_company_id', table='crm_contacts',
        columns=['company_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_contacts_owner_id', table='crm_contacts',
        columns=['owner_id'], unique=False,
    ),
    CreateModel(
        name='Deal',
        table='crm_deals',
        fields=[
            C.varchar("title", 255),
            C.decimal("value", 15, 2, default=0),
            C.varchar("currency", 3, default='USD'),
            C.varchar("stage", 20, default='discovery'),
            C.integer("probability", default=10),
            C.integer("contact_id", null=True),
            C.integer("company_id", null=True),
            C.integer("owner_id", null=True),
            C.date("expected_close_date", null=True),
            C.date("actual_close_date", null=True),
            C.varchar("source", 100, null=True),
            C.varchar("priority", 20, default='medium'),
            C.text("description", null=True),
            C.varchar("tags", 500, null=True),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_deals_title', table='crm_deals',
        columns=['title'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_deals_contact_id', table='crm_deals',
        columns=['contact_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_deals_company_id', table='crm_deals',
        columns=['company_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_deals_owner_id', table='crm_deals',
        columns=['owner_id'], unique=False,
    ),
    CreateModel(
        name='EmailCampaign',
        table='crm_email_campaigns',
        fields=[
            C.varchar("name", 255),
            C.varchar("subject", 500),
            C.text("body_html"),
            C.varchar("status", 20, default='draft'),
            C.integer("sender_id", null=True),
            C.timestamp("scheduled_at", null=True),
            C.timestamp("sent_at", null=True),
            C.integer("recipient_count", default=0),
            C.integer("open_count", default=0),
            C.integer("click_count", default=0),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_email_campaigns_sender_id', table='crm_email_campaigns',
        columns=['sender_id'], unique=False,
    ),
    CreateModel(
        name='Note',
        table='crm_notes',
        fields=[
            C.text("content"),
            C.varchar("entity_type", 50),
            C.integer("entity_id"),
            C.integer("author_id", null=True),
            C.integer("is_pinned", default=False),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_notes_entity_id', table='crm_notes',
        columns=['entity_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_notes_author_id', table='crm_notes',
        columns=['author_id'], unique=False,
    ),
    CreateModel(
        name='Task',
        table='crm_tasks',
        fields=[
            C.varchar("title", 255),
            C.text("description", null=True),
            C.varchar("status", 20, default='pending'),
            C.varchar("priority", 20, default='medium'),
            C.timestamp("due_date", null=True),
            C.timestamp("completed_at", null=True),
            C.integer("assigned_to_id", null=True),
            C.integer("created_by_id", null=True),
            C.integer("contact_id", null=True),
            C.integer("deal_id", null=True),
            C.integer("company_id", null=True),
            C.varchar("task_type", 20, default='other'),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_tasks_assigned_to_id', table='crm_tasks',
        columns=['assigned_to_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_tasks_created_by_id', table='crm_tasks',
        columns=['created_by_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_tasks_contact_id', table='crm_tasks',
        columns=['contact_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_tasks_deal_id', table='crm_tasks',
        columns=['deal_id'], unique=False,
    ),
    CreateIndex(
        name='idx_crm_tasks_company_id', table='crm_tasks',
        columns=['company_id'], unique=False,
    ),
    CreateModel(
        name='User',
        table='crm_users',
        fields=[
            C.varchar("email", 254, unique=True),
            C.varchar("password_hash", 255),
            C.varchar("first_name", 100),
            C.varchar("last_name", 100),
            C.varchar("role", 20, default='rep'),
            C.varchar("avatar_url", 200, null=True),
            C.varchar("phone", 30, null=True),
            C.integer("is_active", default=True),
            C.timestamp("last_login", null=True),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
            C.auto("id"),
        ],
    ),
    CreateIndex(
        name='idx_crm_users_email', table='crm_users',
        columns=['email'], unique=True,
    ),
]
