"""
CRM Serializers — Validation & serialization for all CRM entities.
Uses Aquilia Serializer and ModelSerializer with full field validation.
"""

from aquilia.serializers import Serializer, ModelSerializer
from aquilia.serializers.fields import (
    CharField,
    EmailField,
    IntegerField,
    DecimalField,
    BooleanField,
    DateTimeField,
    DateField,
    ChoiceField,
    URLField,
)

from .models import User, Contact, Company, Deal, Task, Activity, Note, EmailCampaign


# =====================================================================
#  Auth Serializers
# =====================================================================
class RegisterSerializer(Serializer):
    """Validate registration input."""
    email = EmailField()
    password = CharField(min_length=8, max_length=128)
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    role = ChoiceField(
        choices=["admin", "manager", "rep", "viewer"],
        required=False,
        default="rep",
    )


class LoginSerializer(Serializer):
    """Validate login input."""
    email = EmailField()
    password = CharField(min_length=1, max_length=128)


class UserSerializer(ModelSerializer):
    """Serialize user output (safe, no password)."""
    class Meta:
        model = User
        fields = "__all__"
        exclude = ["password_hash"]
        read_only_fields = ["id", "created_at", "updated_at", "last_login"]


class UserUpdateSerializer(Serializer):
    """Validate user profile update."""
    first_name = CharField(max_length=100, required=False)
    last_name = CharField(max_length=100, required=False)
    phone = CharField(max_length=30, required=False)
    avatar_url = URLField(required=False)


# =====================================================================
#  Contact Serializers
# =====================================================================
class ContactSerializer(ModelSerializer):
    """Full contact serializer."""
    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ContactCreateSerializer(Serializer):
    """Validate contact creation."""
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    email = EmailField()
    phone = CharField(max_length=30, required=False)
    mobile = CharField(max_length=30, required=False)
    job_title = CharField(max_length=150, required=False)
    department = CharField(max_length=100, required=False)
    source = ChoiceField(
        choices=["website", "referral", "linkedin", "cold_call", "trade_show", "email_campaign", "other"],
        required=False, default="website",
    )
    status = ChoiceField(
        choices=["lead", "prospect", "qualified", "customer", "churned"],
        required=False, default="lead",
    )
    company_id = IntegerField(required=False)
    address = CharField(required=False)
    city = CharField(max_length=100, required=False)
    state = CharField(max_length=100, required=False)
    country = CharField(max_length=100, required=False)
    zip_code = CharField(max_length=20, required=False)
    notes = CharField(required=False)
    tags = CharField(max_length=500, required=False)
    score = IntegerField(required=False, default=0)


# =====================================================================
#  Company Serializers
# =====================================================================
class CompanySerializer(ModelSerializer):
    """Full company serializer."""
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CompanyCreateSerializer(Serializer):
    """Validate company creation."""
    name = CharField(max_length=255)
    industry = ChoiceField(
        choices=["technology", "finance", "healthcare", "education", "retail",
                 "manufacturing", "consulting", "real_estate", "media", "other"],
        required=False, default="technology",
    )
    size = ChoiceField(
        choices=["1-10", "11-50", "51-200", "201-1000", "1000+"],
        required=False, default="1-10",
    )
    website = URLField(required=False)
    email = EmailField(required=False)
    phone = CharField(max_length=30, required=False)
    address = CharField(required=False)
    city = CharField(max_length=100, required=False)
    state = CharField(max_length=100, required=False)
    country = CharField(max_length=100, required=False)
    zip_code = CharField(max_length=20, required=False)
    annual_revenue = DecimalField(max_digits=15, decimal_places=2, required=False)
    description = CharField(required=False)
    tags = CharField(max_length=500, required=False)


# =====================================================================
#  Deal Serializers
# =====================================================================
class DealSerializer(ModelSerializer):
    """Full deal serializer."""
    class Meta:
        model = Deal
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DealCreateSerializer(Serializer):
    """Validate deal creation."""
    title = CharField(max_length=255)
    value = DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    currency = CharField(max_length=3, required=False, default="USD")
    stage = ChoiceField(
        choices=["discovery", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"],
        required=False, default="discovery",
    )
    probability = IntegerField(required=False, default=10)
    contact_id = IntegerField(required=False)
    company_id = IntegerField(required=False)
    expected_close_date = CharField(required=False)
    source = CharField(max_length=100, required=False)
    priority = ChoiceField(
        choices=["low", "medium", "high", "critical"],
        required=False, default="medium",
    )
    description = CharField(required=False)
    tags = CharField(max_length=500, required=False)


# =====================================================================
#  Task Serializers
# =====================================================================
class TaskSerializer(ModelSerializer):
    """Full task serializer."""
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TaskCreateSerializer(Serializer):
    """Validate task creation."""
    title = CharField(max_length=255)
    description = CharField(required=False)
    status = ChoiceField(
        choices=["pending", "in_progress", "completed", "cancelled"],
        required=False, default="pending",
    )
    priority = ChoiceField(
        choices=["low", "medium", "high", "urgent"],
        required=False, default="medium",
    )
    due_date = CharField(required=False)
    assigned_to_id = IntegerField(required=False)
    contact_id = IntegerField(required=False)
    deal_id = IntegerField(required=False)
    company_id = IntegerField(required=False)
    task_type = ChoiceField(
        choices=["call", "email", "meeting", "follow_up", "demo", "other"],
        required=False, default="other",
    )


# =====================================================================
#  Activity & Note Serializers
# =====================================================================
class ActivitySerializer(ModelSerializer):
    class Meta:
        model = Activity
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class NoteSerializer(ModelSerializer):
    class Meta:
        model = Note
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class NoteCreateSerializer(Serializer):
    content = CharField()
    entity_type = CharField(max_length=50)
    entity_id = IntegerField()
    is_pinned = BooleanField(required=False, default=False)


# =====================================================================
#  Campaign Serializers
# =====================================================================
class CampaignSerializer(ModelSerializer):
    class Meta:
        model = EmailCampaign
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "sent_at", "recipient_count", "open_count", "click_count"]


class CampaignCreateSerializer(Serializer):
    name = CharField(max_length=255)
    subject = CharField(max_length=500)
    body_html = CharField()
    scheduled_at = CharField(required=False)
