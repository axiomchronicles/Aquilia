"""
CRM Mail Service — Send emails, manage campaigns.
Fully wired through the Aquilia ORM.
"""

from typing import Dict, Any, List
from aquilia.di import service
from aquilia.mail import asend_mail, EmailMessage
from aquilia.cache import CacheService

from modules.shared.models import EmailCampaign, Contact, Activity
from modules.shared.faults import MailSendFault, CampaignNotFoundFault


@service(scope="app")
class CRMMailService:
    """Email operations for the CRM. All queries use the ORM."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def send_contact_email(
        self,
        contact_id: int,
        subject: str,
        body: str,
        sender_id: int = None,
    ) -> Dict[str, Any]:
        """Send an email to a specific contact."""
        # Find contact via ORM
        contact = await Contact.get(pk=contact_id)
        if not contact:
            raise MailSendFault(f"Contact {contact_id} not found")

        try:
            await asend_mail(
                subject=subject,
                body=body,
                to=[contact.email],
            )
        except Exception as e:
            raise MailSendFault(str(e))

        # Log activity via ORM
        await Activity.create(
            action="email_sent",
            entity_type="contact",
            entity_id=contact_id,
            user_id=sender_id,
            description=f"Email sent: {subject}",
        )

        return {"message": "Email sent", "to": contact.email, "subject": subject}

    async def list_campaigns(self, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
        """List email campaigns via ORM."""
        total = await EmailCampaign.objects.count()
        offset = (page - 1) * per_page
        campaigns = await EmailCampaign.objects.order("-created_at").limit(per_page).offset(offset).all()

        return {
            "items": [c.to_dict() for c in campaigns],
            "total": total,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        campaign = await EmailCampaign.get(pk=campaign_id)
        if not campaign:
            raise CampaignNotFoundFault(campaign_id)
        return campaign.to_dict()

    async def create_campaign(self, data: Dict[str, Any], sender_id: int = None) -> Dict[str, Any]:
        """Create a new email campaign via ORM."""
        data["sender_id"] = sender_id
        data["status"] = "draft"
        campaign = await EmailCampaign.create(**data)
        return campaign.to_dict()

    async def send_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """Send a campaign to all contacts."""
        campaign_data = await self.get_campaign(campaign_id)

        # Get campaign instance for updating later
        campaign = await EmailCampaign.get(pk=campaign_id)

        # Get all contacts with emails via ORM
        contacts = await Contact.objects.all()

        sent_count = 0
        for contact in contacts:
            if contact.email:
                try:
                    await asend_mail(
                        subject=campaign_data["subject"],
                        body=campaign_data["body_html"],
                        to=[contact.email],
                    )
                    sent_count += 1
                except Exception:
                    pass

        # Update campaign status via ORM instance save
        from datetime import datetime, timezone

        campaign.status = "sent"
        campaign.sent_at = datetime.now(timezone.utc).isoformat()
        campaign.recipient_count = sent_count
        await campaign.save(update_fields=["status", "sent_at", "recipient_count"])

        return {
            "message": f"Campaign sent to {sent_count} contacts",
            "recipient_count": sent_count,
        }
