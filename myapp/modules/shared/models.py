"""
CRM Shared Models
=================
All database models for the CRM: User, Contact, Company, Deal, Task, Activity, Note.
Uses Aquilia ORM with full field types, relationships, signals, and validation.
"""

from aquilia.models import Model
from aquilia.models.fields import (
    CharField,
    EmailField,
    TextField,
    IntegerField,
    DecimalField,
    BooleanField,
    DateTimeField,
    DateField,
    ForeignKey,
    SlugField,
    URLField,
)
from aquilia.models.deletion import CASCADE, SET_NULL
from aquilia.models.signals import pre_save, post_save, receiver


# =====================================================================
#  User (CRM Agent / Sales Rep)
# =====================================================================
class User(Model):
    """CRM system user — sales reps, managers, admins."""

    table = "crm_users"

    email = EmailField(unique=True, db_index=True)
    password_hash = CharField(max_length=255)
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    role = CharField(
        max_length=20,
        choices=[
            ("admin", "Admin"),
            ("manager", "Sales Manager"),
            ("rep", "Sales Rep"),
            ("viewer", "Viewer"),
        ],
        default="rep",
    )
    avatar_url = URLField(null=True, blank=True)
    phone = CharField(max_length=30, null=True, blank=True)
    is_active = BooleanField(default=True)
    last_login = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_safe_dict(self) -> dict:
        """Return user dict without password hash."""
        d = self.to_dict()
        d.pop("password_hash", None)
        d["full_name"] = self.full_name
        return d


# =====================================================================
#  Contact
# =====================================================================
class Contact(Model):
    """Individual contact / lead in the CRM."""

    table = "crm_contacts"

    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    email = EmailField(unique=True, db_index=True)
    phone = CharField(max_length=30, null=True, blank=True)
    mobile = CharField(max_length=30, null=True, blank=True)
    job_title = CharField(max_length=150, null=True, blank=True)
    department = CharField(max_length=100, null=True, blank=True)
    source = CharField(
        max_length=30,
        choices=[
            ("website", "Website"),
            ("referral", "Referral"),
            ("linkedin", "LinkedIn"),
            ("cold_call", "Cold Call"),
            ("trade_show", "Trade Show"),
            ("email_campaign", "Email Campaign"),
            ("other", "Other"),
        ],
        default="website",
    )
    status = CharField(
        max_length=20,
        choices=[
            ("lead", "Lead"),
            ("prospect", "Prospect"),
            ("qualified", "Qualified"),
            ("customer", "Customer"),
            ("churned", "Churned"),
        ],
        default="lead",
    )
    company_id = IntegerField(null=True, blank=True, db_index=True)
    owner_id = IntegerField(null=True, blank=True, db_index=True)
    address = TextField(null=True, blank=True)
    city = CharField(max_length=100, null=True, blank=True)
    state = CharField(max_length=100, null=True, blank=True)
    country = CharField(max_length=100, null=True, blank=True)
    zip_code = CharField(max_length=20, null=True, blank=True)
    notes = TextField(null=True, blank=True)
    tags = CharField(max_length=500, null=True, blank=True)
    score = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# =====================================================================
#  Company / Organization
# =====================================================================
class Company(Model):
    """Company / organization entity."""

    table = "crm_companies"

    name = CharField(max_length=255, unique=True, db_index=True)
    industry = CharField(
        max_length=30,
        choices=[
            ("technology", "Technology"),
            ("finance", "Finance"),
            ("healthcare", "Healthcare"),
            ("education", "Education"),
            ("retail", "Retail"),
            ("manufacturing", "Manufacturing"),
            ("consulting", "Consulting"),
            ("real_estate", "Real Estate"),
            ("media", "Media"),
            ("other", "Other"),
        ],
        default="technology",
    )
    size = CharField(
        max_length=20,
        choices=[
            ("1-10", "1-10"),
            ("11-50", "11-50"),
            ("51-200", "51-200"),
            ("201-1000", "201-1000"),
            ("1000+", "1000+"),
        ],
        default="1-10",
    )
    website = URLField(null=True, blank=True)
    email = EmailField(null=True, blank=True)
    phone = CharField(max_length=30, null=True, blank=True)
    address = TextField(null=True, blank=True)
    city = CharField(max_length=100, null=True, blank=True)
    state = CharField(max_length=100, null=True, blank=True)
    country = CharField(max_length=100, null=True, blank=True)
    zip_code = CharField(max_length=20, null=True, blank=True)
    annual_revenue = DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    description = TextField(null=True, blank=True)
    owner_id = IntegerField(null=True, blank=True, db_index=True)
    logo_url = URLField(null=True, blank=True)
    tags = CharField(max_length=500, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]


# =====================================================================
#  Deal / Opportunity
# =====================================================================
class Deal(Model):
    """Sales deal / opportunity in the pipeline."""

    table = "crm_deals"

    title = CharField(max_length=255, db_index=True)
    value = DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = CharField(max_length=3, default="USD")
    stage = CharField(
        max_length=20,
        choices=[
            ("discovery", "Discovery"),
            ("qualification", "Qualification"),
            ("proposal", "Proposal"),
            ("negotiation", "Negotiation"),
            ("closed_won", "Closed Won"),
            ("closed_lost", "Closed Lost"),
        ],
        default="discovery",
    )
    probability = IntegerField(default=10)
    contact_id = IntegerField(null=True, blank=True, db_index=True)
    company_id = IntegerField(null=True, blank=True, db_index=True)
    owner_id = IntegerField(null=True, blank=True, db_index=True)
    expected_close_date = DateField(null=True, blank=True)
    actual_close_date = DateField(null=True, blank=True)
    source = CharField(max_length=100, null=True, blank=True)
    priority = CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    description = TextField(null=True, blank=True)
    tags = CharField(max_length=500, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


# =====================================================================
#  Task
# =====================================================================
class Task(Model):
    """Task / to-do item linked to contacts, deals, or companies."""

    table = "crm_tasks"

    title = CharField(max_length=255)
    description = TextField(null=True, blank=True)
    status = CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
    )
    priority = CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        default="medium",
    )
    due_date = DateTimeField(null=True, blank=True)
    completed_at = DateTimeField(null=True, blank=True)
    assigned_to_id = IntegerField(null=True, blank=True, db_index=True)
    created_by_id = IntegerField(null=True, blank=True, db_index=True)
    contact_id = IntegerField(null=True, blank=True, db_index=True)
    deal_id = IntegerField(null=True, blank=True, db_index=True)
    company_id = IntegerField(null=True, blank=True, db_index=True)
    task_type = CharField(
        max_length=20,
        choices=[
            ("call", "Call"),
            ("email", "Email"),
            ("meeting", "Meeting"),
            ("follow_up", "Follow Up"),
            ("demo", "Demo"),
            ("other", "Other"),
        ],
        default="other",
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date"]


# =====================================================================
#  Activity Log
# =====================================================================
class Activity(Model):
    """Activity / audit log entry."""

    table = "crm_activities"

    action = CharField(max_length=50)
    entity_type = CharField(max_length=50)
    entity_id = IntegerField(db_index=True)
    user_id = IntegerField(null=True, blank=True, db_index=True)
    description = TextField(null=True, blank=True)
    metadata_json = TextField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# =====================================================================
#  Note
# =====================================================================
class Note(Model):
    """Note attached to any CRM entity."""

    table = "crm_notes"

    content = TextField()
    entity_type = CharField(max_length=50)
    entity_id = IntegerField(db_index=True)
    author_id = IntegerField(null=True, blank=True, db_index=True)
    is_pinned = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


# =====================================================================
#  Email Campaign
# =====================================================================
class EmailCampaign(Model):
    """Email campaign / broadcast."""

    table = "crm_email_campaigns"

    name = CharField(max_length=255)
    subject = CharField(max_length=500)
    body_html = TextField()
    status = CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("sending", "Sending"),
            ("sent", "Sent"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    sender_id = IntegerField(null=True, blank=True, db_index=True)
    scheduled_at = DateTimeField(null=True, blank=True)
    sent_at = DateTimeField(null=True, blank=True)
    recipient_count = IntegerField(default=0)
    open_count = IntegerField(default=0)
    click_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


# =====================================================================
#  Signals — Activity logging on entity changes
# =====================================================================
@receiver(post_save, sender=Contact)
async def log_contact_activity(sender, instance, created, **kwargs):
    """Auto-log activity when a contact is created or updated."""
    action = "contact_created" if created else "contact_updated"
    try:
        await Activity.create(
            action=action,
            entity_type="contact",
            entity_id=instance.pk,
            description=f"Contact {instance.first_name} {instance.last_name} {action.split('_')[1]}",
        )
    except Exception:
        pass


@receiver(post_save, sender=Deal)
async def log_deal_activity(sender, instance, created, **kwargs):
    """Auto-log activity when a deal is created or updated."""
    action = "deal_created" if created else "deal_updated"
    try:
        await Activity.create(
            action=action,
            entity_type="deal",
            entity_id=instance.pk,
            description=f"Deal '{instance.title}' {action.split('_')[1]} — ${instance.value}",
        )
    except Exception:
        pass


@receiver(post_save, sender=Task)
async def log_task_activity(sender, instance, created, **kwargs):
    """Auto-log activity when a task is created or updated."""
    action = "task_created" if created else "task_updated"
    try:
        await Activity.create(
            action=action,
            entity_type="task",
            entity_id=instance.pk,
            description=f"Task '{instance.title}' {action.split('_')[1]}",
        )
    except Exception:
        pass
